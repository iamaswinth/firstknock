from firstknock.pipeline.resolution.skill_canonicalizer import canonicalize_skill, canonicalize_skill_list
from firstknock.pipeline.resolution.date_normalizer import normalize_date, date_range_months

print("=== STRUCTURAL CLEANUP ===")
print("Next.js 14      ->", canonicalize_skill("Next.js 14"))
print("BGE-Reranker-v2 ->", canonicalize_skill("BGE-Reranker-v2"))
print("AWS RDS (MySQL) ->", canonicalize_skill("AWS RDS (MySQL)"))
print("Pinecone (Dense + Sparse) ->", canonicalize_skill("Pinecone (Dense + Sparse)"))
print("GitHub Actions (CI/CD)    ->", canonicalize_skill("GitHub Actions (CI/CD)"))
print("NeonDB (Postgres)         ->", canonicalize_skill("NeonDB (Postgres)"))

print()
print("=== SHORTHAND ALIASES ===")
print("py       ->", canonicalize_skill("py"))
print("JS       ->", canonicalize_skill("JS"))
print("k8s      ->", canonicalize_skill("k8s"))
print("postgres ->", canonicalize_skill("postgres"))
print("ts       ->", canonicalize_skill("ts"))

print()
print("=== DEDUPLICATION ===")
raw = ["React", "ReactJS", "React", "Next.js 14", "Next.js"]
print("Input: ", raw)
print("Output:", canonicalize_skill_list(raw))

print()
print("=== DATE NORMALIZATION ===")
print("Jan 2026  ->", normalize_date("Jan 2026"))
print("July 2025 ->", normalize_date("July 2025"))
print("Dec 2025  ->", normalize_date("Dec 2025"))
print("Sep 2023  ->", normalize_date("Sep 2023"))
print("Present   ->", normalize_date("Present"))
print("Current   ->", normalize_date("Current"))
print("None      ->", normalize_date(None))

print()
print("=== DURATION ===")
print("July 2025 -> Dec 2025 :", date_range_months("2025-07", "2025-12"), "months (expect 5)")
print("Jan 2026  -> Present  :", date_range_months("2026-01", None), "months")
print("Sep 2023  -> Present  :", date_range_months("2023-09", None), "months")

print()
print("=== PASS CRITERIA ===")
checks = [
    ("Next.js 14 -> Next.js",       canonicalize_skill("Next.js 14") == "Next.js"),
    ("BGE-Reranker-v2 -> BGE-Reranker", canonicalize_skill("BGE-Reranker-v2") == "BGE-Reranker"),
    ("AWS RDS (MySQL) -> AWS RDS",  canonicalize_skill("AWS RDS (MySQL)") == "AWS RDS"),
    ("Jan 2026 -> 2026-01",         normalize_date("Jan 2026") == "2026-01"),
    ("July 2025 -> 2025-07",        normalize_date("July 2025") == "2025-07"),
    ("Dec 2025 -> 2025-12",         normalize_date("Dec 2025") == "2025-12"),
    ("Present -> None",             normalize_date("Present") is None),
    ("5 months Jul-Dec 2025",       date_range_months("2025-07", "2025-12") == 5),
]
for label, passed in checks:
    print(f"  {'OK' if passed else 'FAIL'}  {label}")
