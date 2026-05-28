"""Smoke test for LinkedIn enrichment via Apify dev_fusion/linkedin-profile-scraper."""
import asyncio
import sys
import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from firstknock.pipeline.enrichment.linkedin import enrich_linkedin


async def main():
    # Use a well-known public profile for testing
    test_url = "https://www.linkedin.com/in/satyanadella/"
    print(f"Testing LinkedIn enrichment for: {test_url}\n")

    result = await enrich_linkedin(test_url)

    print(f"{'='*50}")
    print(f"  Profile")
    print(f"{'='*50}")
    print(f"  headline:             {result.headline}")
    print(f"  location:             {result.location}")
    print(f"  connections:          {result.connections}")
    print(f"  followers:            {result.followers}")
    print(f"  recommendations:      {result.recommendations_count}")
    print(f"  skills ({len(result.skills)}):          {result.skills[:5]}")
    print()
    print(f"  Experience ({len(result.experience)} positions):")
    for exp in result.experience:
        current = " [current]" if exp.is_current else ""
        print(f"    - {exp.title} @ {exp.company} ({exp.start_date} to {exp.end_date or 'present'}){current}")

    if not result.headline and not result.experience:
        print("\nFAIL: empty result — check APIFY_API_KEY or actor input format")
        sys.exit(1)
    else:
        print("\nOK: LinkedIn enrichment working")


asyncio.run(main())
