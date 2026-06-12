# YouTube + Instagram + Pinterest Downloader Telegram Bot

Python + aiogram v3 + yt-dlp asosida yozilgan Telegram bot.

## Funksiyalar

- `/start` va `/help`
- YouTube linklarni aniqlash
- Instagram public Reel/Post linklarni aniqlash
- Pinterest public video linklarni aniqlash
- Video nomi va davomiyligini ko‘rsatish
- Limitdan oshmasa Telegramga video yuborish
- Telegram Mini App uchun tayyor `mini_app/` sahifa
- Yuklangan fayllarni avtomatik tozalash

## O‘rnatish

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env` faylga BotFather tokeningizni yozing:

```env
BOT_TOKEN=123456:ABC...
MAX_FILE_MB=45
DOWNLOAD_DIR=downloads
MINI_APP_URL=
```

Ishga tushirish:

```bash
python bot.py
```

## Mini App qo‘shish

`mini_app/` papkasini GitHub Pages, Netlify yoki Vercel kabi HTTPS hostingga joylang.

Keyin `.env` ichiga Mini App linkingizni yozing:

```env
MINI_APP_URL=https://your-mini-app-url.com
```

Botni qayta ishga tushiring:

```bash
python bot.py
```

Shundan keyin `/start` bosilganda `🌐 Mini App ochish` tugmasi chiqadi.

## Eslatma

- Instagram private postlari, yopiq account kontenti yoki login talab qiladigan linklar ishlamasligi mumkin.
- Pinterest’da faqat video bo‘lgan public pinlar ishlaydi.
- Faqat o‘zingizga tegishli yoki yuklab olishga ruxsat berilgan kontentdan foydalaning.
- Agar ayrim videolarda xato chiqsa, `yt-dlp` ni yangilang:

```bash
pip install -U yt-dlp
```
