import asyncio
from firstknock.pipeline.parsers.router import parse_file

with open("tests/fixtures/sample_resumes/resume.pdf", "rb") as f:
    data = f.read()

result = asyncio.run(parse_file(data, "pdf"))
print("Source type:", result["source_type"])
print("Total chars:", len(result["raw_text"]))
print()
print("--- First 500 chars ---")
print(result["raw_text"][:500])
print()
print("--- Last 200 chars ---")
print(result["raw_text"][-200:])
