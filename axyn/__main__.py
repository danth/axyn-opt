import asyncio
from concurrent.futures import ThreadPoolExecutor
import discord
import os
import torch
from transformers import pipeline

def infer(generator, input_messages):
    messages = input_messages + [""]

    while len(messages) < len(input_messages) + 2:
        input_text = "\n".join(messages)
        result_text = generator(input_text)[0]["generated_text"]
        messages = result_text.split("\n")

    return messages[len(input_messages)]

def main():
    generator = pipeline(
        "text-generation",
        model="facebook/opt-350m",
        do_sample=True,
        max_new_tokens=5
    )

    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    with ThreadPoolExecutor(max_workers=1) as executor:
        @client.event
        async def on_message(message):
            if message.author == client.user:
                return

            async with message.channel.typing():
                message_texts = [message.content]
                async for other_message in message.channel.history(before=message, limit=5):
                    message_texts.append(other_message.content)
                message_texts.reverse()

                loop = asyncio.get_event_loop()
                our_text = await loop.run_in_executor(executor, infer, generator, message_texts)

            if our_text:
                await message.channel.send(our_text)

        client.run(os.environ["DISCORD_TOKEN"])
