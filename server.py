import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from urllib.parse import quote, unquote

app = FastAPI()

CDN = "https://cdn.changes.tg/gifts/models"


async def get_links(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.find_all("a"):
        href = a.get("href")
        if href and href not in ["../", "/"]:
            links.append(unquote(href.strip("/")))

    return links


@app.get("/")
async def index():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #151515, #2b1b4d);
            color: white;
            padding: 16px;
        }

        h2 {
            margin-top: 0;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }

        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 18px;
            padding: 12px;
            text-align: center;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        }

        .card img {
            width: 90px;
            height: 90px;
            object-fit: contain;
        }

        button {
            width: 100%;
            border: none;
            border-radius: 14px;
            padding: 10px;
            margin-top: 8px;
            background: #8b5cf6;
            color: white;
            font-size: 14px;
            font-weight: bold;
        }

        .back {
            background: #333;
            margin-bottom: 12px;
        }

        input {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            border-radius: 14px;
            border: none;
            margin-bottom: 12px;
            font-size: 15px;
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

let allItems = [];
let currentGift = null;

async function loadGifts() {
    const res = await fetch("/api/gifts");
    allItems = await res.json();

    renderGifts(allItems);
}

function renderGifts(items) {
    document.getElementById("title").innerText = "🎁 Выбери подарок";
    document.getElementById("search").style.display = "block";

    const content = document.getElementById("content");
    content.innerHTML = "";
    content.className = "grid";

    items.forEach(gift => {
        const div = document.createElement("div");
        div.className = "card";

        div.innerHTML = `
            <img src="${gift.icon}" onerror="this.style.display='none'">
            <div>${gift.name}</div>
            <button onclick="loadModels('${gift.name}')">Открыть</button>
        `;

        content.appendChild(div);
    });
}

async function loadModels(giftName) {
    currentGift = giftName;

    document.getElementById("title").innerText = giftName;
    document.getElementById("search").style.display = "none";

    const content = document.getElementById("content");
    content.innerHTML = "<button class='back' onclick='loadGifts()'>← Назад</button>";
    content.className = "";

    const res = await fetch("/api/models/" + encodeURIComponent(giftName));
    const models = await res.json();

    const grid = document.createElement("div");
    grid.className = "grid";

    models.forEach(model => {
        const div = document.createElement("div");
        div.className = "card";

        div.innerHTML = `
            <img src="${model.icon}">
            <div>${model.name}</div>
            <button onclick="sendSticker('${giftName}', '${model.name}', 'add')">➕ Добавить</button>
            <button onclick="sendSticker('${giftName}', '${model.name}', 'find')">📤 Просто скинуть</button>
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

    const filtered = allItems.filter(item =>
        item.name.toLowerCase().includes(q)
    );

    renderGifts(filtered);
}

loadGifts();
</script>

</body>
</html>
""")


@app.get("/api/gifts")
async def gifts():
    gifts = await get_links(CDN)

    result = []

    for gift in gifts:
        models_url = f"{CDN}/{quote(gift)}/png/"
        icon = f"{models_url}1.png"

        result.append({
            "name": gift,
            "icon": icon
        })

    return JSONResponse(result)


@app.get("/api/models/{gift_name}")
async def models(gift_name: str):
    url = f"{CDN}/{quote(gift_name)}/png/"
    files = await get_links(url)

    result = []

    for file in files:
        if file.endswith(".png"):
            model_name = file.replace(".png", "")

            result.append({
                "name": model_name,
                "icon": f"{url}{quote(file)}"
            })

    return JSONResponse(result)