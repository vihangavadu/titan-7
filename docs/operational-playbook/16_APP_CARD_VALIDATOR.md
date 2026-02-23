# 16 — App: Card Validator (`app_card_validator.py`)

**Version:** V8.2.2 | **Accent:** Yellow `#eab308` | **Tabs:** 3

---

## Overview

Card Validator is a **focused app** for card validation and BIN intelligence. It extracts the validation workflow from the Operations Center into a dedicated window, providing deeper BIN analysis, card quality grading, and validation history tracking.

Launched from the **bottom-center card** in the 3×3 launcher grid.

---

## Tab 1: VALIDATE

Quick card validation with Luhn check and Cerberus engine.

| Field | Description |
|-------|-------------|
| **Card Number** | Full PAN (Primary Account Number) |
| **Expiry** | MM/YY format |
| **CVV** | 3 or 4 digit security code |
| **Cardholder Name** | Name on card |
| **Billing ZIP** | Postal code for AVS check |

### Validation Steps

1. **Luhn Algorithm** — Mathematical validity check
2. **BIN Lookup** — First 6-8 digits identify issuer, country, type
3. **Cerberus Validation** — Full card intelligence analysis
4. **AVS Check** — Address Verification System compatibility
5. **Preflight Score** — Overall card readiness score

### Output

| Field | Description |
|-------|-------------|
| **Valid** | Pass/Fail Luhn check |
| **BIN** | Bank Identification Number |
| **Issuer** | Issuing bank name |
| **Country** | Card origin country |
| **Type** | Credit / Debit / Prepaid |
| **Network** | Visa / Mastercard / Amex / Discover |
| **Level** | Classic / Gold / Platinum / World |
| **3DS Likelihood** | Probability of 3DS challenge |
| **Preflight Score** | 0-100 readiness rating |

---

## Tab 2: INTELLIGENCE

Deep BIN analysis and card quality grading.

### BIN Scoring Engine

| Metric | Weight | Description |
|--------|--------|-------------|
| **Issuer Trust** | 25% | Bank reputation and decline rate history |
| **Country Risk** | 20% | Origin country fraud risk level |
| **Card Level** | 15% | Higher level = higher limits, less scrutiny |
| **3DS Profile** | 20% | Likelihood and type of 3DS challenge |
| **Network Score** | 10% | Visa vs MC vs Amex acceptance rates |
| **Freshness** | 10% | How recently the BIN was seen in circulation |

### Card Quality Grades

| Grade | Score | Meaning |
|-------|-------|---------|
| **S** | 90-100 | Premium — high limit, low 3DS, trusted issuer |
| **A** | 75-89 | Good — reliable for most targets |
| **B** | 60-74 | Average — may trigger 3DS on some targets |
| **C** | 40-59 | Risky — frequent declines expected |
| **D** | 0-39 | Poor — prepaid/virtual, high decline rate |

### 3DS Strategy Preview

For each validated card, shows:
- **3DS version** likely to be triggered (1.0 / 2.0 / 2.1)
- **Challenge type** (OTP, biometric, push notification)
- **TRA exemption** eligibility (low-value, trusted beneficiary)
- **Recommended approach** from AI strategy engine

---

## Tab 3: HISTORY

Validation history log with search and export.

| Column | Description |
|--------|-------------|
| **Timestamp** | When the validation was performed |
| **BIN** | First 6 digits |
| **Last 4** | Last 4 digits |
| **Issuer** | Bank name |
| **Grade** | Quality grade (S/A/B/C/D) |
| **Result** | Valid / Invalid / Flagged |
| **Target** | Which target site it was checked against |

**Actions:**
- **Search** — Filter by BIN, issuer, grade, or date
- **Export** — Save history to CSV
- **Clear** — Wipe validation history

---

## Operator Workflow

1. Open Card Validator from launcher (bottom-center card)
2. Enter card details in VALIDATE tab
3. Click **Validate** — review Luhn, BIN, and preflight results
4. Switch to INTELLIGENCE tab for deep BIN analysis
5. Check card grade — S or A grades are preferred
6. Review 3DS strategy preview for the target
7. If card passes, proceed to Profile Forge → Browser Launch
8. Check HISTORY tab for patterns across multiple cards
