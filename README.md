# Yuklovchi Bot

Telegram downloader bot:

- YouTube downloader
- Instagram public Reels/Post downloader
- Pinterest public video downloader
- Telegram Mini App
- Majburiy obuna
- Render deploy uchun toza struktura

## To‘g‘ri papka strukturasi

GitHub repo root ichida shu fayllar turishi kerak:

```text
Yuklovchi_bot/
├─ bot.py
├─ requirements.txt
├─ .python-version
├─ .gitignore
├─ .env.example
├─ render.yaml
├─ README.md
├─ mini_app/
│  ├─ index.html
│  ├─ style.css
│  └─ app.js
└─ cookies/
   └─ .gitkeep
```

## Lokal ishga tushirish

```powershell
python -m venv venv
.env\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python bot.py
```

## Render deploy

Render’da Root Directory bo‘sh qoladi.

Build Command:

```bash
python -m pip install --upgrade pip setuptools wheel && python -m pip install -r requirements.txt && python -m pip install -U yt-dlp
```

Start Command:

```bash
python bot.py
```

Environment Variables:

```text
PYTHON_VERSION=3.12.11
BOT_TOKEN=...
MINI_APP_URL=...
ENABLE_FORCE_SUB=true
FORCE_SUB_CHANNELS=@sening_kanaling
FORCE_SUB_URLS=https://t.me/sening_kanaling
FORCE_SUB_TITLES=Bizning kanal
```

Muhim: `.env` faylni GitHubga yuklamang.
