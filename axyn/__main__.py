import discord
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def load_model():
    model = AutoModelForCausalLM.from_pretrained("facebook/opt-350m", torch_dtype=torch.bfloat16)
    tokenizer = AutoTokenizer.from_pretrained("facebook/opt-350m", use_fast=False)
    return (model, tokenizer)

def infer(model, tokenizer, input_messages):
    messages = input_messages + [""]

    while len(messages) < len(input_messages) + 2:
        input_text = "\n".join(messages)
        input_ids = tokenizer(input_text, return_tensors="pt").input_ids

        generated_ids = model.generate(
            input_ids,
            num_return_sequences=1,
            max_new_tokens=10,
            do_sample=True,
            temperature=1,
            top_k=25
        )

        result_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        messages = result_text.split("\n")

    return messages[len(input_messages)]

def main():
    (model, tokenizer) = load_model()

    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        async with message.channel.typing():
            message_texts = [message.content]
            async for other_message in message.channel.history(before=message, limit=5):
                message_texts.append(other_message.content)
            message_texts.reverse()

            our_text = infer(model, tokenizer, message_texts)

        if our_text:
            await message.channel.send(our_text)

    client.run(os.environ["DISCORD_TOKEN"])
