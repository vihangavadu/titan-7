# 15 — App: Profile Forge (`app_profile_forge.py`)

**Version:** V9.1 | **Accent:** Cyan `#00d4ff` | **Tabs:** 4 (Identity, Forge, Profiles, Advanced)

---

## Overview

Profile Forge is a **focused, streamlined app** for building browser profiles. It extracts the identity input and 9-stage forge pipeline from the Operations Center into a dedicated window, making it easier for operators who primarily do profile generation.

Launched from the **bottom-left card** in the 3×3 launcher grid.

---

## Tab 1: IDENTITY

Input fields for the persona that will be baked into the forged profile.

| Field | Required | Description |
|-------|----------|-------------|
| **Full Name** | Yes | First + last name for the persona |
| **Email** | Yes | Email address embedded in profile artifacts |
| **Phone** | No | Phone number for form autofill |
| **Street Address** | Yes | Billing/shipping street |
| **City** | Yes | Billing city |
| **State** | Yes | Billing state/province |
| **ZIP** | Yes | Postal code |
| **Card Last 4** | Yes | Last 4 digits for purchase history realism |
| **Card Network** | Yes | Visa / Mastercard / Amex |
| **Card Expiry** | Yes | MM/YY format |
| **Target Site** | Yes | Dropdown: amazon.com, walmart.com, etc. |
| **Profile Age** | Yes | Days of simulated browsing history (30-365) |
| **Storage Size** | No | Cache size in MB (default: 500) |

---

## Tab 2: FORGE

The 9-stage pipeline with real-time progress indicators.

### Stage Pipeline

| # | Stage | Module | What It Does |
|---|-------|--------|-------------|
| 1 | **Genesis Engine** | genesis_core | Generates browsing history, cookies, localStorage for the target site |
| 2 | **Purchase History** | purchase_history_engine | Injects aged order confirmations with cardholder data |
| 3 | **IndexedDB/LSNG** | indexeddb_lsng_synthesis | Synthesizes deep storage shards (IndexedDB, LSNG) |
| 4 | **First-Session Bias** | first_session_bias_eliminator | Removes new-device detection signals |
| 5 | **Chrome Commerce** | chromium_commerce_injector | Injects purchase funnel into Chrome History DB |
| 6 | **Forensic Cache** | forensic_synthesis_engine | Generates Cache2 binary artifacts (50-5000 MB) |
| 7 | **Font Sanitizer** | font_sanitizer | Defends against font enumeration fingerprinting |
| 8 | **Audio Hardener** | audio_hardener | Masks AudioContext fingerprint |
| 9 | **Realism Scoring** | profile_realism_engine | Scores profile 0-100 with gap analysis |

### UI Elements

- **Progress bar** (0-100%) with stage name
- **Status indicators** for each module (green dot = available, red = missing)
- **Start Forge** button — begins the pipeline
- **Quality Score** display — final realism score after completion
- **Layers Applied** counter — how many of the 9 stages ran successfully

### Forge Output

After completion, the forge produces:
- Profile directory path (e.g., `/opt/titan/profiles/uuid/`)
- Profile UUID
- Quality score (0-100)
- Layers applied count (max 9)

---

## Tab 3: PROFILES

Browse and manage previously forged profiles.

| Column | Description |
|--------|-------------|
| **Profile ID** | UUID of the forged profile |
| **Persona** | Name used during forge |
| **Target** | Target site the profile was built for |
| **Quality** | Realism score (0-100) |
| **Age** | Simulated browsing age in days |
| **Created** | Timestamp of forge completion |
| **Size** | Total profile directory size |

**Actions:**
- **Open** — Open profile directory in file manager
- **Launch** — Send profile to Browser Launch app
- **Delete** — Remove profile from disk
- **Re-score** — Re-run realism scoring on existing profile

---

## Operator Workflow

1. Open Profile Forge from launcher (bottom-left card)
2. Fill in IDENTITY tab with persona details and card info
3. Select target site and profile age
4. Switch to FORGE tab, click **Start Forge**
5. Watch 9-stage pipeline progress (typically 30-90 seconds)
6. Review quality score — aim for 75+
7. If score is low, check which stages failed (red indicators)
8. Switch to PROFILES tab to manage generated profiles
9. Click **Launch** to send profile to Browser Launch app
