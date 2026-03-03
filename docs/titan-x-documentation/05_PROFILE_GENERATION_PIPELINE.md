# 05 — Profile Generation Pipeline

**9-Stage Forge Pipeline — 400-700MB Forensic-Grade Profiles — Circadian-Weighted History**

The Genesis Profile Engine creates browser profiles indistinguishable from a real person's 6-24 month browsing history. Each profile is 400-700MB — matching the size of a genuine Firefox/Chrome profile that has been used daily for months. This document covers the complete pipeline from persona creation to quality scoring.

---

## Why Profile Depth Matters

Modern antifraud systems (Forter, Sift, Riskified) check:

| Signal | Empty Browser | Real 6-Month Browser | Genesis Profile |
|--------|--------------|---------------------|-----------------|
| Cookie count | 0 | 500-2,000 | 500-2,000 |
| History entries | 0 | 3,000-15,000 | 5,000-15,000 |
| localStorage entries | 0 | Dozens per major site | Dozens per major site |
| IndexedDB databases | 0 | Multiple | 14 web app schemas |
| Profile directory size | ~5KB | 300-700MB | 400-700MB |
| Trust anchor cookies | None | Google, Facebook, Amazon | All present |
| Purchase history | None | Months of orders | 6+ months synthetic |
| Autofill data | Empty | Names, addresses, cards | Fully populated |

A thin profile is the **#1 detection indicator**. It signals either a fresh device (high risk), a privacy-focused user (suspicious), or a bot. Genesis eliminates this entirely.

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    9-STAGE FORGE PIPELINE                        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 1.IDENTITY│→│ 2.PERSONA │→│ 3.HISTORY │→│ 4.CACHE  │       │
│  │  Generate │  │  Enrich   │  │ 1500+ URL│  │ 350-500MB│       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│        ↓              ↓              ↓              ↓           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 5.COOKIES│→│ 6.STORAGE │→│ 7.AUTOFILL│→│8.PURCHASE│       │
│  │ AES-256  │  │ IDB+LS+LDB│ │ Form data │  │ Commerce │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                    ↓            │
│                                             ┌──────────┐        │
│                                             │ 9.SCORE  │        │
│                                             │ Quality  │        │
│                                             └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

**Total pipeline time**: ~90-180 seconds depending on profile age and density settings.

---

## Stage 1: Identity Generation

**Module**: `advanced_profile_generator.py`

Creates a demographically consistent identity package.

### Input Configuration

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

### Generated Identity Fields

| Field | Generation Method | Consistency Check |
|-------|-------------------|-------------------|
| Full name | Demographic-weighted name database | Gender-consistent, ethnicity-consistent |
| Date of birth | Age range matches persona archetype | Credit history age matches |
| Street address | Real US addresses with valid ZIP | ZIP matches city/state, area code matches |
| Email | Name-based + year + common provider | Domain age > profile age |
| Phone | Area code matches billing state | Carrier matches region |
| SSN (last 4) | Random valid digits | — |
| Employment | Matches age/education level | Salary matches card spending pattern |
| Education | Matches age range | Graduation year consistent |

### Persona Archetypes

| Archetype | Age Range | Hardware | Income Level | Browsing Pattern |
|-----------|-----------|----------|-------------|-----------------|
| Student | 18-24 | Budget laptop | $15K-30K | Reddit, Discord, YouTube, Spotify |
| Professional | 28-45 | Business laptop | $60K-120K | LinkedIn, Slack, Google Workspace |
| Gamer | 16-30 | Gaming desktop | $30K-60K | Steam, Twitch, Discord, Reddit |
| Parent | 30-50 | Family desktop | $50K-90K | Amazon, school sites, recipes, Facebook |
| Elderly | 55-75 | Basic desktop | $30K-50K | Email, news, weather, Facebook |

---

## Stage 2: Persona Enrichment

**Module**: `persona_enrichment_engine.py`

AI-powered enrichment transforms skeletal identity data into a believable persona narrative.

### Enrichment Layers

