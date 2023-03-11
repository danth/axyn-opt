import asyncio
from concurrent.futures import ThreadPoolExecutor
import discord
import functools
import nltk
import random
from transformers import pipeline, StoppingCriteria, StoppingCriteriaList

BAD_WORDS = ["nigga", "nigger", "nig nog", "fag", "faggot", "slut"]

class TokenStoppingCriteria(StoppingCriteria):
    def __init__(self, token):
        self.token = token

    def __call__(self, input_ids, score, **kwargs):
        # If the last token generated was our target token, then stop
        return input_ids.squeeze()[-1] == self.token

class Generator:
    def __init__(self):
        self.generator = pipeline(
            "text-generation",
            model="facebook/opt-350m",
            do_sample=True,
            max_new_tokens=5
        )

        self.newline = self.generator.tokenizer(
            "\n",
            add_special_tokens=False
        ).input_ids[0]

        # Generation can take a long time, so we run it on a separate thread to
        # avoid losing connection to Discord in the meantime. This also queues
        # up tasks so that only one is running at a time.
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def generate(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            functools.partial(self.generator, *args, **kwargs)
        )

    async def generate_message(self, input_messages):
        # Remove any newlines as they interfere with indexing
        messages = [message.replace("\n", "\t") for message in input_messages] + [""]
        prompt = "\n".join(messages)

        results = await self.generate(
            prompt,
            stopping_criteria=StoppingCriteriaList([TokenStoppingCriteria(self.newline)]),
            max_new_tokens=250,
            return_full_text=False
        )
        result = results[0]["generated_text"].strip()

        if any(bad_word in result.lower() for bad_word in BAD_WORDS):
            return None

        return result

    async def generate_status(self):
        (prompt, activity_type) = random.choice([
            ("Competing in", discord.ActivityType.competing),
            ("Listening to", discord.ActivityType.listening),
            ("Playing", discord.ActivityType.playing),
            ("Streaming", discord.ActivityType.streaming),
            ("Watching", discord.ActivityType.watching)
        ])

        results = await self.generate(
            prompt,
            suppress_tokens=[self.newline],
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

            if any(bad_word in result_text.lower() for bad_word in BAD_WORDS):
                continue

            if activity_type == discord.ActivityType.streaming:
                return discord.Streaming(
                    name=result_text,
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
            else:
                return discord.Activity(name=result_text, type=activity_type)

        # All of the results were unsuitable, try again
        return await self.generate_status()

