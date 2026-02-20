# Genesis Profile Engine — 700MB Forensic-Grade Browser Profiles

## Core Module: `genesis_core.py` (1642 lines)

Genesis is the profile forging engine that creates browser profiles indistinguishable from a real person's 6-24 month browsing history. Each profile is ~700MB — matching the size of a genuine Firefox/Chrome profile that has been used daily for months.

---

## Why Profile Aging Matters

Modern antifraud systems (Forter, Sift, Riskified) check:
1. **Cookie age**: Fresh cookies = new device = high risk
2. **Browsing history depth**: Empty history = bot or fresh install
3. **Trust anchor presence**: No Google/Facebook cookies = suspicious
4. **localStorage state**: Empty localStorage = never visited before
5. **IndexedDB entries**: Missing service worker caches = abnormal
6. **Profile directory size**: A 5KB profile vs a 700MB profile is an instant flag

A real person who has used their browser for 6 months will have:
- 3,000-15,000 history entries
- 500-2,000 cookies across hundreds of domains
- Dozens of localStorage entries
- Multiple IndexedDB databases
- Cached images, scripts, stylesheets totaling hundreds of MB

Genesis replicates ALL of this synthetically.

---

## Profile Generation Pipeline

### Step 1: Configuration (`ProfileConfig`)

```python
@dataclass
class ProfileConfig:
    target: TargetPreset          # Amazon, eBay, Steam, etc.
    persona_name: str             # "John Michael Davis"
    persona_email: str            # "jmdavis1987@gmail.com"
    persona_address: Dict         # Full billing address
    age_days: int = 90            # Profile age (30-900 days)
    browser: str = "firefox"      # firefox or chromium
    hardware_profile: str = "us_windows_desktop"
    history_density: float = 1.0  # Multiplier for history entries
```

### Step 2: Browsing History Generation

Genesis generates thousands of browsing entries following **circadian rhythm weighting**:

```python
circadian_weights = [
    0.1, 0.05, 0.02, 0.01, 0.01, 0.02,  # 00:00-05:59 (sleeping)
    0.05, 0.1, 0.15, 0.2, 0.25, 0.3,    # 06:00-11:59 (morning)
    0.35, 0.3, 0.25, 0.3, 0.35, 0.4,    # 12:00-17:59 (afternoon)
    0.5, 0.6, 0.7, 0.65, 0.5, 0.3       # 18:00-23:59 (evening peak)
]
```

This means the profile shows more browsing activity in the evening (when real people browse most) and almost none at 3 AM. Antifraud systems that analyze temporal patterns see a natural human rhythm.

**Domain categories generated:**
- Social media: Google, YouTube, Facebook, Twitter, Reddit, Instagram
- News: CNN, BBC, NYTimes, HackerNews
- Productivity: Gmail, Google Drive, GitHub, StackOverflow
- Shopping: Amazon, eBay (builds trust for e-commerce targets)
- Entertainment: Netflix, Spotify, Twitch

### Step 3: Cookie Synthesis

**Trust anchor cookies** are the most critical. These are cookies from major platforms that prove the browser has been used for real browsing:

| Cookie | Domain | Purpose |
|--------|--------|---------|
| `NID` | google.com | Google tracking cookie (proves Google searches) |
| `SID` / `HSID` | google.com | Google session (proves logged-in Google use) |
| `c_user` | facebook.com | Facebook user cookie |
| `datr` | facebook.com | Facebook device cookie (6-month expiry) |
| `session-id` | amazon.com | Amazon session (critical for Amazon targets) |
| `_ga` / `_gid` | (various) | Google Analytics (present on 80% of websites) |

Each cookie is generated with:
- **Realistic creation date**: Spread across the profile's age range
- **Correct expiry**: Matches the real cookie's max-age
- **Valid format**: Base64, hex, or UUID as appropriate
- **SameSite attributes**: `Lax`, `Strict`, or `None` matching real behavior
- **Secure/HttpOnly flags**: Set correctly per domain

### Step 4: localStorage / sessionStorage

Pre-populated with realistic web app state:
- Google account preferences
- YouTube watch history markers
- Reddit theme preferences
- Shopping cart remnants
- Cookie consent acknowledgments
- Dark mode preferences

### Step 5: Hardware Fingerprint Configuration

