import aiohttp
import os
import re
import time
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from urllib.parse import quote, unquote

app = FastAPI()

CDN = "https://cdn.changes.tg/gifts/models"
BOT_TOKEN = os.getenv("BOT_TOKEN")

user_packs = {}


async def get_items(url, only_dirs=False, only_ext=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "html.parser")
    items = []

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue

        if href.startswith("?") or href in ["/", "../"]:
            continue

        if href.startswith("./"):
            href = href[2:]

        name = unquote(href).strip("/")

        if not name:
            continue

        if only_dirs and not href.endswith("/"):
            continue

        if only_ext and not name.lower().endswith(only_ext):
            continue

        items.append(name)

    return sorted(list(set(items)))


async def get_bot_username():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe") as r:
            data = await r.json()
            return data["result"]["username"]


async def download_file(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status != 200:
                return False

            with open(filename, "wb") as f:
                f.write(await r.read())

            return True


def safe_pack_base(title):
    base = title.lower()
    base = re.sub(r"[^a-z0-9_]", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "giftpack"


async def telegram_create_pack(user_id, pack_name, title, filename):
    sticker_json = [{
        "sticker": "attach://sticker_file",
        "emoji_list": ["🎁"],
        "format": "animated"
    }]

    form = aiohttp.FormData()
    form.add_field("user_id", str(user_id))
    form.add_field("name", pack_name)
    form.add_field("title", title)
    form.add_field("sticker_format", "animated")
    form.add_field("stickers", str(sticker_json).replace("'", '"'))
    form.add_field(
        "sticker_file",
        open(filename, "rb"),
        filename=filename,
        content_type="application/x-tgsticker"
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/createNewStickerSet",
            data=form
        ) as r:
            return await r.json()


async def telegram_add_sticker(user_id, pack_name, filename):
    sticker_json = {
        "sticker": "attach://sticker_file",
        "emoji_list": ["🎁"],
        "format": "animated"
    }

    form = aiohttp.FormData()
    form.add_field("user_id", str(user_id))
    form.add_field("name", pack_name)
    form.add_field("sticker", str(sticker_json).replace("'", '"'))
    form.add_field(
        "sticker_file",
        open(filename, "rb"),
        filename=filename,
        content_type="application/x-tgsticker"
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/addStickerToSet",
            data=form
        ) as r:
            return await r.json()


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://telegram.org/js/telegram-web-app.js"></script>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg,#0f172a,#3b0764);
    color: white;
    padding: 14px;
    overflow-x: hidden;
}

h2 {
    margin: 12px 0;
    font-size: 24px;
}

.topbar {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 12px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}

.card {
    background: rgba(255,255,255,0.10);
    border-radius: 18px;
    padding: 10px;
    text-align: center;
    animation: fadeUp 0.25s ease;
    overflow: hidden;
}

.card img {
    width: 100%;
    max-width: 130px;
    height: 130px;
    object-fit: contain;
    display: block;
    margin: 0 auto 8px;
}

.name {
    font-weight: bold;
    font-size: 13px;
    min-height: 34px;
    word-break: break-word;
}

button {
    width: 100%;
    border: none;
    border-radius: 14px;
    padding: 11px 8px;
    margin-top: 7px;
    background: #8b5cf6;
    color: white;
    font-weight: bold;
    font-size: 13px;
}

button:active {
    transform: scale(0.96);
}

.secondary {
    background: #334155;
}

.loader {
    width: 42px;
    height: 42px;
    border: 4px solid rgba(255,255,255,0.2);
    border-top: 4px solid white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 35px auto;
}

.toast {
    position: fixed;
    left: 50%;
    bottom: 25px;
    transform: translateX(-50%);
    background: #16a34a;
    color: white;
    padding: 13px 18px;
    border-radius: 16px;
    font-weight: bold;
    z-index: 9999;
    box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
</head>

<body>

<div class="topbar">
    <button onclick="createPack()">➕ Создать стикерпак</button>
    <button onclick="openPack()">📦 Открыть пак</button>
</div>

<h2 id="title">🎁 Подарки</h2>
<div id="content"><div class="loader"></div></div>

<script>
const tg = window.Telegram.WebApp;
tg.expand();

let packLink = null;
let packTitle = "Gift Pack";

async function createPack(){
    const title = prompt("Введите название стикерпака:", "Gift Pack");

    if(!title) return;

    packTitle = title;

    const res = await fetch("/api/create-pack", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            user_id: tg.initDataUnsafe.user.id,
            title: packTitle
        })
    });

    const data = await res.json();

    if(data.ok){
        packLink = data.link;
        showToast("✅ Стикерпак подготовлен");
    } else {
        showToast("❌ Ошибка создания");
    }
}

