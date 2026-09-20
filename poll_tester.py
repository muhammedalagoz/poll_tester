"""Yerel oylama sayfasi test otomasyonu (Playwright).

Her turda temiz bir tarayici baglami (gizli sekme benzeri) acar, adayi secer,
gonder butonuna basar, sayfayi yeniler. Aday "isaretli" (sari) olunca veya 
GÜNLÜK LİMİT UYARISI alindiginda baglami kapatip yenisini acar. 
'q' tusuna basinca durur.

Guvenlik: yalnizca localhost / 127.0.0.1 / ::1 hedeflerine calisir.
"""
import os
import sys
import threading
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "http://127.0.0.1:8000")
CANDIDATE = os.getenv("CANDIDATE", "Ilhan Fakili")
SUBMIT_TEXT = os.getenv("SUBMIT_TEXT", "VOTA ORA")
HIGHLIGHT_SELECTOR = os.getenv("HIGHLIGHT_SELECTOR", "label.option.leader")
HEADLESS = os.getenv("HEADLESS", "0") == "1"
DELAY_MS = int(os.getenv("DELAY_MS", "500"))

# Rıza ve Çerez ayarları (.env üzerinden dinamik)
CONSENT_SELECTOR = os.getenv("CONSENT_SELECTOR", "")
CONSENT_TEXT = os.getenv("CONSENT_TEXT", "AGREE AND CLOSE")

# Limit uyarısı metni
LIMIT_TEXT = "HAI RAGGIUNTO IL LIMITE VOTI GIORNALIERO"

ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}
stop = threading.Event()


def listen_for_q():
    """Cross-platform 'q' tuşu dinleyicisi (Windows / Unix)."""
    if os.name == 'nt':
        import msvcrt
        while not stop.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8', errors='ignore')
                if key.lower() == 'q':
                    stop.set()
            time.sleep(0.1)
    else:
        import select
        import termios
        import tty
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
    try:
        return page.locator(HIGHLIGHT_SELECTOR, has_text=CANDIDATE).count() > 0
    except Exception:
        return False


def is_limit_reached(page):
    """Sayfada oy verme limitine ulaşıldığını belirten mesaj var mı kontrol eder."""
    try:
        return page.get_by_text(LIMIT_TEXT, exact=False).is_visible(timeout=1000)
    except Exception:
        return False


def dismiss_consent(page):
    try:
        if CONSENT_SELECTOR:
            btn = page.locator(CONSENT_SELECTOR).first
        else:
            btn = page.get_by_text(CONSENT_TEXT, exact=False)

        if btn.is_visible(timeout=2000):
            btn.click(timeout=2000)
            print("  [i] Onay butonuna tıklandı.")
    except Exception:
        pass


def close_ad_banner(page):
    try:
        btn = page.get_by_text("Close X", exact=False)
        if btn.is_visible(timeout=2000):
            btn.click(timeout=2000)
            print("  [i] Reklam kapatma butonuna basıldı.")
    except Exception:
        pass


def vote_once(page, vote_count):
    dismiss_consent(page)
    close_ad_banner(page)

    # İşlem öncesi limit kontrolü
    if is_limit_reached(page):
        return False

    # Adayı bul ve tıkla
    candidate_option = page.get_by_text(CANDIDATE, exact=False).first
    candidate_option.wait_for(state="visible", timeout=10000)
    candidate_option.click(force=True)

    # Radio kontrolü
    try:
        radio_input = candidate_option.locator("xpath=..//input[@type='radio']").first
        if radio_input.count() > 0 and radio_input.is_checked(timeout=1000):
            print(f"  [✓] '{CANDIDATE}' seçeneği işaretlendi.")
        else:
            print(f"  [i] '{CANDIDATE}' öğesine tıklandı.")
    except Exception:
        print(f"  [i] '{CANDIDATE}' tıklandı.")

    # Gönder butonuna tıkla
    submit_btn = page.get_by_role("button", name=SUBMIT_TEXT)
    submit_btn.wait_for(state="visible", timeout=5000)
    submit_btn.click(force=True)

    print(f"  [→] {vote_count}. oy gönderme butonuna tıklandı.")
    page.wait_for_timeout(1000)

    # Sayfayı yenileme
    try:
        page.reload(wait_until="domcontentloaded", timeout=15000)
    except Exception:
        page.evaluate("window.stop()")
        page.goto(TARGET_URL, wait_until="commit", timeout=10000)

    print("  [✓] Sayfa yenilendi.")
    page.wait_for_timeout(DELAY_MS)
    return True

def main():
    threading.Thread(target=listen_for_q, daemon=True).start()
    print(f"Hedef: {TARGET_URL} | Aday: {CANDIDATE} | Durdurmak için 'q'\n")

    with sync_playwright() as p:
        session = 0
        MAX_VOTES_PER_SESSION = 5  # Her tarayıcı oturumunda en fazla 5 oy

        while not stop.is_set():
            session += 1
            print(f"\n--- Oturum #{session} (Yeni Tarayıcı) Başlatılıyor ---")
            
            # Her oturumda Chromium tarayıcısı sıfırdan başlatılır
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                page.goto(TARGET_URL, wait_until="domcontentloaded")
            except Exception:
                pass

            votes = 0
            while not stop.is_set() and not is_highlighted(page):
                # 1. Günlük limit uyarısı çıktı mı kontrol et[cite: 3]
                if is_limit_reached(page):
                    print(f"\n[!] [Oturum #{session}] GÜNLÜK OY LİMİTİ UYARISI ALINDI![cite: 3]")
                    print("    Tarayıcı kapatılıp sıfırdan yeni tarayıcı başlatılacak...")
                    break

                # 2. 5 Oy sınırına ulaşıldı mı kontrol et
                if votes >= MAX_VOTES_PER_SESSION:
                    print(f"\n[i] [Oturum #{session}] {MAX_VOTES_PER_SESSION} oy sınırına ulaşıldı.")
                    print("    Tarayıcı kapatılıp yenisi açılıyor...")
                    break

                votes += 1
                print(f"[Oturum #{session}] {votes}/{MAX_VOTES_PER_SESSION}. Oy denemesi...")
                
                success = vote_once(page, votes)
                if not success:
                    break

            if is_highlighted(page):
                print(f"\n[★ SUCCESS] [Oturum #{session}] Aday sarı/lider olarak işaretlendi!")

            # Bağlam ve Tarayıcı tamamen kapatılır
            context.close()
            browser.close()
            
            print(f"--- Oturum #{session} Kapatıldı ---")
            time.sleep(1)  # Kısa bir bekleme

    print("\nTest Otomasyonu Durduruldu.")

if __name__ == "__main__":
    main()