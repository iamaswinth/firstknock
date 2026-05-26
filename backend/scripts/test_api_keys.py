"""
Quick test for all external API keys configured in .env.
Usage: python scripts/test_api_keys.py
"""
import asyncio
import anthropic
import httpx
from firstknock.config import settings


async def test_perplexity():
    print("\n── Perplexity ──────────────────────────────────")
    if not settings.perplexity_api_key:
        print("  SKIP  PERPLEXITY_API_KEY not set in .env")
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
                    "max_tokens": 10,
                },
            )
        if resp.status_code == 200:
            reply = resp.json()["choices"][0]["message"]["content"].strip()
            print(f"  OK    status=200  reply={reply!r}")
        else:
            print(f"  FAIL  status={resp.status_code}  body={resp.text[:200]}")
    except Exception as exc:
        print(f"  FAIL  {exc}")


async def test_github():
    print("\n── GitHub ──────────────────────────────────────")
    if not settings.github_token:
        print("  SKIP  GITHUB_TOKEN not set in .env")
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {settings.github_token}"},
            )
        if resp.status_code == 200:
            login = resp.json().get("login")
            print(f"  OK    status=200  authenticated as: {login}")
        else:
            print(f"  FAIL  status={resp.status_code}  body={resp.text[:200]}")
    except Exception as exc:
        print(f"  FAIL  {exc}")


async def test_anthropic():
    print("\n── Anthropic ───────────────────────────────────")
    if not settings.anthropic_api_key:
        print("  SKIP  ANTHROPIC_API_KEY not set in .env")
        return

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        )
        reply = msg.content[0].text.strip()
        print(f"  OK    reply={reply!r}")
    except Exception as exc:
        print(f"  FAIL  {exc}")


async def main():
    print("API Key Validation")
    print("=" * 50)
    await test_perplexity()
    await test_github()
    await test_anthropic()
    print("\n" + "=" * 50)


asyncio.run(main())
