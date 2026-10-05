import os
import discord
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

N8N_ENV = os.getenv("N8N_ENV", "test")

N8N_WEBHOOK_URL = (
    os.getenv("N8N_WEBHOOK_TEST")
    if N8N_ENV == "test"
    else os.getenv("N8N_WEBHOOK_PROD")
)

CANALES_PERMITIDOS = {1552066129311047750} # general

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

    es_mencion = client.user in message.mentions

    contenido = message.content

    if es_mencion:
        contenido = contenido.replace(
            f"<@{client.user.id}>", ""
        ).strip()

    print(
        f"[{message.channel.name}] "
        f"{message.author}: {contenido}"
    )

    response = requests.post(
        N8N_WEBHOOK_URL,
        json={
            "type": "mention" if es_mencion else "message",
            "message_id": str(message.id),
            "channel_id": str(message.channel.id),
            "channel_name": message.channel.name,
            "user_id": str(message.author.id),
            "username": str(message.author),
            "mention": f"<@{message.author.id}>",
            "message": contenido,
            "timestamp": message.created_at.isoformat()
        }
    )

    print("Respuesta de n8n:", response.status_code)

    if es_mencion and response.ok:
        data = response.json()

        if isinstance(data, list):
            data = data[0] if data else {}

        respuesta = data.get(
            "reply",
            "No recibí una respuesta de n8n."
        )

        await message.channel.send(respuesta)

client.run(TOKEN)