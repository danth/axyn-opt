import asyncio
from concurrent.futures import ThreadPoolExecutor
import discord
import os

from axyn.generator import Generator

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
    client = discord.Client(intents=intents, status=discord.Status.idle)

    generator = Generator()

    tasks = {}

    with ThreadPoolExecutor(max_workers=1) as executor:
        async def appear_idle():
            await client.change_presence(status=discord.Status.idle)

        async def appear_online():
            loop = asyncio.get_event_loop()
            activity = await loop.run_in_executor(executor, generator.generate_status)
            await client.change_presence(status=discord.Status.online, activity=activity)

        async def unload_later():
            await asyncio.sleep(15 * 60)
            generator.unload()
            await appear_idle()

        async def load():
            loop = asyncio.get_event_loop()
            status_changed = await loop.run_in_executor(executor, generator.load)

            if status_changed:
                asyncio.create_task(appear_online())

        async def reply_to(message):
            if "unload_later" in tasks:
                tasks["unload_later"].cancel()

            async with message.channel.typing():
                [_, texts] = await asyncio.gather(load(), collect_texts(message))

                loop = asyncio.get_event_loop()
                our_text = await loop.run_in_executor(executor, generator.generate_message, texts)

            if our_text:
                await message.channel.send(our_text)

            tasks["unload_later"] = asyncio.create_task(unload_later())

        @client.event
        async def on_ready():
            # Remove all slash commands in case they exist from a previous
            # incarnation of Axyn
            commands = discord.app_commands.CommandTree(client)
            commands.clear_commands(guild=None)
            await commands.sync()

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
