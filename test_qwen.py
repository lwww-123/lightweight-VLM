import os
from openai import OpenAI


client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen-plus",
    messages=[
        {
            "role": "user",
            "content": "你好，请用一句话介绍你自己。"
        }
    ]
)

print(response.choices[0].message.content)