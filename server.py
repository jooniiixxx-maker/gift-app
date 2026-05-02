from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
    <head>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
    </head>
    <body>
        <h2>Gift App</h2>

        <input id="gift" placeholder="Gift name"><br><br>
        <input id="model" placeholder="Model name"><br><br>

        <button onclick="send()">Отправить</button>

        <script>
        function send() {
            let data = {
                gift: document.getElementById("gift").value,
                model: document.getElementById("model").value
            };
            Telegram.WebApp.sendData(JSON.stringify(data));
        }
        </script>
    </body>
    </html>
    """