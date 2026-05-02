import asyncio
import json
import os
import re
from urllib.parse import quote

import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    FSInputFile,
    InputSticker,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest


TOKEN = "8708620848:AAEHi8SlcNczOYIaYH-4HnOcxbXvp-wlcOc"
WEBAPP_URL = "https://gift-app-xvm8.onrender.com"

CDN = "https://cdn.changes.tg/gifts/models"

bot = Bot(TOKEN)
dp = Dispatcher()

user_packs = {}


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🎁 Открыть Mini App",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]
        ],
        resize_keyboard=True
    )


def pack_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="open_app")],
            [InlineKeyboardButton(text="✅ Закончить стикерпак", callback_data="finish_pack")]
        ]
    )


def make_pack_name(user_id: int, bot_username: str):
    return f"giftpack_{user_id}_by_{bot_username}"[:64]


async def download_file(url: str, filename: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return False

            with open(filename, "wb") as f:
                f.write(await response.read())

            return True


async def get_tgs_file(gift_name: str, model_name: str):
    variants = [
        (gift_name, model_name),
        (gift_name.title(), model_name.title()),
        (gift_name.upper(), model_name.upper()),
    ]

    for gift, model in variants:
        gift_encoded = quote(gift)
        model_encoded = quote(model)

        url = f"{CDN}/{gift_encoded}/{model_encoded}.tgs"

        safe_name = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ_-]", "_", model)
        filename = f"{safe_name}.tgs"

        if await download_file(url, filename):
            return filename

    return None


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Открой Mini App и выбери подарок/модель:",
        reply_markup=main_keyboard()
    )


@dp.callback_query(F.data == "open_app")
async def open_app(callback: types.CallbackQuery):
    await callback.message.answer(
        "Открой Mini App:",
        reply_markup=main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "finish_pack")
async def finish_pack(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    pack = user_packs.get(user_id)

    if pack:
        await callback.message.answer(
            f"✅ Стикерпак готов:\nhttps://t.me/addstickers/{pack['name']}"
        )
    else:
        await callback.message.answer("Стикерпак ещё не создан.")

    await callback.answer()


@dp.message(F.web_app_data)
async def handle_webapp(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        await message.answer("Ошибка данных из Mini App.")
        return

    action = data.get("action")
    gift = data.get("gift")
    model = data.get("model")

    if not gift or not model:
        await message.answer("Не получил подарок или модель.")
        return

    filename = await get_tgs_file(gift, model)

    if not filename:
        await message.answer("Не нашёл `.tgs` файл. Проверь название подарка и модели.")
        return

    try:
        if action == "find":
            await message.answer_document(
                FSInputFile(filename),
                caption=f"{gift} — {model}"
            )

        elif action == "add":
            user_id = message.from_user.id
            me = await bot.get_me()

            if user_id not in user_packs:
                pack_name = make_pack_name(user_id, me.username)
                pack_title = f"{message.from_user.first_name}'s Gift Pack"

                sticker = InputSticker(
                    sticker=FSInputFile(filename),
                    emoji_list=["🎁"],
                    format="animated"
                )

                await bot.create_new_sticker_set(
                    user_id=user_id,
                    name=pack_name,
                    title=pack_title,
                    stickers=[sticker]
                )

                user_packs[user_id] = {
                    "name": pack_name,
                    "title": pack_title
                }

                await message.answer(
                    f"✅ Стикерпак создан!\n\n"
                    f"Добавлен стикер: {gift} — {model}\n\n"
                    f"https://t.me/addstickers/{pack_name}",
                    reply_markup=pack_menu()
                )

            else:
                pack_name = user_packs[user_id]["name"]

                sticker = InputSticker(
                    sticker=FSInputFile(filename),
                    emoji_list=["🎁"],
                    format="animated"
                )

                await bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_name,
                    sticker=sticker
                )

                await message.answer(
                    f"✅ Стикер добавлен:\n{gift} — {model}",
                    reply_markup=pack_menu()
                )

        else:
            await message.answer("Неизвестное действие.")

    except TelegramBadRequest as e:
        await message.answer(f"Ошибка Telegram:\n{e.message}")

    finally:
        if os.path.exists(filename):
            os.remove(filename)


async def main():
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())