import asyncio
import anthropic
import openai
from firstknock.config import settings


async def test_anthropic():
    print("Testing Anthropic (Claude)...")
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        print("  Claude:  OK —", response.content[0].text.strip())
    except anthropic.AuthenticationError:
        print("  Claude:  FAIL — invalid or expired API key")
    except Exception as e:
        print(f"  Claude:  FAIL — {e}")


async def test_openai():
    print("Testing OpenAI...")
    try:
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        print("  OpenAI:  OK —", response.choices[0].message.content.strip())
    except openai.AuthenticationError:
        print("  OpenAI:  FAIL — invalid or expired API key")
    except Exception as e:
        print(f"  OpenAI:  FAIL — {e}")


async def main():
    await test_anthropic()
    await test_openai()


asyncio.run(main())