| Layer | What's Generated | Used By |
|-------|-----------------|---------|
| Social presence | Facebook profile age, Instagram activity level | Trust anchor cookies |
| Employment history | Company, role, tenure | LinkedIn cookies/localStorage |
| Education background | University, degree, graduation year | Persona consistency |
| Interests | 5-10 hobby/interest categories | History URL weighting |
| Behavioral traits | Typing speed range, mouse precision, scroll style | Ghost Motor persona |
| Shopping preferences | Preferred categories, price range, brands | Purchase history generation |
| Device usage | Hours per day, peak usage time, session length | Circadian weighting |

### AI Generation

The `PersonaEnrichmentEngine` uses Ollama (titan-analyst model) to generate internally consistent persona details. Each detail must be consistent with all others:

```
Age 34 + Professional archetype →
  Education: Bachelor's degree, graduated 2014 →
  Employment: 10 years experience, mid-senior role →
  Income: $85K (matches card spending) →
  Interests: Tech news, fitness, travel →
  Browsing: LinkedIn daily, HackerNews, running forums →
  Shopping: Amazon Prime member, prefers electronics + outdoor gear
```

---

## Stage 3: Browsing History Generation

**Module**: `genesis_core.py`

Generates 5,000-15,000 browsing history entries with circadian rhythm weighting.

### Circadian Rhythm Weights

```
Hour  | Weight | Activity Level
──────┼────────┼──────────────────
00:00 | 0.10   | Late night — minimal
01:00 | 0.05   | Sleeping
02:00 | 0.02   | Deep sleep
03:00 | 0.01   | Deep sleep
04:00 | 0.01   | Deep sleep
05:00 | 0.02   | Early morning
06:00 | 0.05   | Waking up
07:00 | 0.10   | Morning routine
08:00 | 0.15   | Work starts
09:00 | 0.20   | Morning work
10:00 | 0.25   | Mid-morning
11:00 | 0.30   | Pre-lunch
12:00 | 0.35   | Lunch break browsing
13:00 | 0.30   | Post-lunch
14:00 | 0.25   | Afternoon
15:00 | 0.30   | Mid-afternoon
16:00 | 0.35   | Late afternoon
17:00 | 0.40   | End of work
18:00 | 0.50   | Evening begins
19:00 | 0.60   | Dinner time browsing
20:00 | 0.70   | Peak evening (highest)
21:00 | 0.65   | Evening
22:00 | 0.50   | Winding down
23:00 | 0.30   | Late evening
```

### Domain Categories

| Category | Example Domains | Weight (Professional) | Weight (Student) |
|----------|----------------|----------------------|-----------------|
| Search | google.com, bing.com | 25% | 20% |
| Social | facebook.com, twitter.com, reddit.com, instagram.com | 15% | 30% |
| News | cnn.com, bbc.com, nytimes.com, hackernews | 10% | 5% |
| Productivity | gmail.com, drive.google.com, github.com | 20% | 15% |
| Shopping | amazon.com, ebay.com (builds trust for targets) | 10% | 5% |
| Entertainment | youtube.com, netflix.com, spotify.com, twitch.tv | 10% | 20% |
| Reference | wikipedia.org, stackoverflow.com | 5% | 10% |
| Misc | weather.com, maps.google.com | 5% | 5% |

### History Entry Structure

Each entry includes:
- **URL**: Full URL with realistic paths and parameters
- **Title**: Matching page title
- **Visit time**: Timestamp following circadian distribution
- **Visit type**: typed, link, bookmark, redirect (weighted probabilities)
- **Visit duration**: Time spent on page (5s-300s based on content type)
- **Referrer**: Previous URL (creates natural navigation chains)
- **Transition type**: How the user arrived (search, link click, direct, bookmark)

### Firefox Profile Assembly

For Firefox profiles, Genesis creates forensic-grade SQLite databases:

| Database | Tables | Content |
|----------|--------|---------|
| `places.sqlite` | `moz_places`, `moz_historyvisits`, `moz_bookmarks` | Full browsing history |
| `cookies.sqlite` | `moz_cookies` | All cookies with correct schema |
| `webappsstore.sqlite` | `webappsstore2` | localStorage entries |
| `permissions.sqlite` | `moz_perms` | Site permissions (camera, notifications) |
| `content-prefs.sqlite` | `prefs` | Per-site zoom, font sizes |
| `formhistory.sqlite` | `moz_formhistory` | Form autofill data |
| `containers.json` | — | Firefox Multi-Account Containers |
| `user.js` | — | Firefox preferences |

