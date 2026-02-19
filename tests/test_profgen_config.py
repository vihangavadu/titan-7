"""
Tests for profgen/config.py - Profile configuration and shared constants.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ensure profgen is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "profgen"))

from config import (
    PROFILE_UUID, PERSONA_NAME, PERSONA_EMAIL, PERSONA_PHONE,
    BILLING, CARD_LAST4, AGE_DAYS, STORAGE_MB, NOW, CREATED,
    CANVAS_SEED, AUDIO_SEED, WEBGL_SEED,
    TRUST_DOMAINS, COMMERCE_DOMAINS, ALL_DOMAINS,
    TRANSITION_LINK, TRANSITION_TYPED, TRANSITION_BOOKMARK,
    SUBPAGES, PHASES,
    circ_hour, rand_subpage, rand_visit_type, spread_time,
    pareto_visits, title_for, stripe_mid,
)


class TestConfigConstants:
    """Test static configuration values."""

    def test_profile_uuid_is_hex(self):
        """PROFILE_UUID is a 32-char hex string."""
        assert len(PROFILE_UUID) == 32
        int(PROFILE_UUID, 16)  # Should not raise

    def test_persona_fields(self):
        """Persona identity fields are populated."""
        assert len(PERSONA_NAME) > 0
        assert "@" in PERSONA_EMAIL
        assert PERSONA_PHONE.startswith("+")

    def test_billing_has_required_keys(self):
        """Billing address has all required keys."""
        for key in ["street", "city", "state", "zip", "country"]:
            assert key in BILLING

    def test_age_days_positive(self):
        """AGE_DAYS is a positive integer."""
        assert AGE_DAYS > 0

    def test_created_is_in_past(self):
        """CREATED timestamp is AGE_DAYS before NOW."""
        diff = (NOW - CREATED).days
        assert diff == AGE_DAYS

    def test_fingerprint_seeds_are_integers(self):
        """Canvas, audio, webgl seeds are integers derived from UUID hash."""
        assert isinstance(CANVAS_SEED, int)
        assert isinstance(AUDIO_SEED, int)
        assert isinstance(WEBGL_SEED, int)
        assert CANVAS_SEED > 0
        assert AUDIO_SEED > 0
        assert WEBGL_SEED > 0

    def test_seeds_are_different(self):
        """Each fingerprint seed is unique."""
        assert CANVAS_SEED != AUDIO_SEED
        assert CANVAS_SEED != WEBGL_SEED
        assert AUDIO_SEED != WEBGL_SEED


class TestDomainLists:
    """Test domain configuration."""

    def test_trust_domains_not_empty(self):
        """TRUST_DOMAINS has entries."""
        assert len(TRUST_DOMAINS) > 0

    def test_commerce_domains_not_empty(self):
        """COMMERCE_DOMAINS has entries."""
        assert len(COMMERCE_DOMAINS) > 0

    def test_all_domains_is_union(self):
        """ALL_DOMAINS = TRUST_DOMAINS + COMMERCE_DOMAINS."""
        assert ALL_DOMAINS == TRUST_DOMAINS + COMMERCE_DOMAINS

    def test_google_in_trust(self):
        """google.com is a trust domain."""
        assert "google.com" in TRUST_DOMAINS

    def test_amazon_in_commerce(self):
        """amazon.com is a commerce domain."""
        assert "amazon.com" in COMMERCE_DOMAINS

    def test_no_duplicates_in_all(self):
        """No duplicate domains in ALL_DOMAINS."""
        assert len(ALL_DOMAINS) == len(set(ALL_DOMAINS))


class TestTransitionConstants:
    """Test Firefox visit type constants."""

    def test_transition_values(self):
        """Transition constants have correct Firefox values."""
        assert TRANSITION_LINK == 1
        assert TRANSITION_TYPED == 2
        assert TRANSITION_BOOKMARK == 3


class TestSubpages:
    """Test SUBPAGES configuration."""

    def test_subpages_for_trust_domains(self):
        """Each trust domain has subpages defined."""
        for domain in TRUST_DOMAINS:
            assert domain in SUBPAGES, f"Missing subpages for {domain}"
            assert len(SUBPAGES[domain]) > 0

    def test_subpages_for_commerce_domains(self):
        """Each commerce domain has subpages defined."""
        for domain in COMMERCE_DOMAINS:
            assert domain in SUBPAGES, f"Missing subpages for {domain}"
            assert len(SUBPAGES[domain]) > 0

    def test_subpages_are_paths(self):
        """Subpage entries start with /."""
        for domain, pages in SUBPAGES.items():
            for page in pages:
                assert page.startswith("/"), f"Bad subpage for {domain}: {page}"


class TestPhases:
    """Test narrative phase configuration."""

    def test_phases_defined(self):
        """PHASES dict has expected phase names."""
        assert "discovery" in PHASES
        assert "development" in PHASES
        assert "seasoned" in PHASES

    def test_phase_entries_are_tuples(self):
        """Each phase entry is a (domain, path, days_ago, visit_count) tuple."""
        for phase_name, entries in PHASES.items():
            for entry in entries:
                assert len(entry) == 4, f"Bad entry in {phase_name}: {entry}"
                domain, path, days_ago, count = entry
                assert isinstance(domain, str)
                assert isinstance(path, str)
                assert isinstance(days_ago, int)
                assert isinstance(count, int)
                assert days_ago >= 0
                assert count > 0


class TestCircHour:
    """Test circadian-weighted hour generation."""

    def test_returns_valid_hour(self):
        """circ_hour() returns 0-23."""
        for _ in range(100):
            h = circ_hour()
            assert 0 <= h <= 23

    def test_distribution_favors_daytime(self):
        """Daytime hours (8-22) are more common than nighttime."""
        hours = [circ_hour() for _ in range(10000)]
        daytime = sum(1 for h in hours if 8 <= h <= 22)
        nighttime = sum(1 for h in hours if h < 5 or h > 22)
        assert daytime > nighttime


class TestRandSubpage:
    """Test random subpage selection."""

    def test_known_domain(self):
        """Returns a subpage from SUBPAGES for known domains."""
        page = rand_subpage("google.com")
        assert page in SUBPAGES["google.com"]

    def test_unknown_domain_returns_generic(self):
        """Returns a generic subpage for unknown domains."""
        page = rand_subpage("unknown-domain.xyz")
        assert page.startswith("/")

    def test_returns_string(self):
        """Always returns a string."""
        for domain in ALL_DOMAINS:
            page = rand_subpage(domain)
            assert isinstance(page, str)


class TestRandVisitType:
    """Test weighted random visit type."""

    def test_returns_valid_type(self):
        """Returns a valid Firefox transition type."""
        valid_types = {1, 2, 3, 5, 6, 8}  # LINK, TYPED, BOOKMARK, REDIRECT_PERM, REDIRECT_TEMP, FRAMED_LINK
        for _ in range(100):
            vt = rand_visit_type()
            assert vt in valid_types

    def test_link_is_most_common(self):
        """TRANSITION_LINK (1) is the most common type."""
        types = [rand_visit_type() for _ in range(10000)]
        link_count = types.count(TRANSITION_LINK)
        assert link_count > len(types) * 0.5  # Should be >50%


class TestSpreadTime:
    """Test time spreading with organic jitter."""

    def test_returns_datetime(self):
        """spread_time() returns a datetime."""
        result = spread_time(30)
        assert isinstance(result, datetime)

    def test_roughly_correct_days_ago(self):
        """Result is approximately days_ago in the past."""
        result = spread_time(60)
        diff = (NOW - result).days
        assert 55 <= diff <= 65  # Allow jitter

    def test_avoids_deep_night(self):
        """Results should rarely be in 0-4am range."""
        results = [spread_time(30) for _ in range(200)]
        deep_night = sum(1 for r in results if r.hour < 5)
        # Should be very rare
        assert deep_night < len(results) * 0.1


class TestParetoVisits:
    """Test Pareto-distributed visit generation."""

    def test_returns_list(self):
        """pareto_visits() returns a list."""
        result = pareto_visits(ALL_DOMAINS, AGE_DAYS)
        assert isinstance(result, list)

    def test_default_count(self):
        """Default generates ~2000 visits."""
        result = pareto_visits(ALL_DOMAINS, AGE_DAYS)
        assert len(result) == 2000

    def test_custom_count(self):
        """Custom n parameter works."""
        result = pareto_visits(ALL_DOMAINS, AGE_DAYS, n=500)
        assert len(result) == 500

    def test_entry_format(self):
        """Each entry is (domain, day_offset, visit_count)."""
        result = pareto_visits(ALL_DOMAINS, AGE_DAYS, n=100)
        for domain, day, count in result:
            assert isinstance(domain, str)
            assert isinstance(day, int)
            assert day >= 0
            assert isinstance(count, int)
            assert count >= 1


class TestTitleFor:
    """Test page title generation."""

    def test_known_domain(self):
        """Known domains return their proper title."""
        assert title_for("google.com") == "Google"
        assert "YouTube" in title_for("youtube.com")
        assert "GitHub" in title_for("github.com")

    def test_with_path(self):
        """Path is appended to title."""
        title = title_for("google.com", "/search")
        assert "Google" in title
        assert "Search" in title

    def test_unknown_domain(self):
        """Unknown domain uses capitalized domain name."""
        title = title_for("mysite.com")
        assert "Mysite" in title

    def test_root_path(self):
        """Root path doesn't append extra text."""
        title = title_for("google.com", "/")
        assert title == "Google"


class TestStripeMid:
    """Test Stripe machine ID generation."""

    def test_returns_string(self):
        """stripe_mid() returns a string."""
        mid = stripe_mid()
        assert isinstance(mid, str)

    def test_has_dot_separators(self):
        """Stripe MID has dot-separated parts."""
        mid = stripe_mid()
        parts = mid.split(".")
        assert len(parts) == 3

    def test_contains_timestamp(self):
        """Middle part is a Unix timestamp."""
        mid = stripe_mid()
        parts = mid.split(".")
        ts = int(parts[1])
        # Should be a reasonable timestamp (after 2020)
        assert ts > 1577836800
