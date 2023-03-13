import asyncio
from concurrent.futures import ThreadPoolExecutor
import discord
import os
import random

from axyn.generator import Generator
from axyn.voice import VoiceManager

async def collect_texts(message):
    texts = [message.content]
    texts_length = len(message.content)

    async for other_message in message.channel.history(before=message):
        # Limit the prompt to a reasonable length (counted in characters)
        if texts_length >= 1000:
            break

        texts.append(other_message.content)
        texts_length += len(other_message.content)

    texts.reverse()

    return texts

def main():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    generator = Generator()
    tasks = {}
    voice = VoiceManager()

    async def clear_commands():
        commands = discord.app_commands.CommandTree(client)
        commands.clear_commands(guild=None)
        await commands.sync()

    async def rotate_status():
        while True:
            activity = await generator.generate_status()
            await client.change_presence(activity=activity)

            # Wait between 1 and 12 hours
            time_to_wait = random.randint(60 * 60, 60 * 60 * 12)
            await asyncio.sleep(time_to_wait)

    @client.event
    async def on_ready():
        asyncio.create_task(clear_commands())
        asyncio.create_task(rotate_status())

    async def reply_to(message):
        async with message.channel.typing():
            texts = await collect_texts(message)
            our_text = await generator.generate_message(texts)

        if our_text:
            asyncio.create_task(message.channel.send(our_text))

            if isinstance(message.author, discord.Member) and message.author.voice:
                asyncio.create_task(voice.play_tts(message.author.voice.channel, our_text))

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        # If we are still responding to a previous message, cancel that
        # task. This prevents Axyn from building up a backlog of tasks for
        # the same channel, so it won't send multiple disjointed messages
        # when it catches up.
        if message.channel.id in tasks:
            tasks[message.channel.id].cancel()

        tasks[message.channel.id] = asyncio.create_task(reply_to(message))

    client.run(os.environ["DISCORD_TOKEN"])
