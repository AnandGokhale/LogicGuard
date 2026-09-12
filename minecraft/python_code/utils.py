import json

import os


import asyncio
import openai


import re

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
      model="o3-mini",
      messages=[
          {"role": "system", "content": intro},
          {"role": "user", "content": main}
      ]
    )
    response_content = completion.choices[0].message.content # .strip()

    return response_content



