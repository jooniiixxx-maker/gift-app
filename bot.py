import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

TOKEN = os.getenv("BOT_TOKEN", "8708620848:AAEHi8SlcNczOYIaYH-4HnOcxbXvp-wlcOc")
WEBAPP_URL = "https://gift-app-xvm8.onrender.com"

bot = Bot(TOKEN)
dp = Dispatcher()


def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 Открыть Mini App",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]
        ]
    )


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Открой Mini App через кнопку ниже:",
        reply_markup=main_keyboard()
    )


async def main():
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())