from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from huggingface_hub import InferenceClient
from app.utils.constants import MixtralConfig
from app.utils.config import HUGGINGFACE_TOKEN, OPENAI_API_KEY,ANTHROPIC_API_KEY
import re
import ast
import json
from openai import OpenAI
from typing import List
import anthropic




from cachetools import TTLCache

cache_client = TTLCache(maxsize=10000, ttl=1800)

processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

client = InferenceClient("mistralai/Mixtral-8x7B-Instruct-v0.1",token=HUGGINGFACE_TOKEN)


def generate_img_desc(image: Image.Image):
    inputs = processor(image, return_tensors="pt")
    out = model.generate(**inputs)
    return processor.decode(out[0], skip_special_tokens=True)

def generate_img_desc_multi(images: List[Image.Image]):
    inputs = processor(images, return_tensors="pt", padding=True, truncation=True)
    out = model.generate(**inputs)
    return [processor.decode(out[i], skip_special_tokens=True) for i in range(len(images))]


def generate_mixtral_content(prompt, retry=True):
    try:
        temperature = float(MixtralConfig.TEMPERATURE)
        if temperature < 1e-2:
            temperature = 1e-2
        top_p = float(MixtralConfig.TOP_P)

        generate_kwargs = dict(
            temperature=MixtralConfig.TEMPERATURE,
            max_new_tokens=MixtralConfig.MAX_NEW_TOKEN,
            top_p=top_p,
            repetition_penalty=MixtralConfig.REPETITION_PENALTY,
            do_sample=True,
            seed=42,
        )
        formatted_prompt = f"<s>[INST] {prompt} [/INST]"
        stream = client.text_generation(formatted_prompt, **generate_kwargs, stream=True, details=True, return_full_text=False)
        output = ""
        for response in stream:
            output += response.token.text
        return output
    except Exception as e:
        print(f"An error occurred: {e}")
        if retry:
            return generate_mixtral_content(prompt, retry=False)  # Recursive call with retry=False
        return None

        
def remove_s_tag_from_end(text: str) -> str:
    if text.endswith("</s>"):
        return text[:-len("</s>")]
    return text

def remove_s_tag(text):
    if "</s>" in text:
        text = text.replace("</s>", "")
    return text

def extract_json_from_string(data_string):
    match = re.search(r'\{[^{}]*\}', data_string)
    if match:
        data_inside_brackets = match.group()
        # Remove any trailing characters that are not part of the JSON-like string
        data_inside_brackets = re.sub(r'</s>.*', '', data_inside_brackets)
        # Convert the JSON-like string to a Python object
        if data_inside_brackets[-2] == ",":
            result = data_inside_brackets[:-2] + data_inside_brackets[-1]
        else:
            result = data_inside_brackets
        data_object = json.loads(result)
        return data_object
    else:
        return None
    
def generate_openai_content(prompt):
    # Get the API key from user data
    api_key = OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in user data")

    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    # Request completion from OpenAI
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        # model="gpt-4-turbo-2024-04-09",
        # response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to output JSON. and do not use the following words: opt, android"},
            {"role": "user", "content": prompt}
        ]
    )

    data = json.loads(response.choices[0].message.content)
    # first_key = next(iter(data))
    # first_key_content = data[first_key]
    return data

def generate_anthropic_content(prompt):
   try:
       
    client = anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY,
    )
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt
            },
            {
                "role": "assistant",
                "content": ""
            }
        ]
    )
    print(message.content[0].text)
    data = json.loads(message.content[0].text)
    return data
   except Exception as e:
       print(e)
       return None