async function loadGifts(){
    document.getElementById("title").innerText = "🎁 Подарки";

    const content = document.getElementById("content");
    content.innerHTML = "<div class='loader'></div>";

    const res = await fetch("/api/gifts");
    const gifts = await res.json();

    let html = '<div class="grid">';

    gifts.forEach(g=>{
        html += `
        <div class="card">
            <div class="name">${g.name}</div>
            <button onclick="loadModels('${escapeJs(g.name)}')">Открыть</button>
        </div>`;
    });

    html += "</div>";
    content.innerHTML = html;
}

async function loadModels(gift){
    document.getElementById("title").innerText = gift;

    const content = document.getElementById("content");
    content.innerHTML = "<div class='loader'></div>";

    const res = await fetch("/api/models?gift=" + encodeURIComponent(gift));
    const models = await res.json();

    let html = "<button class='secondary' onclick='loadGifts()'>← Назад</button><br><br>";
    html += '<div class="grid">';

    models.forEach(m=>{
        html += `
        <div class="card">
            <img src="${m.icon}" loading="lazy">
            <div class="name">${m.name}</div>
            <button onclick="addSticker('${escapeJs(gift)}','${escapeJs(m.name)}')">➕ Добавить</button>
        </div>`;
    });

    html += "</div>";
    content.innerHTML = html;
}

async function addSticker(gift, model){
    showToast("⏳ Добавляем...");

    const res = await fetch("/api/add", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            user_id: tg.initDataUnsafe.user.id,
            title: packTitle,
            gift: gift,
            model: model
        })
    });

    const data = await res.json();

    if(data.ok){
        packLink = data.link;
        showToast("✅ Стикер добавлен");
    } else {
        showToast("❌ " + (data.error || "Ошибка"));
    }
}

function openPack(){
    if(packLink){
        window.open(packLink);
    } else {
        showToast("Сначала создай пак или добавь стикер");
    }
}

function showToast(text){
    const old = document.querySelector(".toast");
    if(old) old.remove();

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerText = text;

    document.body.appendChild(toast);

    setTimeout(()=>toast.remove(), 2200);
}

function escapeJs(text){
    return text.replace(/'/g, "\\\\'").replace(/"/g, "&quot;");
}

loadGifts();
</script>

</body>
</html>
"""


@app.get("/api/gifts")
async def gifts():
    items = await get_items(CDN + "/", only_dirs=True)
    return JSONResponse([{"name": i} for i in items])


@app.get("/api/models")
async def models(gift: str):
    url = f"{CDN}/{quote(gift)}/png/"
    files = await get_items(url, only_ext=".png")

    return JSONResponse([
        {
            "name": f.replace(".png", ""),
            "icon": f"{url}{quote(f)}"
        }
        for f in files
    ])


@app.post("/api/create-pack")
async def create_pack(request: Request):
    data = await request.json()

    user_id = int(data["user_id"])
    title = data.get("title", "Gift Pack")

    bot_username = await get_bot_username()
    base = safe_pack_base(title)

    pack_name = f"{base}_{user_id}_{int(time.time())}_by_{bot_username}"
    pack_name = pack_name[:64]

    user_packs[user_id] = {
        "name": pack_name,
        "title": title,
        "created": False
    }

    return JSONResponse({
        "ok": True,
        "link": f"https://t.me/addstickers/{pack_name}"
    })


@app.post("/api/add")
async def add(request: Request):
    data = await request.json()

    user_id = int(data["user_id"])
    title = data.get("title", "Gift Pack")
    gift = data["gift"]
    model = data["model"]

    if user_id not in user_packs:
        bot_username = await get_bot_username()
        pack_name = f"giftpack_{user_id}_{int(time.time())}_by_{bot_username}"[:64]

        user_packs[user_id] = {
            "name": pack_name,
            "title": title,
            "created": False
        }

    pack = user_packs[user_id]
    pack_name = pack["name"]

    filename = f"{re.sub(r'[^a-zA-Z0-9_]', '_', model)}.tgs"
    url = f"{CDN}/{quote(gift)}/{quote(model)}.tgs"

    ok = await download_file(url, filename)

    if not ok:
        return JSONResponse({"ok": False, "error": "Файл .tgs не найден"})

    try:
        if not pack["created"]:
            result = await telegram_create_pack(
                user_id=user_id,
                pack_name=pack_name,
                title=pack["title"],
                filename=filename
            )
            print("CREATE RESULT:", result)

            if not result.get("ok"):
                return JSONResponse({"ok": False, "error": result.get("description", "Telegram error")})

            pack["created"] = True

        else:
            result = await telegram_add_sticker(
                user_id=user_id,
                pack_name=pack_name,
                filename=filename
            )
            print("ADD RESULT:", result)

            if not result.get("ok"):
                return JSONResponse({"ok": False, "error": result.get("description", "Telegram error")})

    finally:
        if os.path.exists(filename):
            os.remove(filename)

    return JSONResponse({
        "ok": True,
        "link": f"https://t.me/addstickers/{pack_name}"
    })