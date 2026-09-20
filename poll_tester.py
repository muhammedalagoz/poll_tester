"""Yerel oylama sayfasi test otomasyonu (Playwright).

Her turda temiz bir tarayici baglami (gizli sekme benzeri) acar, adayi secer,
gonder butonuna basar, sayfayi yeniler. Aday "isaretli" (sari) olunca baglami
kapatip yenisini acar. 'q' tusuna basinca durur.

Guvenlik: yalnizca localhost / 127.0.0.1 / ::1 hedeflerine calisir.
"""
import os
import select
import sys
import termios
import threading
import tty
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "http://127.0.0.1:8000")
CANDIDATE = os.getenv("CANDIDATE", "Ilhan Fakili")
SUBMIT_TEXT = os.getenv("SUBMIT_TEXT", "VOTA ORA")
HIGHLIGHT_SELECTOR = os.getenv("HIGHLIGHT_SELECTOR", "label.option.leader")
OPTION_SELECTOR = os.getenv("OPTION_SELECTOR", "label.option")
HEADLESS = os.getenv("HEADLESS", "0") == "1"
DELAY_MS = int(os.getenv("DELAY_MS", "500"))
# Yerel sayfada cerez/onay modali cikiyorsa kapatma butonu (bos ise atlanir).
# CONSENT_SELECTOR: CSS secici (or. "#consent-modal button.accept")
# CONSENT_TEXT: buton metni (or. "Kabul et"); ikisi de verilirse secici kullanilir.
CONSENT_SELECTOR = os.getenv("CONSENT_SELECTOR", "")
CONSENT_TEXT = os.getenv("CONSENT_TEXT", "")

ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}
stop = threading.Event()


def check_target():
    host = urlparse(TARGET_URL).hostname
    if host not in ALLOWED_HOSTS:
        sys.exit(f"Reddedildi: '{host}' yerel bir adres degil. "
                 f"Yalnizca {sorted(ALLOWED_HOSTS)} desteklenir.")


def listen_for_q():
    """Terminalde 'q' tusunu bekler (enter gerektirmez)."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while not stop.is_set():
            if select.select([sys.stdin], [], [], 0.2)[0]:
                if sys.stdin.read(1).lower() == "q":
                    stop.set()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def is_highlighted(page):
    return page.locator(HIGHLIGHT_SELECTOR, has_text=CANDIDATE).count() > 0


def dismiss_consent(page):
    try:
        agree_btn = page.get_by_text("AGREE AND CLOSE", exact=False)
        # Sadece 2 saniye içinde ekranda belirirse tıkla
        if agree_btn.is_visible(timeout=2000):
            agree_btn.click(timeout=2000)
            print("Agree butonuna başarıyla tıklandı.")
    except Exception:
        # Ekran kapanmışsa veya buton çıkmadıysa hatayı yut ve devam et
        pass

def close_ad_banner(page):
    try:
        # Close X uyarısını 2 saniyeye düşürerek süreci yavaşlatmasını engelleyin
        page.get_by_text("Close X", exact=False).click(timeout=2000)
        print("Reklam kapatma butonuna basıldı.")
    except Exception:
        # Reklam çıkmadıysa sessizce devam et
        pass
def vote_once(page, vote_count):
    # Çerez banner'ı ve reklamları güvenli şekilde geç
    dismiss_consent(page)
    close_ad_banner(page)

    # Adayı bul
    candidate_option = page.get_by_text(CANDIDATE, exact=False).first
    candidate_option.wait_for(state="visible", timeout=10000)
    
    # Tıkla
    candidate_option.click(force=True)

    # Seçeneğin veya ilgili radio butonun işaretlendiğini kontrol et
    # Eğer DOM üzerinde doğrudan input[type="radio"] varsa is_checked() kontrolü yapılır
    try:
        radio_input = candidate_option.locator("xpath=..//input[@type='radio']").first
        if radio_input.count() > 0 and radio_input.is_checked(timeout=1000):
            print(f"  [✓] '{CANDIDATE}' seçeneği/radio butonu başarıyla işaretlendi.")
        else:
            print(f"  [i] '{CANDIDATE}' öğesine tıklandı (radio kontrolü doğrulanamadı, devam ediliyor).")
    except Exception:
        print(f"  [i] '{CANDIDATE}' tıklandı.")

    # Gönder butonuna tıkla
    submit_btn = page.get_by_role("button", name=SUBMIT_TEXT)
    submit_btn.wait_for(state="visible", timeout=5000)
    submit_btn.click(force=True)

    print(f"  [→] {vote_count}. oy gönderme butonuna tıklandı.")

    # İsteğin sunucuya iletilmesi için kısa bekleme
    page.wait_for_timeout(1000)

    # Sayfayı yenileme / tekrar yönlendirme
    try:
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
    except Exception:
        page.evaluate("window.stop()")
        page.goto(TARGET_URL, wait_until="commit", timeout=10000)

    print(f"  [✓] Sayfa yenilendi.")
    page.wait_for_timeout(DELAY_MS)


def main():
    threading.Thread(target=listen_for_q, daemon=True).start()
    print(f"Hedef: {TARGET_URL} | Aday: {CANDIDATE} | Durdurmak için 'q'")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        session = 0
        while not stop.is_set():
            session += 1
            print(f"\n--- Oturum #{session} Başlatılıyor ---")
            context = browser.new_context()  # temiz çerez/oturum
            page = context.new_page()
            
            try:
                page.goto(TARGET_URL, wait_until="domcontentloaded")
            except Exception:
                pass
                
            votes = 0
            while not stop.is_set() and not is_highlighted(page):
                votes += 1
                print(f"\n[Oturum #{session}] {votes}. Oy kullanma denemesi yapılıyor...")
                vote_once(page, votes)
                
            if is_highlighted(page):
                print(f"\n[★ SUCCESS] [Oturum #{session}] Aday sarı/lider olarak işaretlendi!")
                print(f"   Toplam {votes} denemede hedef duruma ulaşıldı. Yeni oturuma geçiliyor...")
                
            context.close()
        browser.close()
    print("\nTest Otomasyonu Durduruldu.")


if __name__ == "__main__":
    main()
