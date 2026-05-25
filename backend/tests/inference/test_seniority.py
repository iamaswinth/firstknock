from firstknock.pipeline.inference.seniority import compute_seniority


def test_junior():
    assert compute_seniority(0) == "junior"
    assert compute_seniority(6) == "junior"
    assert compute_seniority(11) == "junior"


def test_mid():
    assert compute_seniority(12) == "mid"
    assert compute_seniority(24) == "mid"
    assert compute_seniority(35) == "mid"


def test_senior():
    assert compute_seniority(36) == "senior"
    assert compute_seniority(48) == "senior"
    assert compute_seniority(71) == "senior"


def test_staff():
    assert compute_seniority(72) == "staff"
    assert compute_seniority(90) == "staff"
    assert compute_seniority(120) == "staff"
