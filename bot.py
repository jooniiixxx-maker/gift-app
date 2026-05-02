import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

TOKEN = "8708620848:AAEHi8SlcNczOYIaYH-4HnOcxbXvp-wlcOc"
WEBAPP_URL = "https://тут_будет_render_url"

bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(
                text="Открыть Mini App",
                web_app=types.WebAppInfo(url=WEBAPP_URL)
            )]
        ],
        resize_keyboard=True
    )
    await message.answer("Открой Mini App:", reply_markup=keyboard)


@dp.message()
async def handle_webapp(message: types.Message):
    if message.web_app_data:
        data = json.loads(message.web_app_data.data)

        gift = data.get("gift")
        model = data.get("model")

        await message.answer(f"Ты выбрал:\n{gift} | {model}")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())