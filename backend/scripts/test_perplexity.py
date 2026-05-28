"""Smoke test for the expanded Perplexity company intelligence enrichment."""
import asyncio
import sys
import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from firstknock.pipeline.enrichment.company import enrich_companies


async def main():
    test_companies = ["Stripe", "Figma", "Notion"]
    print(f"Testing company intelligence enrichment for: {test_companies}\n")

    results = await enrich_companies(test_companies)

    for company, data in results.items():
        print(f"{'='*50}")
        print(f"  {company}")
        print(f"{'='*50}")
        for k, v in data.items():
            if v is not None and v != [] and v != "":
                print(f"  {k:<25} {v}")
        print()

    all_empty = all(
        all(v is None or v == [] for v in d.values()) for d in results.values()
    )
    if all_empty:
        print("FAIL: all results empty — check PERPLEXITY_API_KEY")
        sys.exit(1)
    else:
        print("OK: enrichment working")


asyncio.run(main())
