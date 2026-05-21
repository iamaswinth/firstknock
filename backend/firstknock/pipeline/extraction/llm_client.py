import anthropic
from firstknock.config import settings
from .prompts import SYSTEM_PROMPT, EXTRACT_TOOL

# Sonnet 4.6 pricing per million tokens
_COST_PER_M_INPUT = 3.0
_COST_PER_M_OUTPUT = 15.0


async def call_extraction(text: str) -> dict:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=settings.extraction_model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_resume"},
        messages=[{"role": "user", "content": text}],
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens / 1_000_000 * _COST_PER_M_INPUT) + (output_tokens / 1_000_000 * _COST_PER_M_OUTPUT)
    print(f"[extraction] tokens: {input_tokens} in / {output_tokens} out | est. cost: ${cost:.4f}")

    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_resume":
            return block.input

    raise ValueError("No tool_use block in response")
