import asyncio
import html
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from dotenv import load_dotenv
from yt_dlp import YoutubeDL

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "7566074255:AAFvyyVaU9iW31_wmlYjMQnUonRs4rm6bVM").strip()
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "1024"))
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()

DOWNLOAD_DIR.mkdir(exist_ok=True)

URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_first_url(text: str) -> str | None:
    match = URL_RE.search(text or "")
    return match.group(0).strip() if match else None


def normalize_hostname(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    return hostname.lower().removeprefix("www.")


def detect_platform(url: str) -> str | None:
    host = normalize_hostname(url)

    if host in {"youtube.com", "m.youtube.com", "youtu.be"} or host.endswith(".youtube.com"):
        return "YouTube"
    if host in {"instagram.com", "m.instagram.com"} or host.endswith(".instagram.com"):
        return "Instagram"
    if host in {"pinterest.com", "pin.it"} or host.endswith(".pinterest.com"):
        return "Pinterest"

    return None


def is_supported_url(url: str) -> bool:
    return detect_platform(url) is not None


def main_keyboard() -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    if MINI_APP_URL:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🌐 Mini App ochish",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="ℹ️ Qo‘llanma", callback_data="help")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def extract_video_info(url: str) -> dict:
    opts = {
        "quiet": True,
        "skip_download": False,
        "noplaylist": True,
        "no_warnings": True,
    }
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def download_video(url: str) -> Path:
    output_template = str(DOWNLOAD_DIR / "%(extractor)s_%(id)s.%(ext)s")
    max_bytes = MAX_FILE_MB * 1024 * 1024

    opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "max_filesize": max_bytes,
        "restrictfilenames": True,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = Path(ydl.prepare_filename(info))

        # yt-dlp can change extension after merge/conversion; find the real downloaded file.
        if not filepath.exists():
            video_id = info.get("id")
            possible = list(DOWNLOAD_DIR.glob(f"*_{video_id}.*")) if video_id else []
            if possible:
                filepath = max(possible, key=lambda p: p.stat().st_size)

        if not filepath.exists():
            raise FileNotFoundError("Downloaded file not found")

        if filepath.stat().st_size > max_bytes:
            filepath.unlink(missing_ok=True)
            raise ValueError(f"File is larger than {MAX_FILE_MB} MB")

        return filepath


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return ""
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"⏱ Davomiyligi: {hours}:{minutes:02d}:{sec:02d}\n"
    return f"⏱ Davomiyligi: {minutes}:{sec:02d}\n"


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Put your token into .env file.")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "👋 <b>Salom, jigar!</b>\n\n"
        "Men YouTube, Instagram va Pinterest’dan public videolarni yuklab beraman.\n\n"
        "📌 Link yubor: YouTube / Instagram Reels / Pinterest video.\n"
        f"📦 Limit: {MAX_FILE_MB} MB\n\n"
        "⚠️ Faqat o‘zingga tegishli yoki yuklab olishga ruxsat berilgan kontentdan foydalan.",
        reply_markup=main_keyboard(),
    )


@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "🧭 <b>Qo‘llanma</b>\n\n"
        "1) YouTube, Instagram yoki Pinterest video linkini yubor.\n"
        "2) Bot linkni tekshiradi.\n"
        "3) Hajmi limitdan oshmasa, Telegramga video qilib yuboradi.\n\n"
        "✅ Mos linklar:\n"
        "• https://youtu.be/...\n"
        "• https://youtube.com/shorts/...\n"
        "• https://instagram.com/reel/...\n"
        "• https://pin.it/...\n\n"
        "Instagram private postlari yoki login talab qiladigan kontent ishlamasligi mumkin."
    )


@dp.callback_query(F.data == "help")
async def help_callback(callback) -> None:
    await callback.message.answer(
        "📌 Link yuboring, men platformani avtomatik aniqlayman: YouTube, Instagram yoki Pinterest."
    )
    await callback.answer()


@dp.message(F.text)
async def downloader_handler(message: Message) -> None:
    text = message.text.strip()
    url = extract_first_url(text)

    if not url or not is_supported_url(url):
        await message.answer(
            "📌 Admin bilan bog'lanish.\n\n"
            "Masalan:\n"
            "• https://t.me/ASLCODERR\n"
        )
        return

    platform = detect_platform(url) or "Video"
    status = await message.answer(f"🔎 {platform} link tekshirilyapti...")

    try:
        info = await asyncio.to_thread(extract_video_info, url)
        title = html.escape(info.get("title") or f"{platform} video")
        duration_text = format_duration(info.get("duration"))

        await status.edit_text(
            f"✅ Topildi: <b>{platform}</b>\n"
            f"🎬 <b>{title}</b>\n"
            f"{duration_text}\n"
            "⬇️ Yuklab olinmoqda..."
        )

        filepath = await asyncio.to_thread(download_video, url)

        await status.edit_text("📤 Telegramga yuborilyapti...")
        video_file = FSInputFile(filepath)

        if filepath.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
            await message.answer_video(video=video_file, caption=f"🎬 {title}")
        else:
            await message.answer_document(document=video_file, caption=f"📎 {title}")

        await status.delete()
        filepath.unlink(missing_ok=True)

    except ValueError as e:
        await status.edit_text(
            f"❌ Video hajmi katta yoki yuklab bo‘lmadi.\n"
            f"Limit: {MAX_FILE_MB} MB\n\n"
            f"Texnik xabar: <code>{html.escape(str(e))}</code>"
        )
    except Exception as e:
        logger.exception("Download error")
        await status.edit_text(
            "❌ Xatolik yuz berdi. Boshqa public video link bilan sinab ko‘r.\n\n"
            "Ehtimoliy sabablar:\n"
            "• Link private yoki login talab qiladi\n"
            "• Video hajmi katta\n"
            "• Platforma vaqtincha yuklashga ruxsat bermayapti\n\n"
            f"Texnik xabar: <code>{html.escape(str(e)[:500])}</code>"
        )


async def main() -> None:
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
