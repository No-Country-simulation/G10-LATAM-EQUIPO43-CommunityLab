import os
import discord
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# 1. Definir entorno
N8N_ENV = os.getenv("N8N_ENV", "test")

# 2. Leer la URL Base (Host)
N8N_HOST = os.getenv("N8N_HOST", "http://localhost:5678")

# 3. Elegir el Endpoint según el entorno
N8N_ENDPOINT = (
    os.getenv("N8N_ENDPOINT_TEST")
    if N8N_ENV == "test"
    else os.getenv("N8N_ENDPOINT_PROD")
)

# 4. Construir la URL completa concatenando
N8N_WEBHOOK_URL = f"{N8N_HOST}{N8N_ENDPOINT}"

# 1. Leemos el string del .env
canales_raw = os.getenv("CANALES_PERMITIDOS", "")

# 2. Convertimos ese texto en un conjunto (set) de enteros
if canales_raw:
    CANALES_PERMITIDOS = {
        int(canal_id.strip()) for canal_id in canales_raw.split(",") if canal_id.strip()
    }
else:
    CANALES_PERMITIDOS = set()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id not in CANALES_PERMITIDOS:
        return

    if message.author.bot:
        return

    # es_mencion = client.user in message.mentions

    contenido = message.content

    # if es_mencion:
    #     contenido = contenido.replace(f"<@{client.user.id}>", "").strip()

    if not contenido:
        return

    print(f"[{message.channel.name}] " f"{message.author}: {contenido}")

    response = requests.post(
        N8N_WEBHOOK_URL,
        json={
            "server_id": str(message.guild.id),
            "server_name": message.guild.name,
            # "type": "mention" if es_mencion else "message",
            "message_id": str(message.id),
            "channel_id": str(message.channel.id),
            "channel_name": message.channel.name,
            "user_id": str(message.author.id),
            "username": message.author.name,  # El nombre técnico único
            "display_name": message.author.display_name,  # El apodo amigable en el servidor
            "mention": f"<@{message.author.id}>",
            "message": contenido,
            "timestamp": message.created_at.isoformat(),
        },
    )

    print("Respuesta de n8n:", response.status_code)

    # if es_mencion and response.ok:
    #     print("Respuesta n8n:", repr(response.text))
    #     print("Content-Type:", response.headers.get("Content-Type"))
    #     data = response.json()

    #     if isinstance(data, list):
    #         data = data[0] if data else {}

    #     respuesta = data.get("reply", "No recibí una respuesta de n8n.")

    #     await message.channel.send(respuesta)


client.run(TOKEN)
