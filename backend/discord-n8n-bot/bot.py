import os
import discord
import requests

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")


@client.event
async def on_message(message):
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
        "https://granite-alone-useable.ngrok-free.dev/webhook/discord-message",
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