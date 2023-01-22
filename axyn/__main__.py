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

    print(infer(model, tokenizer, [
        "Hello",
        "Hi",
        "How are you?"
    ]))
