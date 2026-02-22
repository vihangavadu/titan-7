# MODULE 1: GENESIS ENGINE — Complete Technical Reference

## Profile Forge: Detection-Aware Identity Synthesis

**Module:** `genesis_core.py` | **Lines:** 1462 | **Path:** `/opt/titan/core/genesis_core.py`  
**Version:** 7.0.2 | **Authority:** Dva.12

---

## Table of Contents

1. [Purpose & Philosophy](#1-purpose--philosophy)
2. [Classes & Data Structures](#2-classes--data-structures)
3. [Profile Archetypes](#3-profile-archetypes)
4. [Target Presets](#4-target-presets)
5. [Profile Generation Pipeline](#5-profile-generation-pipeline)
6. [Hardware Fingerprint Database](#6-hardware-fingerprint-database)
7. [Cookie & History Engineering](#7-cookie--history-engineering)
8. [Trust Anchor System](#8-trust-anchor-system)
9. [Integration Points](#9-integration-points)
10. [API Reference](#10-api-reference)

---

## 1. Purpose & Philosophy

Genesis Engine is the **Profile Forge** — it creates aged browser profiles that appear to belong to a real person who has been browsing the internet for weeks or months. These profiles are then loaded into the hardened Camoufox browser for manual operation.

**Key Principle:** Genesis does NOT automate browsing. It generates the **artifacts** of browsing (cookies, history, localStorage, hardware fingerprints) so that when the human operator opens the browser, the target site sees a returning customer with established trust signals.

**Why This Works:**
- Fraud engines score "new device" profiles at 60-80 risk (out of 100)
- A profile with 90+ days of browsing history, aged cookies, and trust anchors scores 15-25
- The difference between a fresh profile and an aged one is often the difference between instant decline and approval

---

## 2. Classes & Data Structures

### 2.1 Enums

#### `TargetCategory`
```python
class TargetCategory(Enum):
    ECOMMERCE = "ecommerce"
    GAMING = "gaming"
    CRYPTO = "crypto"
    BANKING = "banking"
    GIFT_CARDS = "gift_cards"
    STREAMING = "streaming"
```
Used to categorize targets for profile optimization. Each category has different trust requirements and profile aging needs.

#### `ProfileArchetype`
```python
class ProfileArchetype(Enum):
    STUDENT_DEVELOPER = "student_developer"
    PROFESSIONAL = "professional"
    RETIREE = "retiree"
    GAMER = "gamer"
    CASUAL_SHOPPER = "casual_shopper"
```
Defines the "persona narrative" — the browsing history, commerce patterns, and trust tokens are generated to match a believable human archetype.

### 2.2 Dataclasses

#### `TargetPreset`
```python
@dataclass
class TargetPreset:
    name: str                      # Internal ID (e.g., "amazon_us")
    category: TargetCategory       # Platform category
    domain: str                    # Primary domain (e.g., "amazon.com")
    display_name: str              # GUI display name
    recommended_age_days: int      # Minimum profile age for success
    trust_anchors: List[str]       # Domains that build trust (Google, Facebook)
    required_cookies: List[str]    # Cookies the target expects to see
    browser_preference: str        # "firefox" or "chromium"
    notes: str = ""                # Operator notes
```

#### `ProfileConfig`
```python
@dataclass
class ProfileConfig:
    target: TargetPreset           # Which target this profile is for
    persona_name: str              # Fake identity name
    persona_email: str             # Fake identity email
    persona_address: Dict[str, str]  # Fake identity address
    age_days: int = 90             # How old the profile should appear
    browser: str = "firefox"       # Browser type
    include_social_history: bool = True   # Include social media in history
    include_shopping_history: bool = True # Include shopping in history
    hardware_profile: str = "us_windows_desktop"  # Hardware fingerprint ID
```

#### `GeneratedProfile`
```python
@dataclass
class GeneratedProfile:
    profile_id: str                # Unique hash-based ID (titan_<12hex>)
    profile_path: Path             # Filesystem path to profile directory
    browser_type: str              # "firefox" or "chromium"
    age_days: int                  # Profile age in days
    target_domain: str             # Target domain
    cookies_count: int             # Number of generated cookies
    history_count: int             # Number of history entries
    created_at: datetime           # Generation timestamp
    hardware_fingerprint: Dict     # Hardware fingerprint data
```

---

## 3. Profile Archetypes

Each archetype defines a complete persona narrative with specific browsing patterns, commerce history, and trust tokens.

### 3.1 STUDENT_DEVELOPER

| Property | Value |
|----------|-------|
| **Age Range** | 20-28 |
| **Hardware** | `us_macbook_pro` (Apple M3 Pro) |
| **Timezone** | America/Los_Angeles |
| **Trust Tokens** | spotify_student, github_pro, aws_free_tier |

**History Domains:** overleaf.com, arxiv.org, chegg.com, spotify.com, github.com, stackoverflow.com, aws.amazon.com, digitalocean.com, leetcode.com, hackerrank.com, coursera.org, udemy.com, reddit.com, discord.com, twitch.tv

**Commerce History:** newegg.com (30%), amazon.com (50%), ubereats.com (40%), doordash.com (30%), bestbuy.com (20%)

### 3.2 PROFESSIONAL

| Property | Value |
|----------|-------|
| **Age Range** | 28-50 |
| **Hardware** | `us_windows_desktop` (Intel i7 + RTX 4070) |
| **Timezone** | America/New_York |
| **Trust Tokens** | linkedin_premium, office365 |

**History Domains:** linkedin.com, levels.fyi, glassdoor.com, slack.com, zoom.us, notion.so, figma.com, jira.atlassian.com, gmail.com, outlook.com, salesforce.com, hubspot.com, wsj.com, bloomberg.com, cnbc.com

**Commerce History:** amazon.com (60%), bestbuy.com (40%), costco.com (30%), homedepot.com (20%), target.com (30%)

### 3.3 RETIREE

| Property | Value |
|----------|-------|
| **Age Range** | 55-75 |
| **Hardware** | `us_windows_desktop` |
| **Timezone** | America/Phoenix |
| **Trust Tokens** | aarp_member |

**History Domains:** weather.com, cnn.com, foxnews.com, webmd.com, aarp.org, facebook.com, youtube.com, pinterest.com, mayoclinic.org, nih.gov, medicare.gov

**Commerce History:** amazon.com (70%), walmart.com (50%), cvs.com (40%), walgreens.com (30%), costco.com (30%)

### 3.4 GAMER

| Property | Value |
|----------|-------|
| **Age Range** | 18-35 |
| **Hardware** | `us_windows_desktop` |
| **Timezone** | America/Los_Angeles |
| **Trust Tokens** | steam_account, discord_nitro, twitch_prime |

**History Domains:** steampowered.com, twitch.tv, discord.com, reddit.com, ign.com, kotaku.com, nvidia.com, amd.com, epicgames.com, gog.com, humble.com, g2a.com

**Commerce History:** steampowered.com (80%), newegg.com (50%), amazon.com (40%), bestbuy.com (30%), gamestop.com (20%)

### 3.5 CASUAL_SHOPPER

| Property | Value |
|----------|-------|
| **Age Range** | 25-55 |
| **Hardware** | `us_windows_desktop` |
| **Timezone** | America/Chicago |
| **Trust Tokens** | amazon_prime |

**History Domains:** google.com, facebook.com, instagram.com, pinterest.com, youtube.com, tiktok.com, twitter.com, reddit.com

**Commerce History:** amazon.com (80%), target.com (50%), walmart.com (50%), etsy.com (30%), ebay.com (30%), wayfair.com (20%)

---

## 4. Target Presets

Genesis includes 15+ pre-configured target presets. Each preset defines the optimal profile configuration for a specific target.

| Preset ID | Domain | Category | Age (days) | Browser | Trust Anchors | Notes |
|-----------|--------|----------|------------|---------|---------------|-------|
| `amazon_us` | amazon.com | ECOMMERCE | 90 | firefox | google, facebook | High-value electronics need 90+ days |
| `amazon_uk` | amazon.co.uk | ECOMMERCE | 90 | firefox | google.co.uk, facebook | — |
| `eneba_gift` | eneba.com | GIFT_CARDS | 60 | chromium | google, steam | Lower friction than physical goods |
| `g2a_gift` | g2a.com | GIFT_CARDS | 45 | chromium | google, steam | — |
| `steam_wallet` | store.steampowered.com | GAMING | 120 | firefox | google | Aggressive device fingerprinting |
| `coinbase_buy` | coinbase.com | CRYPTO | 180 | chromium | google, gmail | Requires KYC module first |
| `bestbuy_us` | bestbuy.com | ECOMMERCE | 60 | chromium | google | — |
| `newegg_us` | newegg.com | ECOMMERCE | 45 | firefox | google | — |
| `stockx_us` | stockx.com | ECOMMERCE | 90 | chromium | google, instagram | High resale value — strict verification |
| `netflix_sub` | netflix.com | STREAMING | 30 | firefox | google | — |
| `mygiftcardsupply` | mygiftcardsupply.com | GIFT_CARDS | 60 | firefox | google | Stripe PSP — good for Amazon/Google Play |
| `dundle` | dundle.com | GIFT_CARDS | 60 | firefox | google, steam | Adyen PSP with Forter — requires aged profile |
| `shopapp` | shop.app | ECOMMERCE | 45 | chromium | google, shopify | Shopify Payments — varies by merchant |
| `eneba_keys` | eneba.com | GAMING | 60 | firefox | google, steam, twitch | Adyen PSP — 3DS common on EU cards |

---

## 5. Profile Generation Pipeline

### 5.1 Entry Point: `forge_profile(config)`

```
ProfileConfig ──► Generate Profile ID (SHA-256 hash)
                      │
                      ▼
              Create Profile Directory
                      │
          ┌───────────┼───────────┬──────────────┐
          ▼           ▼           ▼              ▼
     History     Cookies    LocalStorage    Hardware FP
     Generator   Generator  Generator       Generator
          │           │           │              │
          ▼           ▼           ▼              ▼
     Write Firefox/Chromium Profile to Disk
                      │
                      ▼
              Write Metadata JSON
                      │
                      ▼
              Return GeneratedProfile
```

### 5.2 Profile ID Generation

```python
seed = f"{persona_name}:{target_domain}:{datetime.now().isoformat()}"
profile_id = f"titan_{sha256(seed)[:12]}"
```

Each profile gets a unique, deterministic-ish ID based on the persona and target.

### 5.3 History Generation Algorithm

The history generator uses **Pareto distribution** to create realistic browsing patterns:

1. **Day Weight:** `1.0 / (1 + day * 0.1)` — Recent days have more entries
2. **Entry Count:** `max(1, int(paretovariate(1.5) * 3 * day_weight))` — Heavy-tailed distribution
3. **Hour Selection:** Weighted by **circadian rhythm** array (24 weights, peak at 18:00-21:00)
4. **Domain Mix:**
   - 30% chance: Target domain (if shopping history enabled)
   - 20% chance: Trust anchor domain
   - 50% chance: Common browsing domain (Google, YouTube, Reddit, etc.)

**Circadian Weights (hourly):**
```
00-05: [0.10, 0.05, 0.02, 0.01, 0.01, 0.02]  ← Sleeping
06-11: [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]  ← Morning ramp
12-17: [0.35, 0.30, 0.25, 0.30, 0.35, 0.40]  ← Afternoon
18-23: [0.50, 0.60, 0.70, 0.65, 0.50, 0.30]  ← Evening peak
```

### 5.4 Cookie Generation

Cookies are generated in three categories:

1. **Trust Anchor Cookies** — Google (SID, HSID, SSID, NID), Facebook (c_user, xs, fr)
2. **Target-Specific Cookies** — From `required_cookies` list in target preset
3. **Stripe Device Fingerprint** — Pre-aged `__stripe_mid` cookie (30 days older than profile)

All cookies have:
- `creation_time` set to `now - age_days` (microsecond precision)
- `expiry` set to `now + 365 days`
- `secure: true`, `http_only: true`

### 5.5 Stripe MID Generation

```python
device_hash = sha256(f"{persona_name}:{hardware_profile}")[:16]
timestamp = int(creation_time.timestamp())
random_part = token_hex(8)
stripe_mid = f"{device_hash}.{timestamp}.{random_part}"
```

This pre-ages the Stripe device fingerprint by 30 days beyond the profile age, making it appear the user has been a Stripe customer for a long time.

### 5.6 LocalStorage Generation

- **Google Analytics:** `_ga` with aged timestamp, `_gid` with current timestamp
- **Facebook Pixel:** `_fbp` with aged timestamp

---

## 6. Hardware Fingerprint Database

Genesis includes 10 hardware profiles, each a complete device identity:

| Profile ID | CPU | GPU | Screen | Platform |
|-----------|-----|-----|--------|----------|
| `us_windows_desktop` | Intel i7-13700K | RTX 4070 | 2560x1440 | Win32 (Dell XPS 8960) |
| `us_windows_desktop_amd` | Ryzen 9 7950X | RX 7900 XTX | 3440x1440 | Win32 (ASUS ROG) |
| `us_windows_desktop_intel` | Intel i5-13600K | UHD 770 | 1920x1080 | Win32 (HP Pavilion) |
| `us_macbook_pro` | Apple M3 Pro | M3 Pro GPU | 3024x1964 | MacIntel |
| `us_macbook_air_m2` | Apple M2 | M2 GPU | 2560x1664 | MacIntel |
| `us_windows_laptop` | Intel i7-1365U | Iris Xe | 1920x1200 | Win32 (Lenovo ThinkPad) |
| `us_windows_laptop_hp` | Intel i5-1335U | Iris Xe | 1920x1080 | Win32 (HP EliteBook) |
| `uk_windows_desktop` | Intel i7-13700K | RTX 4070 | 2560x1440 | Win32 (Dell XPS) |
| `ca_windows_desktop` | Ryzen 7 7800X3D | RTX 4060 Ti | 2560x1440 | Win32 (ASUS TUF) |
| `au_macbook_pro` | Apple M3 Pro | M3 Pro GPU | 3024x1964 | MacIntel |

Each profile includes: `cpu`, `cores`, `memory`, `gpu`, `gpu_vendor`, `gpu_renderer` (ANGLE string), `screen`, `platform`, `vendor`, `product`, `user_agent`.

---

## 7. Cookie & History Engineering

### 7.1 Why Aged Cookies Matter

Fraud engines check cookie age as a trust signal:
- `__stripe_mid` age > 30 days = trusted device
- Google `SID` cookie present = logged-in Google user
- Facebook `c_user` cookie present = real Facebook account
- Target domain cookies present = returning customer

### 7.2 Cookie Timestamp Precision

All timestamps use **microsecond precision** (`timestamp * 1000000`) to match Firefox's internal cookie storage format. Chromium uses a different epoch (Windows FILETIME), and the engine adjusts accordingly.

### 7.3 History Entry Structure

```json
{
    "url": "https://www.amazon.com/dp/B0CKJNZ3P2",
    "title": "Amazon.com: Electronics - Wireless Headphones",
    "visit_time": 1707321600000000,
    "visit_count": 3,
    "typed_count": 1
}
```

- `visit_time`: Microseconds since Unix epoch
- `visit_count`: How many times this URL was visited (1-10, random)
- `typed_count`: How many times the URL was typed in address bar (0-2)

---

## 8. Trust Anchor System

Trust anchors are domains that, when present in cookies/history, signal to fraud engines that this is a real user with an established web presence.

### 8.1 Google Trust Anchors

Generated cookies: `SID` (64 hex), `HSID` (32 hex), `SSID` (32 hex), `NID` (128 hex)

These simulate a user who is logged into Google, which is one of the strongest trust signals available.

### 8.2 Facebook Trust Anchors

Generated cookies: `c_user` (9-digit numeric), `xs` (64 hex), `fr` (48 hex)

Simulates a Facebook-logged-in user. Many fraud engines cross-reference Facebook login status.

### 8.3 Stripe Trust Anchors

Generated cookie: `__stripe_mid` (pre-aged by 30 extra days)

This is the Stripe merchant device ID. A pre-aged Stripe MID tells Stripe Radar that this device has been seen before, dramatically reducing risk score.

---

## 9. Integration Points

### 9.1 With Target Intelligence

Genesis uses `target_intelligence.py` to:
- Look up antifraud system for the target
- Adjust profile parameters based on fraud engine requirements
- Generate operator playbook for the handover

### 9.2 With Pre-Flight Validator

After profile generation, `preflight_validator.py` checks:
- Profile directory exists and is complete
- Cookie count meets minimum threshold
- History age matches configuration
- Hardware fingerprint is consistent

### 9.3 With Handover Protocol

`handover_protocol.py` receives the `GeneratedProfile` and:
- Freezes the profile (read-only)
- Generates handover document with operator instructions
- Includes target-specific playbook and post-checkout guide

### 9.4 With Browser

The generated profile directory is loaded by `titan-browser`:
```bash
titan-browser --profile /opt/titan/profiles/titan_a1b2c3d4e5f6 --target amazon.com
```

---

## 10. API Reference

### GenesisEngine

```python
engine = GenesisEngine(output_dir="/opt/titan/profiles")
```

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `forge_profile(config)` | `ProfileConfig` | `GeneratedProfile` | Main entry — creates complete aged profile |
| `forge_for_target(target_id, persona)` | `str, dict` | `GeneratedProfile` | Convenience — uses target preset |
| `forge_archetype_profile(archetype, target_id)` | `ProfileArchetype, str` | `GeneratedProfile` | Archetype-based generation |
| `get_available_archetypes()` | — | `List[ProfileArchetype]` | List all archetypes |

### Internal Methods

| Method | Purpose |
|--------|---------|
| `_generate_profile_id(config)` | SHA-256 based unique ID |
| `_generate_history(config)` | Pareto-distributed browsing history |
| `_generate_cookies(config)` | Trust anchor + target cookies |
| `_generate_local_storage(config)` | GA + FB pixel localStorage |
| `_generate_hardware_fingerprint(config)` | Hardware identity from database |
| `_generate_anchor_cookies(domain, time)` | Google/Facebook cookie sets |
| `_generate_stripe_mid(config, time)` | Pre-aged Stripe device ID |
| `_write_firefox_profile(path, ...)` | Write Firefox profile format |
| `_write_chromium_profile(path, ...)` | Write Chromium profile format |
| `_write_hardware_profile(path, fp)` | Write hardware fingerprint JSON |
| `_random_path()` | Random URL path segment |
| `_generate_title(domain)` | Realistic page title for domain |

---

**End of Genesis Engine Deep Dive** | **TITAN V7.0 SINGULARITY**

