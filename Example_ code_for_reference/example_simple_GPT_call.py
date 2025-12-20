#!/usr/bin/env python3

import sys
from openai import OpenAI

def get_gpt_response(prompt):
    OPENAI_API_KEY_FILE = "openai_api_key.txt"
    # Get OPENAPI key from a file
    try:
        with open(OPENAI_API_KEY_FILE, 'r') as f:
            OPENAI_API_KEY = f.read().strip()
    except FileNotFoundError:
        print(f"ERROR: API key file '{OPENAI_API_KEY_FILE}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An error occurred while reading the API key file: {e}")
        sys.exit(1)
    # Check the API key is valid
    if not OPENAI_API_KEY.startswith("sk-"):
        print(f"ERROR: Invalid API key found in '{OPENAI_API_KEY_FILE}'")
        sys.exit(1)

    # Create object 'client' to handle future API requests to OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        
        #model="gpt-3.5-turbo",
        model="gpt-4o-mini",
        #model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,        # "Creativity" lower values less random
        top_p=0.5,              # "Focus vs diversity" lower values more focus/coherance, less diversity
        frequency_penalty=0.5,  # "Repetition of tokens (concepts, kinda)" higher values penalise repetition based on frequency
        presence_penalty=0.5    # "Repetition or tokens (concepts, kinda)" higher higher values penalise repetition based on any presence
    )
    text = response.choices[0].message.content.strip()
    total_tokens = response.usage.total_tokens
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens

    return text, total_tokens, prompt_tokens, completion_tokens

if __name__ == "__main__":

    prompt = "what it the capital of france?"

    # Get the response from GPT
    response, total_tokens, prompt_tokens, completion_tokens = get_gpt_response(prompt)

    print("Response:")
    print(response)