import asyncio
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Optional, Tuple, List

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    FSInputFile,
)
from dotenv import load_dotenv
from yt_dlp import YoutubeDL

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
MAX_FILE_MB = int(os.getenv('MAX_FILE_MB', '45'))
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', 'downloads'))
MINI_APP_URL = os.getenv('MINI_APP_URL', '').strip()
PORT = int(os.getenv('PORT', '10000'))

ENABLE_FORCE_SUB = os.getenv('ENABLE_FORCE_SUB', 'true').lower().strip() in ('1', 'true', 'yes', 'on')
FORCE_SUB_CHANNELS = [x.strip() for x in os.getenv('FORCE_SUB_CHANNELS', '').split(',') if x.strip()]
FORCE_SUB_URLS = [x.strip() for x in os.getenv('FORCE_SUB_URLS', '').split(',') if x.strip()]
FORCE_SUB_TITLES = [x.strip() for x in os.getenv('FORCE_SUB_TITLES', '').split(',') if x.strip()]
INSTAGRAM_COOKIES_FILE = os.getenv('INSTAGRAM_COOKIES_FILE', '').strip()

if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN topilmadi. Render Environment Variables yoki .env ichiga BOT_TOKEN yozing.')

DOWNLOAD_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('yuklovchi-bot')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

URL_RE = re.compile(r'https?://[^\s]+', re.IGNORECASE)


