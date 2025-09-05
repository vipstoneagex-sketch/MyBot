# main.py
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.utils import executor

from dotenv import load_dotenv
from db import init_db, add_movie, get_movie_by_name

# Load environment variables
load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables!")

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: Message):
    await message.answer(
        "👋 Welcome to MovieBot!\n\n"
        "Upload movies in the admin group and I’ll save them.\n"
        "Send me a movie name and I’ll fetch it for you 🎬."
    )


@dp.message_handler(content_types=["document", "video"])
async def save_movie(message: Message):
    """Save movie info when admin posts a file."""
    if not message.chat.type in ["group", "supergroup"]:
        return  # Only group uploads allowed

    movie_name = None

    # Prefer caption (description) over filename
    if message.caption:
        movie_name = message.caption.strip()
    elif message.document:
        movie_name = message.document.file_name
    elif message.video:
        movie_name = message.video.file_name

    if not movie_name:
        await message.reply("⚠️ Couldn’t detect movie name!")
        return

    await add_movie(movie_name, message.chat.id, message.message_id)
    await message.reply(f"✅ Saved <b>{movie_name}</b> to database.")


@dp.message_handler()
async def search_movie(message: Message):
    """Search movies when users send a name."""
    query = message.text.strip()
    movie = await get_movie_by_name(query)

    if not movie:
        await message.answer("❌ Movie not found. Try another name.")
        return

    chat_id, msg_id = movie["chat_id"], movie["message_id"]
    try:
        await bot.forward_message(
            chat_id=message.chat.id,
            from_chat_id=chat_id,
            message_id=msg_id
        )
    except Exception as e:
        logger.error(f"Failed to forward movie: {e}")
        await message.answer("⚠️ Error while fetching movie.")


async def on_startup(_):
    logger.info("🚀 Bot started!")
    await init_db()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)