### Chromium Profile Assembly

For Chrome/Chromium profiles (`oblivion_forge.py`, `chromium_constructor.py`):

| File/Database | Content |
|---------------|---------|
| `Preferences` | Browser settings, extensions, default search |
| `Bookmarks` | Bookmark bar + folders |
| `History` | SQLite with `urls`, `visits`, `keyword_search_terms` |
| `Login Data` | Encrypted saved passwords (AES-256-GCM) |
| `Web Data` | Autofill, credit cards, addresses |
| `Cookies` | Encrypted cookie database |
| `Local State` | Chrome encryption key, profile info |
| `Extensions/` | Extension directories |
| `Local Storage/` | LevelDB localStorage databases |
| `IndexedDB/` | Per-origin IndexedDB databases |

---

## Stage 4: Cache Generation

**Module**: `genesis_core.py`

Generates 350-500MB of binary cache data matching real browser usage.

### Cache Contents

| Cache Type | Size | Content |
|-----------|------|---------|
| HTTP cache | 200-350MB | Cached images, scripts, stylesheets from history URLs |
| Service worker cache | 20-50MB | Progressive web app cached resources |
| Code cache | 10-30MB | V8/SpiderMonkey compiled JavaScript bytecode |
| Shader cache | 5-15MB | WebGL shader compilation cache |
| Font cache | 5-10MB | Downloaded web fonts |

### Cache Aging

Cache entries have timestamps distributed across the profile's age range, with more recent entries having higher frequency — matching real cache accumulation patterns.

---

## Stage 5: Cookie Synthesis

**Modules**: `cookie_forge.py`, `chromium_cookie_engine.py`

### Trust Anchor Cookies (Critical)

| Cookie | Domain | Max-Age | Format | Significance |
|--------|--------|---------|--------|-------------|
| `NID` | google.com | 6 months | 128-char base64 | Google tracking — proves search activity |
| `SID` | google.com | 2 years | 68-char alphanumeric | Google session — proves logged-in use |
| `HSID` | google.com | 2 years | 11-char alphanumeric | Google HTTPS session |
| `c_user` | facebook.com | 1 year | Numeric user ID | Facebook user identification |
| `datr` | facebook.com | 2 years | 24-char base64 | Facebook device cookie |
| `session-id` | amazon.com | 1 year | 140-char numeric | Amazon session (critical for Amazon targets) |
| `_ga` | (various) | 2 years | GA1.2.XXXXXXXXXX.XXXXXXXXXX | Google Analytics (on 80%+ of sites) |
| `_gid` | (various) | 24 hours | GA1.2.XXXXXXXXXX.XXXXXXXXXX | Google Analytics daily |

### Cookie Attributes

Each cookie is generated with correct:
- **Creation date**: Spread across profile age range (older cookies created earlier)
- **Expiry date**: Matches real cookie's max-age from creation date
- **SameSite**: `Lax`, `Strict`, or `None` per domain policy
- **Secure flag**: Set for HTTPS-only domains
- **HttpOnly flag**: Set for server-side cookies
- **Path**: Correct per-cookie path scope
- **Value format**: Base64, hex, UUID, JWT, or numeric as appropriate per cookie

### Chrome Cookie Encryption

For Chromium profiles, cookies are encrypted with AES-256-GCM using Chrome's DPAPI-compatible key derivation:

```
Local State → os_crypt.encrypted_key → DPAPI decrypt → AES key
Cookie value → AES-256-GCM encrypt → stored in Cookies SQLite
```

The `ChromeCryptoEngine` in `oblivion_forge.py` replicates this exactly, so Chrome's internal cookie reader accepts the database as genuine.

---

## Stage 6: Storage Synthesis

**Modules**: `indexeddb_lsng_synthesis.py`, `leveldb_writer.py`

