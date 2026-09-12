import json
import os
import re

import asyncio
import openai


def extract_javascript_code_block(s: str) -> str:
    """
    Extracts the JavaScript code block from a string following this pattern:
    Code:
    ```javascript
    // code here
    ```
    """
    match = re.search(r'Code:\s*```javascript\n(.*?)```', s, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return ""



api_key = os.getenv("OPENAI_API_KEY")

client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_response_4o(intro, main):
    # Send the prompt to OpenAI's chat API and get the response
    completion = await client.chat.completions.create(
      model="gpt-4o",
      temperature = 0.1,
      messages=[
          {"role": "system", "content": intro},
          {"role": "user", "content": main}
      ]
    )
    response_content = completion.choices[0].message.content # .strip()

    #print(response_content)

    # Extract the response text
    return response_content

async def get_response_4o_mini(intro, main):
    # Send the prompt to OpenAI's chat API and get the response
    completion = await client.chat.completions.create(
      model="gpt-4o-mini",
      temperature = 0.5,
      messages=[
          {"role": "system", "content": intro},
          {"role": "user", "content": main}
      ]
    )
    response_content = completion.choices[0].message.content # .strip()

    #print(response_content)

    # Extract the response text
    return response_content


async def get_response_4_nano(intro, main):
    # Send the prompt to OpenAI's chat API and get the response
    completion = await client.chat.completions.create(
      model="gpt-4.1-nano",
      temperature = 0.2,
      messages=[
          {"role": "system", "content": intro},
          {"role": "user", "content": main}
      ]
    )
    response_content = completion.choices[0].message.content # .strip()

    #print(response_content)

    # Extract the response text
    return response_content


async def get_response_4_1(intro, main):
    # Send the prompt to OpenAI's chat API and get the response
    completion = await client.chat.completions.create(
      model="gpt-4.1",
      temperature = 0.1,
      messages=[
          {"role": "system", "content": intro},
          {"role": "user", "content": main}
      ]
    )
    response_content = completion.choices[0].message.content # .strip()

    return response_content


async def get_response_o3(intro, main):
    # Send the prompt to OpenAI's chat API and get the response
    completion = await client.chat.completions.create(
      model="o4-mini",
      messages=[
          {"role": "system", "content": intro},
          {"role": "user", "content": main}
      ]
    )
    response_content = completion.choices[0].message.content # .strip()

    return response_content


def rule_finder(demo_name):
    path = f"./data/rules/{demo_name}_rules.json"

    if not os.path.exists(path):
        return [],[]
    
    with open(path, "r") as f:
        rules_data = json.load(f)

    rules = [entry["rule"] for entry in rules_data if "rule" in entry]
    explanations = [entry["explanation"] for entry in rules_data if "explanation" in entry]
    
    return rules, explanations




