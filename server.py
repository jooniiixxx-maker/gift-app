import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from urllib.parse import quote, unquote

app = FastAPI()

CDN = "https://cdn.changes.tg/gifts/models"


async def get_items(url, only_dirs=False, only_ext=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=20) as r:
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

        if not name or name.startswith("?"):
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
body{margin:0;font-family:Arial;background:linear-gradient(135deg,#111827,#2e174f);color:white;padding:16px}
h2{font-size:26px}
input{width:100%;box-sizing:border-box;border:none;border-radius:16px;padding:14px;margin-bottom:14px;font-size:16px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.card{background:rgba(255,255,255,.1);border-radius:20px;padding:12px;text-align:center}
.card img{width:95px;height:95px;object-fit:contain}
.name{font-weight:bold;min-height:36px}
button{width:100%;border:none;border-radius:15px;padding:12px;margin-top:8px;background:#8b5cf6;color:white;font-weight:bold}
.back{background:#333;margin-bottom:14px}
</style>
</head>
<body>

<h2 id="title">🎁 Выбери подарок</h2>
<input id="search" placeholder="Поиск подарка..." oninput="filterItems()">
<div id="content">Загрузка...</div>

<script>
const tg = window.Telegram.WebApp;
tg.expand();

let allGifts = [];

async function loadGifts(){
    const content = document.getElementById("content");
    content.innerHTML = "Загрузка...";
    content.className = "";

    try {
        const res = await fetch("/api/gifts");
        allGifts = await res.json();
        renderGifts(allGifts);
    } catch(e) {
        content.innerHTML = "Ошибка загрузки подарков";
    }
}

function renderGifts(items){
    const content = document.getElementById("content");
    content.className = "grid";
    content.innerHTML = "";

    items.forEach(gift=>{
        const div = document.createElement("div");
        div.className = "card";
        div.innerHTML = `
            <div class="name">${gift.name}</div>
            <button onclick="loadModels('${gift.name.replaceAll("'", "\\\\'")}')">Открыть</button>
        `;
        content.appendChild(div);
    });
}

async function loadModels(giftName){
    document.getElementById("title").innerText = giftName;
    document.getElementById("search").style.display = "none";

    const content = document.getElementById("content");
    content.className = "";
    content.innerHTML = "<button class='back' onclick='backToGifts()'>← Назад</button><div>Загрузка моделей...</div>";

    try {
        const res = await fetch("/api/models?gift=" + encodeURIComponent(giftName));
        const models = await res.json();

        content.innerHTML = "<button class='back' onclick='backToGifts()'>← Назад</button>";

        if (!models.length) {
            content.innerHTML += "<div>Модели не найдены</div>";
            return;
        }

        const grid = document.createElement("div");
        grid.className = "grid";

        models.forEach(model=>{
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

    } catch(e) {
        content.innerHTML += "<div>Ошибка загрузки моделей</div>";
    }
}

function backToGifts(){
    document.getElementById("title").innerText = "🎁 Выбери подарок";
    document.getElementById("search").style.display = "block";
    renderGifts(allGifts);
}

function sendSticker(gift, model, action){
    tg.sendData(JSON.stringify({action, gift, model}));
    tg.close();
}

function filterItems(){
    const q = document.getElementById("search").value.toLowerCase();
    renderGifts(allGifts.filter(g=>g.name.toLowerCase().includes(q)));
}

loadGifts();
</script>
</body>
</html>
"""


@app.get("/api/gifts")
async def gifts():
    gifts = await get_items(CDN + "/", only_dirs=True)
    return JSONResponse([{"name": gift} for gift in gifts])


@app.get("/api/models")
async def models(gift: str = Query(...)):
    png_url = f"{CDN}/{quote(gift)}/png/"
    png_files = await get_items(png_url, only_ext=".png")

    result = []

    for file in png_files:
        model_name = file.replace(".png", "")
        result.append({
            "name": model_name,
            "icon": f"{png_url}{quote(file)}"
        })

    return JSONResponse(result)