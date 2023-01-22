import asyncio
from concurrent.futures import ThreadPoolExecutor
import discord
import os
import random
import torch
from transformers import pipeline

def generate_message(generator, input_messages):
    # Remove any newlines as they interfere with indexing
    messages = [message.replace("\n", "\t") for message in input_messages] + [""]

    # This loop will exit when the AI adds a newline at the end of its message
    while len(messages) < len(input_messages) + 2:
        input_text = "\n".join(messages)
        result_text = generator(input_text)[0]["generated_text"]

        if result_text == input_text:
            if len(messages) <= len(input_messages):
                # Nothing was generated at all
                return None
            else:
                # Nothing was generated in the current iteration
                return messages[len(input_messages)]

        messages = result_text.split("\n")

    return messages[len(input_messages)]

def generate_status(generator):
    (prompt, activity_type) = random.choice([
        ("Competing in", discord.ActivityType.competing),
        ("Listening", discord.ActivityType.listening),
        ("Playing", discord.ActivityType.playing),
        ("Streaming", discord.ActivityType.streaming),
        ("Watching", discord.ActivityType.watching)
    ])

    results = generator(
        prompt,
        temperature=1.0,
        top_k=150,
        max_new_tokens=8,
        num_return_sequences=10
    )

    for result in results:
        result_text = result["generated_text"]

        # Slice up to the end of a sentence to ensure that the message makes sense
        if "." in result_text:
            result_text = result_text.split(".")[0]
        else:
            continue

        # Remove some invalid or boring results
        for stop_word in {"\n", "it", "this", "that"}:
            if stop_word in result_text:
                continue

        # Remove the prompt
        words = result_text.split(" ")[1:]
        if len(words) == 0:
            continue
        name = " ".join(words)

        return discord.Activity(name=name, type=activity_type)

    # All of the results were unsuitable, try again
    return generate_status(generator)

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
        async def on_ready():
            # Remove all slash commands in case they exist from a previous
            # incarnation of Axyn
            commands = discord.app_commands.CommandTree(client)
            commands.clear_commands(guild=None)
            await commands.sync()

            await client.change_presence(activity=generate_status(generator))

        @client.event
        async def on_message(message):
            if message.author == client.user:
                return

            async with message.channel.typing():
                message_texts = [message.content]
                async for other_message in message.channel.history(before=message, limit=15):
                    message_texts.append(other_message.content)
                message_texts.reverse()

                loop = asyncio.get_event_loop()
                our_text = await loop.run_in_executor(executor, generate_message, generator, message_texts)

            if our_text:
                await message.channel.send(our_text)

        client.run(os.environ["DISCORD_TOKEN"])