Each profile includes a `hardware_config.json` that tells Camoufox what hardware to report:

```json
{
  "cpu_model": "13th Gen Intel(R) Core(TM) i7-13700K",
  "cpu_cores": 16,
  "ram_gb": 32,
  "gpu_vendor": "Intel",
  "gpu_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 730)",
  "screen_resolution": "1920x1080",
  "color_depth": 24,
  "platform": "Win32",
  "oscpu": "Windows NT 10.0; Win64; x64"
}
```

### Step 6: Firefox Profile Assembly (profgen pipeline)

For Firefox profiles, Genesis uses the `profgen` pipeline to create forensic-grade SQLite databases:

- **`places.sqlite`**: Browsing history with `moz_places`, `moz_historyvisits`, `moz_bookmarks` tables
- **`cookies.sqlite`**: Cookie database with correct schema version
- **`webappsstore.sqlite`**: localStorage entries
- **`permissions.sqlite`**: Site permissions (camera, microphone, notifications)
- **`content-prefs.sqlite`**: Per-site zoom levels, font sizes
- **`formhistory.sqlite`**: Form autofill data
- **`containers.json`**: Firefox Multi-Account Containers
- **`user.js`**: Firefox preferences (privacy settings, homepage, etc.)

---

## Archetype-Based Profile Generation

Genesis supports **persona archetypes** that create consistent behavioral patterns:

| Archetype | Age Range | Hardware | Browsing Pattern |
|-----------|-----------|----------|-----------------|
| **Student** | 18-24 | Budget laptop | Reddit, Discord, YouTube, Spotify, textbook sites |
| **Professional** | 28-45 | Business laptop | LinkedIn, Slack, Google Workspace, news sites |
| **Gamer** | 16-30 | Gaming desktop | Steam, Twitch, Discord, Reddit gaming subs |
| **Parent** | 30-50 | Family desktop | Amazon, school sites, recipe sites, Facebook |
| **Elderly** | 55-75 | Basic desktop | Email, news, weather, Facebook, health sites |

Each archetype generates history entries weighted toward their typical browsing patterns, making the profile's behavioral signature consistent with the persona.

---

## How Purchase History Helps Current Purchases

### Module: `purchase_history_engine.py`

This is one of TITAN's most powerful features. It injects **synthetic past purchases** into the profile to establish trust with the target merchant.

**Why it works**: When you make a purchase on Amazon, their antifraud system checks:
1. Is this a new customer? (High risk)
2. Have they bought before? (Lower risk)
3. What's their purchase velocity? (Sudden spike = fraud)
4. Do past purchases match the current one? (Category consistency)

Purchase History Engine creates a realistic purchase timeline:

```
Day -180: Small purchase ($12.99 phone case)
Day -150: Medium purchase ($34.99 book set)
Day -120: Account verification (address update)
Day -90:  Regular purchase ($49.99 headphones)
Day -60:  Subscription start (Prime trial)
Day -30:  Multiple small purchases ($15-40 range)
Day -14:  Cart abandonment (adds items, doesn't buy)
Day -7:   Wishlist activity
Day 0:    TARGET PURCHASE (now looks like a returning customer)
```

The engine generates:
- **Order confirmation emails** in the profile's email client
- **Shipping notification cookies** from carrier sites
- **Review activity** (browsing product reviews)
- **Cart history** in localStorage
- **Payment method familiarity** (saved card indicators)

This transforms a "first-time buyer" (high risk, ~40% decline rate) into a "returning customer" (low risk, ~5% decline rate).

---

## Profile Realism Scoring

### Module: `profile_realism_engine.py`

Before deployment, each profile is scored on multiple dimensions:

| Dimension | Weight | What It Checks |
|-----------|--------|---------------|
| History depth | 20% | Enough entries for claimed age |
| Cookie diversity | 15% | Cookies from multiple domain categories |
| Temporal consistency | 20% | Circadian rhythm, no impossible timestamps |
| Trust anchors | 15% | Google, Facebook, Amazon cookies present |
| Hardware consistency | 10% | GPU matches CPU generation |
| Geo consistency | 10% | Timezone, locale, language all match |
| Size realism | 10% | Profile size matches claimed age |

A score below 70% triggers a warning; below 50% the profile is rejected and regenerated.