### IndexedDB Schemas (14 Web Apps)

| Web App | Database Name | Object Stores | Key Data |
|---------|--------------|---------------|----------|
| Google | IDBWrapper-firebaseLocalStorage | user, settings | Firebase tokens, preferences |
| YouTube | yt-player-preferences | preferences, history | Player settings, watch markers |
| Facebook | fb_* | messages, notifications | Cached notifications, seen states |
| Amazon | A-cache | cart, wishlist, recent | Cart items, recently viewed |
| Netflix | nf-* | profiles, playback | Profile selection, playback position |
| Spotify | sp_* | library, playback | Library cache, play queue |
| Instagram | ig-* | feed, stories | Feed cache, story seen states |
| Discord | dc-* | messages, guilds | Server cache, unread markers |
| eBay | ebay-* | searches, watched | Search history, watched items |
| Twitter/X | twt-* | timeline, notifications | Timeline cache, notification states |
| Reddit | reddit-* | subreddits, preferences | Subscribed subs, theme preference |
| LinkedIn | li-* | profile, connections | Profile view cache |
| GitHub | gh-* | repos, notifications | Repository cache |
| Pinterest | pin-* | boards, pins | Board cache, saved pins |

### localStorage Generation

Each domain gets persona-weighted key/value pairs:

| Key Pattern | Domain | Value Type |
|-------------|--------|-----------|
| `theme`, `darkMode` | Various | "dark" or "light" (persona preference) |
| `cookieConsent` | Various | "accepted" + timestamp |
| `lastVisit` | Various | ISO timestamp |
| `cart` | Shopping sites | JSON cart state |
| `recentSearches` | Search engines | Array of search queries |
| `preferences` | Various | JSON settings object |
| `auth_token` | Social sites | JWT or opaque token |

### LevelDB Format

Chrome's localStorage uses LevelDB binary format. The `leveldb_writer.py` module uses `plyvel` bindings to write native LevelDB files that Chrome reads without error.

**Timestamp distribution**: Pareto-distributed — most entries are recent, with a long tail of older entries. This matches real accumulation patterns.

---

## Stage 7: Autofill Injection

**Module**: `form_autofill_injector.py`

### Autofill Database Contents

| Entry Type | Fields | Consistency Source |
|-----------|--------|-------------------|
| Name | First, middle, last | Stage 1 identity |
| Address | Street, city, state, ZIP, country | Stage 1 identity |
| Email | Primary + secondary | Stage 1 identity |
| Phone | Mobile + home | Stage 1 identity (area code matches) |
| Company | Employer name | Stage 2 persona |
| Credit card | Last 4 digits, cardholder name, expiry | Session card data |

### Form History

Simulated past form submissions create realistic autofill suggestions:
- Search queries in search engines
- Login usernames (not passwords) on social sites
- Address entries on shopping sites
- Contact form submissions

**Browser behavior**: When Camoufox encounters a form field, it shows autofill suggestions populated from this database — matching real Chrome/Firefox behavior.

---

## Stage 8: Purchase History

**Module**: `purchase_history_engine.py`, `commerce_injector.py`, `chromium_commerce_injector.py`

### Purchase Timeline

A typical 6-month purchase history:

```
Day -180: Small purchase ($12.99 phone case)
Day -150: Medium purchase ($34.99 book set)
Day -120: Account verification (address update)
Day -90:  Regular purchase ($49.99 headphones)
Day -60:  Subscription start (Prime trial)
Day -30:  Multiple small purchases ($15-40 range)
Day -14:  Cart abandonment (adds items, doesn't buy)
Day -7:   Wishlist activity
Day 0:    TARGET PURCHASE (appears as returning customer)
```

### Commerce Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| Order confirmation markers | Cookies + localStorage | Proves prior purchase |
| Shipping notification traces | Cookies from carrier sites | Proves delivery received |
| Review browsing history | History entries | Proves product research |
| Cart history | localStorage | Proves cart usage |
| Saved payment method indicator | localStorage | Proves payment familiarity |
| Loyalty/rewards tokens | Cookies | Proves membership |
| Wishlist items | localStorage + IndexedDB | Proves browsing intent |

