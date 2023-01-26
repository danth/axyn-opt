import asyncio
from concurrent.futures import ThreadPoolExecutor
import discord
import nltk
import os
import random
import torch
from transformers import pipeline, StoppingCriteria, StoppingCriteriaList

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

class TokenStoppingCriteria(StoppingCriteria):
    def __init__(self, token):
        self.token = token

    def __call__(self, input_ids: torch.LongTensor, score: torch.FloatTensor, **kwargs):
        # If the last token generated was our target token, then stop
        return input_ids.squeeze()[-1] == self.token

def generate_message(generator, input_messages):
    bad_words = generator.tokenizer(
        ["nigga", "nigger", "nig nog", "fag", "faggot", "slut"],
        add_prefix_space=True,
        add_special_tokens=False
    ).input_ids

    newline = generator.tokenizer("\n", add_special_tokens=False).input_ids[0]

    # Remove any newlines as they interfere with indexing
    messages = [message.replace("\n", "\t") for message in input_messages] + [""]
    prompt = "\n".join(messages)

    results = generator(
        prompt,
        bad_words_ids=bad_words,
        stopping_criteria=StoppingCriteriaList([TokenStoppingCriteria(newline)]),
        max_new_tokens=250,
        return_full_text=False
    )

    return results[0]["generated_text"].strip()

def generate_status(generator):
    bad_words = generator.tokenizer(
        ["nigga", "nigger", "nig nog", "fag", "faggot", "slut"],
        add_prefix_space=True,
        add_special_tokens=False
    ).input_ids

    newline = generator.tokenizer("\n", add_special_tokens=False).input_ids[0]

    (prompt, activity_type) = random.choice([
        ("Competing in", discord.ActivityType.competing),
        ("Listening to", discord.ActivityType.listening),
        ("Playing", discord.ActivityType.playing),
        ("Streaming", discord.ActivityType.streaming),
        ("Watching", discord.ActivityType.watching)
    ])

    results = generator(
        prompt,
        bad_words_ids=bad_words,
        suppress_tokens=[newline],
        temperature=1.0,
        top_k=150,
        max_new_tokens=7,
        num_return_sequences=10,
        return_full_text=False
    )

    for result in results:
        result_text = result["generated_text"]

        # Slice up to the end of a sentence to ensure that the message makes sense
        sentences = nltk.sent_tokenize(result_text)
        if len(sentences) < 2:
            # If there was no split, then the first sentence might have been cut off
            continue

        result_text = sentences[0].strip()

        # If the sentence ended immediately after the prompt, we could have
        # just a piece of punctuation left
        words = nltk.word_tokenize(result_text)
        if len(words) < 2:
            continue

        if activity_type == discord.ActivityType.streaming:
            return discord.Streaming(
                name=result_text,
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )
        else:
            return discord.Activity(name=result_text, type=activity_type)

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
