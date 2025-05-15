import asyncio
from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(
        api_key="sk-oW8aVGDZPSt5YdusGvAG16j6X8IasdTik2sWCFMkHAQnPtma",
        base_url="https://api.fe8.cn/v1"
    )

    chat_completion = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "讲个笑话",
            }
        ],
        model="gpt-4o-mini"
    )
    print(chat_completion.choices[0].message.content)

# 运行入口
if __name__ == "__main__":
    asyncio.run(main())
