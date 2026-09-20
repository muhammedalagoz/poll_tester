# poll_tester

Kendi yerel oylama sayfanı test etmek için Playwright tabanlı bir otomasyon aracı. Sahte bir oylama sunucusuyla (`mock_poll_server.py`) birlikte gelir; böylece "oturum başına tek oy" gibi sınırlamaların doğru çalışıp çalışmadığını kendi makinende deneyebilirsin.

> **Kullanım kapsamı:** Yalnızca senin sahibi olduğun veya test izni olan, yerel (`localhost` / `127.0.0.1`) sayfalarda kullan. Üçüncü tarafların herkese açık anketlerine karşı çalıştırmak anket sonucunu manipüle etmek olur ve bu projenin amacı değildir.

## Nasıl çalışır

1. Temiz bir tarayıcı bağlamı açar (çerezsiz, gizli sekme benzeri).
2. Ayarlanan adayı seçip gönder butonuna basar, sayfayı yeniler.
3. Aday "lider" (sarı) olarak işaretlenince bağlamı kapatıp yenisini açar.
4. Terminalde `q` tuşuna basınca durur.

## Dosyalar

| Dosya | Açıklama |
| --- | --- |
| `poll_tester.py` | Playwright ile oylama otomasyonu |
| `mock_poll_server.py` | Yerel sahte oylama sunucusu (yalnızca `127.0.0.1`) |
| `.env.example` | Ayar şablonu |
| `requirements.txt` | Bağımlılıklar (`playwright`, `python-dotenv`) |

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

`.env` dosyasını yerel sunucuya göre düzenle:

```env
TARGET_URL=https://www.tuttosport.com/sondaggi/calcio/golden-boy/2026/09/10-151147857/golden_boy_web_2026_vota_il_tuo_preferito_round_3
CANDIDATE=Ilhan Fakili
SUBMIT_TEXT=VOTA ORA
HIGHLIGHT_SELECTOR=label.option.leader
OPTION_SELECTOR=label.option
HEADLESS=0
DELAY_MS=500
```

## Çalıştırma

Bir terminalde sahte sunucuyu başlat:

```bash
python mock_poll_server.py
```

Başka bir terminalde testi çalıştır:

```bash
python poll_tester.py
```

Durdurmak için terminalde `q` tuşuna bas.

## Ayarlar

| Değişken | Varsayılan | Açıklama |
| --- | --- | --- |
| `TARGET_URL` | `http://127.0.0.1:8000` | Test edilen yerel sayfa |
| `CANDIDATE` | `Ilhan Fakili` | Seçilecek adayın metni |
| `SUBMIT_TEXT` | `VOTA ORA` | Gönder butonunun adı |
| `HIGHLIGHT_SELECTOR` | `label.option.leader` | Liderin işaretlendiğini gösteren seçici |
| `OPTION_SELECTOR` | `label.option` | Seçenek öğeleri için seçici |
| `HEADLESS` | `0` | `1` ise tarayıcı görünmez çalışır |
| `DELAY_MS` | `500` | Turlar arası bekleme (ms) |

Sahte sunucu için: `PORT` (varsayılan `8000`) ve `ENFORCE_LIMIT` (varsayılan `1`; açıkken aynı çerezle ikinci oy reddedilir).

## Notlar

- `.env` dosyasını repoya ekleme; yalnızca `.env.example` paylaşılır.
- macOS/Linux gerekir (`termios` ve `tty` kullanılır).
