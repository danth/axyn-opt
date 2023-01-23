import asyncio
from concurrent.futures import ThreadPoolExecutor
import discord
import os
import random
import torch
from transformers import pipeline

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

        for stop_word in {"nigga", "nigger", "nig nog", "fag", "whore", "slut"}:
            if stop_word in result_text:
                # Try again for a less offensive result
                return generate_message(generator, input_messages)

        messages = result_text.split("\n")

    return messages[len(input_messages)]

def generate_status(generator):
    (prompt, activity_type) = random.choice([
        ("Competing in", discord.ActivityType.competing),
        ("Listening to", discord.ActivityType.listening),
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
        name = result_text.removeprefix(prompt).strip()
        if not name:
            continue

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

    reply_tasks = {}

    with ThreadPoolExecutor(max_workers=1) as executor:
        async def reply_to(message):
            async with message.channel.typing():
                texts = await collect_texts(message)

                loop = asyncio.get_event_loop()
                our_text = await loop.run_in_executor(executor, generate_message, generator, texts)

            if our_text:
                await message.channel.send(our_text)

        async def rotate_status():
            while True:
                loop = asyncio.get_event_loop()
                activity = await loop.run_in_executor(executor, generate_status, generator)

                await client.change_presence(activity=activity)

                # Wait between 1 hour and 12 hours before changing the status again
                time_to_wait = random.randint(60 * 60, 60 * 60 * 12)
                await asyncio.sleep(time_to_wait)

        @client.event
        async def on_ready():
            # Remove all slash commands in case they exist from a previous
            # incarnation of Axyn
            commands = discord.app_commands.CommandTree(client)
            commands.clear_commands(guild=None)
            await commands.sync()

            asyncio.create_task(rotate_status())

        @client.event
        async def on_message(message):
            if message.author == client.user:
                return

            # If we are still responding to a previous message, cancel that
            # task. This prevents Axyn from building up a backlog of tasks for
            # the same channel, so it won't send multiple disjointed messages
            # when it catches up.
            if message.channel.id in reply_tasks:
                reply_tasks[message.channel.id].cancel()

            reply_tasks[message.channel.id] = asyncio.create_task(reply_to(message))


        client.run(os.environ["DISCORD_TOKEN"])