### Trust Impact

| Buyer Type | Decline Rate | Profile Detection |
|-----------|-------------|-------------------|
| First-time buyer (empty profile) | ~40% | High risk |
| First-time buyer (aged profile) | ~25% | Medium risk |
| Returning customer (purchase history) | ~5% | Low risk |

Purchase history transforms profiles from "first-time buyer" → "returning customer" — a **35% improvement** in success rate.

---

## Stage 9: Quality Scoring

**Module**: `profile_realism_engine.py`

### Scoring Dimensions

| Dimension | Weight | What It Checks | Pass Threshold |
|-----------|--------|---------------|----------------|
| History depth | 20% | Enough entries for claimed age | >3,000 entries for 90+ days |
| Cookie diversity | 15% | Cookies from multiple categories | >5 domain categories |
| Temporal consistency | 20% | Circadian rhythm, no impossible timestamps | No activity at 4 AM on workdays |
| Trust anchors | 15% | Google, Facebook, Amazon cookies present | All 3 critical anchors |
| Hardware consistency | 10% | GPU matches CPU generation | No mismatches |
| Geo consistency | 10% | Timezone, locale, language all match | All 3 aligned |
| Size realism | 10% | Profile size matches claimed age | >200MB for 90+ day profile |

### Quality Grades

| Score | Grade | Action |
|-------|-------|--------|
| 90-100 | Excellent | Deploy immediately |
| 70-89 | Good | Deploy with minor warnings |
| 50-69 | Fair | Warning — review flagged dimensions |
| Below 50 | Poor | **Rejected** — auto-regenerated |

### Validation Rules

- No browsing activity between 2-5 AM on weekdays (unless persona archetype is "gamer")
- Cookie creation dates must be within profile age range
- No cookies with future expiry dates beyond 2 years
- localStorage entries must have timestamps after corresponding history entries
- Cache size must be proportional to history entry count
- Autofill data must match identity fields exactly
- Purchase history amounts must be consistent with persona income level

---

## Profile Import/Export

### Export Formats

| Format | Tool | Use Case |
|--------|------|----------|
| Titan native | `genesis_core.py` | Full profile with all 9 stages |
| MultiLogin X | `multilogin_forge.py` | Import into MultiLogin browser manager |
| GoLogin | `antidetect_importer.py` | Cross-platform sharing |
| Dolphin | `antidetect_importer.py` | Cross-platform sharing |
| Octo Browser | `antidetect_importer.py` | Cross-platform sharing |

### Secure Destruction

**Module**: `profile_burner.py`

When a profile is no longer needed:
1. Multi-pass random data overwrite (3 passes)
2. File unlink (remove from filesystem)
3. Verification scan (confirm no recoverable data)
4. Directory structure removal

Ensures destroyed profiles cannot be recovered with forensic tools.

---

## Profile Isolation

**Module**: `profile_isolation.py`

Each profile operates in complete isolation:

| Isolation Layer | Technology | Purpose |
|----------------|-----------|---------|
| Filesystem | Separate directory tree | No shared files between profiles |
| Process | Separate browser process | No shared memory |
| Network | Network namespace (optional) | No shared network state |
| DNS | Per-profile DNS resolver | No DNS cache contamination |
| Cookies | Encrypted, profile-specific key | No cookie leakage |

---

## First-Session Bias Elimination

**Module**: `first_session_bias_eliminator.py`

Even with a fully aged profile, some antifraud systems detect "first visit to THIS site" signals. The eliminator addresses this:

| Signal | What It Creates |
|--------|----------------|
| Returning visitor cookie | Site-specific identifier with past visit timestamps |
| Device fingerprint token | Previously seen device hash |
| Cross-site presence | Evidence the device visited related sites |
| Trust score booster | Historical trust signals from identity aging engine |

### Identity Aging Engine

Ages tokens to appear established:
- Cookie timestamps backdated to match first visit
- localStorage entries with incrementing visit counters
- IndexedDB entries with accumulated state
- Referrer chain showing organic discovery path

---

*Document 05 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
