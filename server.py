import aiohttp
import os
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


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://telegram.org/js/telegram-web-app.js"></script>

<style>
body {
    margin: 0;
    font-family: Arial;
    background: linear-gradient(135deg,#0f172a,#3b0764);
    color: white;
    padding: 16px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(2,1fr);
    gap: 12px;
}

.card {
    background: rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 12px;
    text-align: center;
    animation: fadeUp 0.3s ease;
}

.card:active {
    transform: scale(0.95);
}

button {
    width: 100%;
    padding: 10px;
    margin-top: 6px;
    border: none;
    border-radius: 12px;
    background: #8b5cf6;
    color: white;
    font-weight: bold;
}

.loader {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(255,255,255,0.2);
    border-top: 4px solid white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 30px auto;
}

.toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: #16a34a;
    padding: 12px 18px;
    border-radius: 14px;
    font-weight: bold;
    animation: fadeUp 0.3s ease;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

@keyframes fadeUp {
    from { opacity:0; transform: translateY(20px); }
    to { opacity:1; transform: translateY(0); }
}
</style>
</head>

<body>

<div style="display:flex; gap:10px; margin-bottom:10px;">
<button onclick="finish()">Закончить</button>
<button onclick="openPack()">Открыть пак</button>
</div>

<h2 id="title">Подарки</h2>

<div id="content"><div class="loader"></div></div>

<script>
const tg = window.Telegram.WebApp;
tg.expand();

let packLink = null;

async function loadGifts(){
    document.getElementById("title").innerText = "Подарки";

    const content = document.getElementById("content");
    content.innerHTML = "<div class='loader'></div>";

    const res = await fetch("/api/gifts");
    const gifts = await res.json();

    let html = '<div class="grid">';
    gifts.forEach(g=>{
        html += `
        <div class="card">
            <div>${g.name}</div>
            <button onclick="loadModels('${g.name}')">Открыть</button>
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

    let html = "<button onclick='loadGifts()'>← Назад</button><div class='grid'>";

    models.forEach(m=>{
        html += `
        <div class="card">
            <img src="${m.icon}">
            <div>${m.name}</div>
            <button onclick="add('${gift}','${m.name}')">Добавить</button>
        </div>`;
    });

    html += "</div>";

    content.innerHTML = html;
}

async function add(gift, model){
    showToast("⏳ Добавляем...");

    const res = await fetch("/api/add", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            user_id: tg.initDataUnsafe.user.id,
            gift: gift,
            model: model
        })
    });

    const data = await res.json();

    if(data.ok){
        packLink = data.link;
        showToast("✅ Добавлено");
    } else {
        showToast("Ошибка");
    }
}

function showToast(text){
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerText = text;
    document.body.appendChild(toast);

    setTimeout(()=>toast.remove(), 2000);
}

function openPack(){
    if(packLink) window.open(packLink);
    else showToast("Пак ещё не создан");
}

function finish(){
    tg.close();
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
        {"name": f.replace(".png",""), "icon": f"{url}{quote(f)}"}
        for f in files
    ])


@app.post("/api/add")
async def add(request: Request):
    data = await request.json()

    user_id = data["user_id"]
    gift = data["gift"]
    model = data["model"]

    filename = f"{model}.tgs"
    url = f"{CDN}/{quote(gift)}/{quote(model)}.tgs"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status != 200:
                return JSONResponse({"ok": False})

            with open(filename, "wb") as f:
                f.write(await r.read())

    import requests

    if user_id not in user_packs:
        pack_name = f"giftpack_{user_id}_by_bot"

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/createNewStickerSet",
            data={
                "user_id": user_id,
                "name": pack_name,
                "title": "Gift Pack",
                "emojis": "🎁"
            },
            files={"png_sticker": open(filename,"rb")}
        )

        user_packs[user_id] = pack_name

    else:
        pack_name = user_packs[user_id]

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/addStickerToSet",
            data={
                "user_id": user_id,
                "name": pack_name,
                "emojis": "🎁"
            },
            files={"png_sticker": open(filename,"rb")}
        )

    os.remove(filename)

    return JSONResponse({
        "ok": True,
        "link": f"https://t.me/addstickers/{pack_name}"
    })