def extract_url(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    match = URL_RE.search(text)
    return match.group(0) if match else None


def detect_platform(url: str) -> str:
    u = url.lower()
    if 'youtube.com' in u or 'youtu.be' in u:
        return 'YouTube'
    if 'instagram.com' in u:
        return 'Instagram'
    if 'pinterest.' in u or 'pin.it' in u:
        return 'Pinterest'
    return 'Noma’lum platforma'


def is_force_sub_configured() -> bool:
    return ENABLE_FORCE_SUB and len(FORCE_SUB_CHANNELS) > 0


def make_channel_title(index: int, channel: str) -> str:
    if index < len(FORCE_SUB_TITLES) and FORCE_SUB_TITLES[index]:
        return FORCE_SUB_TITLES[index]
    return channel.replace('@', '')


def make_channel_url(index: int, channel: str) -> str:
    if index < len(FORCE_SUB_URLS) and FORCE_SUB_URLS[index]:
        return FORCE_SUB_URLS[index]
    if channel.startswith('@'):
        return f'https://t.me/{channel[1:]}'
    return 'https://t.me/'


def subscription_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i, channel in enumerate(FORCE_SUB_CHANNELS):
        rows.append([
            InlineKeyboardButton(
                text=f'➕ {make_channel_title(i, channel)}',
                url=make_channel_url(i, channel),
            )
        ])
    rows.append([InlineKeyboardButton(text='✅ Obunani tekshirish', callback_data='check_subscription')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_keyboard(is_subscribed: bool) -> InlineKeyboardMarkup:
    rows = []
    if is_subscribed and MINI_APP_URL:
        rows.append([InlineKeyboardButton(text='🌐 Mini App ochish', web_app=WebAppInfo(url=MINI_APP_URL))])
    rows.append([InlineKeyboardButton(text='ℹ️ Yordam', callback_data='help')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def check_user_subscription(user_id: int) -> Tuple[bool, List[str]]:
    if not is_force_sub_configured():
        return True, []

    allowed_statuses = {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }

    missing = []
    for channel in FORCE_SUB_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in allowed_statuses:
                missing.append(channel)
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.warning('Obunani tekshirishda muammo: %s | %s', channel, e)
            missing.append(channel)
        except Exception as e:
            logger.exception('Noma’lum obuna tekshirish xatosi: %s', e)
            missing.append(channel)
    return len(missing) == 0, missing


async def require_subscription(message: Message) -> bool:
    subscribed, _ = await check_user_subscription(message.from_user.id)
    if subscribed:
        return True
    await message.answer(
        '🔒 Botdan foydalanish uchun avval kanalga obuna bo‘ling.\n\n'
        'Obuna bo‘lgandan keyin **✅ Obunani tekshirish** tugmasini bosing.',
        reply_markup=subscription_keyboard(),
        parse_mode='Markdown',
    )
    return False


def build_ytdlp_opts(url: str, skip_download: bool = False, outtmpl: Optional[str] = None) -> dict:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'retries': 5,
        'fragment_retries': 5,
        'extractor_retries': 3,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/125.0 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
        },
    }
    if skip_download:
        opts['skip_download'] = True
    if outtmpl:
        opts['outtmpl'] = outtmpl
        opts['format'] = 'best[ext=mp4][height<=720]/best[height<=720]/best'
        opts['merge_output_format'] = 'mp4'
    if 'instagram.com' in url.lower() and INSTAGRAM_COOKIES_FILE:
        cookie_path = Path(INSTAGRAM_COOKIES_FILE)
        if cookie_path.exists():
            opts['cookiefile'] = str(cookie_path)
    return opts


async def get_video_info(url: str) -> dict:
    opts = build_ytdlp_opts(url, skip_download=True)
    def _extract():
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    return await asyncio.to_thread(_extract)


async def download_video(url: str) -> Path:
    unique_id = uuid.uuid4().hex
    outtmpl = str(DOWNLOAD_DIR / f'{unique_id}.%(ext)s')
    opts = build_ytdlp_opts(url, outtmpl=outtmpl)

    def _download():
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            possible_path = Path(filename)
            if possible_path.exists():
                return possible_path
            mp4_path = possible_path.with_suffix('.mp4')
            if mp4_path.exists():
                return mp4_path
            files = sorted(DOWNLOAD_DIR.glob(f'{unique_id}.*'), key=lambda p: p.stat().st_mtime, reverse=True)
            if files:
                return files[0]
            raise FileNotFoundError('Yuklangan fayl topilmadi.')

    return await asyncio.to_thread(_download)


async def process_url(message: Message, url: str) -> None:
    if not await require_subscription(message):
        return

    platform = detect_platform(url)
    status_msg = await message.answer(f'🔎 Platforma: **{platform}**\nLink tekshirilmoqda...', parse_mode='Markdown')

    try:
        info = await get_video_info(url)
        title = info.get('title', 'Video')
        duration = info.get('duration')
        duration_text = ''
        if duration:
            minutes = duration // 60
            seconds = duration % 60
            duration_text = f'\n⏱ Davomiyligi: {minutes}:{seconds:02d}'

        await status_msg.edit_text(
            f'✅ Video topildi\n\n🎬 **{title}**{duration_text}\n\n⬇️ Yuklab olinmoqda...',
            parse_mode='Markdown',
        )

        file_path = await download_video(url)
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_MB:
            file_path.unlink(missing_ok=True)
            await status_msg.edit_text(
                f'⚠️ Fayl hajmi katta: **{size_mb:.1f} MB**\n\nHozir maksimal limit: **{MAX_FILE_MB} MB**.',
                parse_mode='Markdown',
            )
            return

        await status_msg.edit_text('📤 Telegramga yuborilmoqda...')
        await message.answer_video(video=FSInputFile(file_path), caption=f'✅ Tayyor!\n🎬 {title}\n\n🤖 Bot orqali yuklandi.')
        await status_msg.delete()
        file_path.unlink(missing_ok=True)

    except Exception as e:
        logger.exception('Download error')
        await status_msg.edit_text(
            '❌ Yuklashda xatolik chiqdi.\n\n'
            'Sabablar:\n'
            '• Link noto‘g‘ri bo‘lishi mumkin\n'
            '• Video private/yopiq bo‘lishi mumkin\n'
            '• Instagram login talab qilayotgan bo‘lishi mumkin\n'
            '• Hosting IP vaqtincha cheklangan bo‘lishi mumkin\n\n'
            f'Texnik xato: `{e}`',
            parse_mode='Markdown',
        )


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    subscribed, _ = await check_user_subscription(message.from_user.id)
    if not subscribed:
        await message.answer(
            'Assalomu alaykum! 👋\n\n'
            'Bu bot orqali YouTube, Instagram va Pinterest videolarini yuklab olishingiz mumkin.\n\n'
            '🔒 Botdan foydalanish uchun avval kanalga obuna bo‘ling:',
            reply_markup=subscription_keyboard(),
        )
        return
    await message.answer(
        'Assalomu alaykum! 👋\n\n'
        'Men YouTube, Instagram va Pinterest videolarini yuklab beraman.\n\n'
        '📌 Link yuboring yoki Mini App orqali kiriting.',
        reply_markup=start_keyboard(is_subscribed=True),
    )


@dp.message(Command('help'))
async def help_handler(message: Message) -> None:
    if not await require_subscription(message):
        return
    await message.answer(
        'ℹ️ **Yordam**\n\n'
        '1. YouTube / Instagram / Pinterest link yuboring.\n'
        '2. Bot videoni tekshiradi.\n'
        '3. Hajmi mos bo‘lsa Telegramga yuboradi.\n\n'
        '⚠️ Private/yopiq postlar ishlamasligi mumkin.',
        parse_mode='Markdown',
        reply_markup=start_keyboard(is_subscribed=True),
    )


@dp.callback_query(F.data == 'help')
async def help_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    subscribed, _ = await check_user_subscription(callback.from_user.id)
    if not subscribed:
        await callback.message.answer('🔒 Avval kanalga obuna bo‘ling.', reply_markup=subscription_keyboard())
        return
    await callback.message.answer(
        'ℹ️ **Yordam**\n\nYouTube / Instagram / Pinterest link yuboring yoki Mini App orqali link kiriting.',
        parse_mode='Markdown',
        reply_markup=start_keyboard(is_subscribed=True),
    )


@dp.callback_query(F.data == 'check_subscription')
async def check_subscription_callback(callback: CallbackQuery) -> None:
    subscribed, _ = await check_user_subscription(callback.from_user.id)
    if not subscribed:
        await callback.answer('Hali obuna topilmadi ⚠️', show_alert=True)
        await callback.message.answer(
            '❌ Obuna hali tasdiqlanmadi.\n\nKanalga obuna bo‘ling, keyin yana tekshiring:',
            reply_markup=subscription_keyboard(),
        )
        return
    await callback.answer('Obuna tasdiqlandi ✅', show_alert=True)
    await callback.message.answer(
        '✅ Obuna tasdiqlandi!\n\nEndi YouTube, Instagram yoki Pinterest link yuboring.',
        reply_markup=start_keyboard(is_subscribed=True),
    )


@dp.message(lambda message: message.web_app_data is not None)
async def web_app_handler(message: Message) -> None:
    if not await require_subscription(message):
        return
    try:
        data = json.loads(message.web_app_data.data)
        url = data.get('url')
    except Exception:
        await message.answer('❌ Mini App’dan kelgan ma’lumot noto‘g‘ri.')
        return
    if not url:
        await message.answer('❌ Mini App link yubormadi.')
        return
    await process_url(message, url)


@dp.message(F.text)
async def text_handler(message: Message) -> None:
    url = extract_url(message.text)
    if not url:
        if not await require_subscription(message):
            return
        await message.answer(
            '📌 YouTube, Instagram yoki Pinterest link yuboring.\n\nMasalan:\n`https://youtu.be/...`',
            parse_mode='Markdown',
            reply_markup=start_keyboard(is_subscribed=True),
        )
        return
    await process_url(message, url)


async def health(request):
    return web.Response(text='Bot is running ✅')


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info('Health server started on port %s', PORT)


async def main() -> None:
    logger.info('Bot ishga tushdi.')
    await start_web_server()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
