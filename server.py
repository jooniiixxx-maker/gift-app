import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from urllib.parse import quote, unquote

app = FastAPI()

CDN = "https://cdn.changes.tg/gifts/models"


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

        # убираем ./ в начале
        href_clean = href
        if href_clean.startswith("./"):
            href_clean = href_clean[2:]

        name = unquote(href_clean).strip("/")

        if not name:
            continue

        if name.startswith("?"):
            continue

        if only_dirs and not href.endswith("/"):
            continue

        if only_ext and not name.lower().endswith(only_ext):
            continue

        items.append(name)

    return sorted(list(set(items)))

    soup = BeautifulSoup(html, "html.parser")
    items = []

    for a in soup.find_all("a"):
        href = a.get("href")
        text = a.get_text(strip=True)

        if not href or not text:
            continue

        if href.startswith("?") or href in ["/", "../", "./"]:
            continue

        if text.lower() in ["name", "size", "modified", "up", "list", "grid"]:
            continue

        name = unquote(href).strip("/")

        if name.startswith(".") or name.startswith("?"):
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
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #111827, #2e174f);
    color: white;
    padding: 14px;
}

h2 {
    margin: 10px 0 14px;
    font-size: 24px;
}

input {
    width: 100%;
    box-sizing: border-box;
    border: none;
    border-radius: 16px;
    padding: 13px;
    margin-bottom: 14px;
    font-size: 15px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}

.card {
    background: rgba(255,255,255,0.10);
    border-radius: 20px;
    padding: 12px;
    text-align: center;
    min-height: 150px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.25);
}

.card img {
    width: 90px;
    height: 90px;
    object-fit: contain;
    margin-bottom: 8px;
}

.name {
    font-weight: bold;
    font-size: 14px;
    min-height: 36px;
}

button {
    width: 100%;
    border: none;
    border-radius: 15px;
    padding: 11px;
    margin-top: 8px;
    background: #8b5cf6;
    color: white;
    font-weight: bold;
    font-size: 14px;
}

.back {
    background: #333;
    margin-bottom: 14px;
}
</style>
</head>

<body>
<h2 id="title">🎁 Выбери подарок</h2>
<input id="search" placeholder="Поиск подарка..." oninput="filterItems()">
<div id="content" class="grid"></div>

<script>
const tg = window.Telegram.WebApp;
tg.expand();

let allGifts = [];

async function loadGifts() {
    document.getElementById("title").innerText = "🎁 Выбери подарок";
    document.getElementById("search").style.display = "block";
    document.getElementById("content").className = "grid";
    document.getElementById("content").innerHTML = "Загрузка...";

    const res = await fetch("/api/gifts");
    allGifts = await res.json();
    renderGifts(allGifts);
}

function renderGifts(items) {
    const content = document.getElementById("content");
    content.innerHTML = "";

    items.forEach(gift => {
        const div = document.createElement("div");
        div.className = "card";

        div.innerHTML = `
            <img src="${gift.icon}" onerror="this.style.display='none'">
            <div class="name">${gift.name}</div>
            <button onclick="loadModels('${gift.name.replaceAll("'", "\\\\'")}')">Открыть</button>
        `;

        content.appendChild(div);
    });
}

async function loadModels(giftName) {
    document.getElementById("title").innerText = giftName;
    document.getElementById("search").style.display = "none";

    const content = document.getElementById("content");
    content.className = "";
    content.innerHTML = "<button class='back' onclick='loadGifts()'>← Назад</button><div>Загрузка...</div>";

    const res = await fetch("/api/models/" + encodeURIComponent(giftName));
    const models = await res.json();

    content.innerHTML = "<button class='back' onclick='loadGifts()'>← Назад</button>";

    const grid = document.createElement("div");
    grid.className = "grid";

    models.forEach(model => {
        const div = document.createElement("div");
        div.className = "card";

        div.innerHTML = `
            <img src="${model.icon}" onerror="this.style.display='none'">
            <div class="name">${model.name}</div>
            <button onclick="sendSticker('${giftName.replaceAll("'", "\\\\'")}', '${model.name.replaceAll("'", "\\\\'")}', 'add')">➕ Добавить</button>
            <button onclick="sendSticker('${giftName.replaceAll("'", "\\\\'")}', '${model.name.replaceAll("'", "\\\\'")}', 'find')">📤 Скинуть</button>
        `;

        grid.appendChild(div);
    });

    content.appendChild(grid);
}

function sendSticker(gift, model, action) {
    tg.sendData(JSON.stringify({
        action: action,
        gift: gift,
        model: model
    }));
    tg.close();
}

function filterItems() {
    const q = document.getElementById("search").value.toLowerCase();
    renderGifts(allGifts.filter(g => g.name.toLowerCase().includes(q)));
}

loadGifts();
</script>
</body>
</html>
"""


@app.get("/api/gifts")
async def gifts():
    gifts = await get_items(CDN + "/", only_dirs=True)

    result = []

    for gift in gifts:
        png_url = f"{CDN}/{quote(gift)}/png/"
        png_files = await get_items(png_url, only_ext=".png")

        icon = ""
        if png_files:
            icon = f"{png_url}{quote(png_files[0])}"

        result.append({
            "name": gift,
            "icon": icon
        })

    return JSONResponse(result)


@app.get("/api/gifts")
async def gifts():
    gifts = await get_items(CDN + "/", only_dirs=True)

    result = []

    for gift in gifts:
        result.append({
            "name": gift,
            "icon": ""
        })

    return JSONResponse(result)