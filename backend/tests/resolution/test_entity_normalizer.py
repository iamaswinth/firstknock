import pytest
from unittest.mock import AsyncMock, MagicMock

from firstknock.pipeline.resolution.entity_normalizer import (
    _strip_company,
    _strip_institution,
    resolve_company,
    resolve_institution,
)


# ── _strip_company ─────────────────────────────────────────────────────────────

class TestStripCompany:
    def test_strips_pvt_ltd(self):
        assert _strip_company("Cimpress India Pvt. Ltd.") == "Cimpress India"

    def test_strips_llc(self):
        assert _strip_company("Google LLC") == "Google"

    def test_strips_inc(self):
        assert _strip_company("Meta Platforms, Inc.") == "Meta Platforms"

    def test_strips_technologies(self):
        assert _strip_company("Infosys Technologies") == "Infosys"

    def test_strips_tech(self):
        assert _strip_company("Zoho Tech") == "Zoho"

    def test_strips_solutions(self):
        assert _strip_company("TCS Solutions") == "TCS"

    def test_strips_limited(self):
        assert _strip_company("Wipro Limited") == "Wipro"

    def test_strips_private_limited(self):
        assert _strip_company("Freshworks Private Limited") == "Freshworks"

    def test_strips_parenthetical(self):
        assert _strip_company("Amazon (AWS Division)") == "Amazon"

    def test_noop_when_already_clean(self):
        assert _strip_company("Google") == "Google"
        assert _strip_company("AWS") == "AWS"
        assert _strip_company("Stripe") == "Stripe"

    def test_handles_empty(self):
        assert _strip_company("") == ""

    def test_idempotent(self):
        samples = [
            "Google LLC",
            "Cimpress India Pvt. Ltd.",
            "Infosys Technologies",
            "Meta Platforms, Inc.",
            "AWS",
        ]
        for name in samples:
            once = _strip_company(name)
            twice = _strip_company(once)
            assert once == twice, f"Not idempotent: {name!r} → {once!r} → {twice!r}"


# ── _strip_institution ─────────────────────────────────────────────────────────

class TestStripInstitution:
    def test_strips_parenthetical(self):
        assert _strip_institution("IIT Delhi (Computer Science)") == "IIT Delhi"

    def test_noop_abbreviation(self):
        # Abbreviations are handled by alias file or fuzzy pre-check, not by stripping
        assert _strip_institution("MIT") == "MIT"
        assert _strip_institution("IIT Delhi") == "IIT Delhi"

    def test_noop_full_name(self):
        assert _strip_institution("University of Hyderabad") == "University of Hyderabad"


# ── resolve_company (async) ────────────────────────────────────────────────────

class TestResolveCompany:
    @pytest.fixture
    def mock_session_hit(self):
        """Session that returns an existing Company node."""
        record = MagicMock()
        record.__getitem__ = lambda self, key: "Cimpress India"
        result = AsyncMock()
        result.single = AsyncMock(return_value=record)
        session = MagicMock()
        session.run = AsyncMock(return_value=result)
        return session

    @pytest.fixture
    def mock_session_miss(self):
        """Session that returns no existing Company node."""
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session = MagicMock()
        session.run = AsyncMock(return_value=result)
        return session

    @pytest.mark.asyncio
    async def test_uses_existing_node_name_on_hit(self, mock_session_hit):
        # LinkedIn sends "Cimpress India Pvt. Ltd." but graph already has "Cimpress India"
        resolved = await resolve_company(mock_session_hit, "Cimpress India Pvt. Ltd.")
        assert resolved == "Cimpress India"

    @pytest.mark.asyncio
    async def test_returns_stripped_name_on_miss(self, mock_session_miss):
        resolved = await resolve_company(mock_session_miss, "Google LLC")
        assert resolved == "Google"

    @pytest.mark.asyncio
    async def test_alias_fallback_on_miss(self, mock_session_miss, monkeypatch):
        import firstknock.pipeline.resolution.entity_normalizer as mod
        monkeypatch.setattr(mod, "_COMPANY_ALIASES", {"stripe": "Stripe Inc."})
        resolved = await resolve_company(mock_session_miss, "Stripe")
        assert resolved == "Stripe Inc."


# ── resolve_institution (async) ───────────────────────────────────────────────

class TestResolveInstitution:
    @pytest.fixture
    def mock_session_hit(self):
        record = MagicMock()
        record.__getitem__ = lambda self, key: "Indian Institute of Technology Delhi"
        result = AsyncMock()
        result.single = AsyncMock(return_value=record)
        session = MagicMock()
        session.run = AsyncMock(return_value=result)
        return session

    @pytest.fixture
    def mock_session_miss(self):
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session = MagicMock()
        session.run = AsyncMock(return_value=result)
        return session

    @pytest.mark.asyncio
    async def test_uses_existing_node_on_hit(self, mock_session_hit):
        # LinkedIn sends full name; resume wrote abbreviated form first — fuzzy finds it
        resolved = await resolve_institution(mock_session_hit, "IIT Delhi")
        assert resolved == "Indian Institute of Technology Delhi"

    @pytest.mark.asyncio
    async def test_returns_cleaned_name_on_miss(self, mock_session_miss):
        resolved = await resolve_institution(mock_session_miss, "MIT")
        assert resolved == "MIT"

    @pytest.mark.asyncio
    async def test_alias_fallback_on_miss(self, mock_session_miss, monkeypatch):
        import firstknock.pipeline.resolution.entity_normalizer as mod
        monkeypatch.setattr(
            mod, "_INSTITUTION_ALIASES",
            {"iit delhi": "Indian Institute of Technology Delhi"}
        )
        resolved = await resolve_institution(mock_session_miss, "IIT Delhi")
        assert resolved == "Indian Institute of Technology Delhi"
