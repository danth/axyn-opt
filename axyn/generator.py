import discord
import nltk
import random
from transformers import pipeline, StoppingCriteria, StoppingCriteriaList

class TokenStoppingCriteria(StoppingCriteria):
    def __init__(self, token):
        self.token = token

    def __call__(self, input_ids, score, **kwargs):
        # If the last token generated was our target token, then stop
        return input_ids.squeeze()[-1] == self.token

class Generator:
    def __init__(self):
        self.generator = None

    # Returns True when the status needs to be changed to online,
    # False when the model was already loaded
    def load(self):
        if self.generator is not None:
            return False

        self.generator = pipeline(
            "text-generation",
            model="facebook/opt-350m",
            do_sample=True,
            max_new_tokens=5
        )

        self.bad_words = self.generator.tokenizer(
            ["nigga", "nigger", "nig nog", "fag", "faggot", "slut"],
            add_prefix_space=True,
            add_special_tokens=False
        ).input_ids

        self.newline = self.generator.tokenizer(
            "\n",
            add_special_tokens=False
        ).input_ids[0]

        return True

    def unload(self):
        self.generator = None

    def generate_message(self, input_messages):
        # Remove any newlines as they interfere with indexing
        messages = [message.replace("\n", "\t") for message in input_messages] + [""]
        prompt = "\n".join(messages)

        results = self.generator(
            prompt,
            bad_words_ids=self.bad_words,
            stopping_criteria=StoppingCriteriaList([TokenStoppingCriteria(self.newline)]),
            max_new_tokens=250,
            return_full_text=False
        )

        return results[0]["generated_text"].strip()

    def generate_status(self):
        (prompt, activity_type) = random.choice([
            ("Competing in", discord.ActivityType.competing),
            ("Listening to", discord.ActivityType.listening),
            ("Playing", discord.ActivityType.playing),
            ("Streaming", discord.ActivityType.streaming),
            ("Watching", discord.ActivityType.watching)
        ])

        results = self.generator(
            prompt,
            bad_words_ids=self.bad_words,
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

            if activity_type == discord.ActivityType.streaming:
                return discord.Streaming(
                    name=result_text,
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
            else:
                return discord.Activity(name=result_text, type=activity_type)

        # All of the results were unsuitable, try again
        return self.generate_status()

