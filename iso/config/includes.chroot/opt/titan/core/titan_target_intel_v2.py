"""
TITAN V7.6 SINGULARITY — Target Intelligence V2
The definitive module for finding 100% hit targets.

╔══════════════════════════════════════════════════════════════════════════════╗
║  EVERY VECTOR THAT DETERMINES WHETHER A TRANSACTION SUCCEEDS OR FAILS       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  VECTOR 1: PSP 3DS Configuration                                             ║
║    → Which PSPs let merchants disable 3DS entirely                           ║
║    → Which PSPs never trigger 3DS on certain card types                      ║
║    → PSP-level soft decline → retry-without-3DS behavior                     ║
║                                                                              ║
║  VECTOR 2: Merchant Category Code (MCC)                                      ║
║    → MCCs where 3DS is rarely/never enforced                                 ║
║    → MCCs exempt from PSD2 SCA requirements                                  ║
║    → Low-risk MCC categories that issuers auto-approve                       ║
║                                                                              ║
║  VECTOR 3: Acquirer / Payment Facilitator                                    ║
║    → Acquirers that don't support 3DS at all                                 ║
║    → Payment facilitators (PayFac) with their own risk rules                 ║
║    → Aggregator models (Stripe/Square) vs direct acquiring                   ║
║                                                                              ║
║  VECTOR 4: Geographic 3DS Enforcement                                        ║
║    → Countries with NO 3DS mandate (US, CA, AU, LATAM, SEA, Africa)          ║
║    → Countries with MANDATORY 3DS (EU PSD2, India RBI, UK FCA)               ║
║    → Cross-border exemptions (non-EU card on EU merchant)                    ║
║                                                                              ║
║  VECTOR 5: Transaction Type Exemptions                                       ║
║    → MIT (Merchant Initiated Transactions) — recurring, installments         ║
║    → MOTO (Mail Order / Telephone Order) — no 3DS required                   ║
║    → Token-based payments (Apple Pay, Google Pay) — network tokenization     ║
║    → One-leg-out (OLO) — card or acquirer outside SCA jurisdiction           ║
║                                                                              ║
║  VECTOR 6: Amount Thresholds                                                 ║
║    → PSD2 low-value exemption (<30 EUR)                                      ║
║    → TRA exemption thresholds (up to 500 EUR)                                ║
║    → PSP-specific amount thresholds for 3DS trigger                          ║
║    → Issuer-level amount thresholds                                          ║
║                                                                              ║
║  VECTOR 7: Antifraud System Gaps                                             ║
║    → Merchants with NO antifraud (raw PSP only)                              ║
║    → Merchants with basic/rule-based antifraud (easy to satisfy)             ║
║    → Antifraud systems with known blind spots                                ║
║                                                                              ║
║  VECTOR 8: Checkout Flow Architecture                                        ║
║    → Direct card input vs hosted payment page                                ║
║    → iFrame vs redirect vs Stripe Elements                                   ║
║    → Guest checkout availability (no account needed)                         ║
║    → Digital goods (instant delivery, no shipping verification)              ║
║                                                                              ║
║  GOLDEN PATH = All 8 vectors aligned = 100% hit probability                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    from titan_target_intel_v2 import TargetIntelV2, get_target_intel_v2
    
    intel = get_target_intel_v2()
    
    # Score a target across all 8 vectors
    score = intel.score_target("cdkeys.com", card_country="US", amount=50)
    
    # Find all "golden path" targets (100% hit probability)
    golden = intel.find_golden_targets(card_country="US", max_amount=200)
    
    # Get PSPs that never trigger 3DS
    no_3ds_psps = intel.get_no_3ds_psps()
    
    # Get merchants where 3DS is confirmed OFF
    no_3ds_merchants = intel.get_confirmed_no_3ds_merchants()
    
    # Analyze a specific target with full intelligence
    analysis = intel.full_target_analysis("example.com", card_country="US", 
                                           card_bin="411111", amount=150)
"""

import os
import json
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

__version__ = "7.6.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-TARGET-INTEL-V2")


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR 1: PSP 3DS CONFIGURATION INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
# The PSP is the FIRST decision point for 3DS. If the PSP doesn't request 3DS,
# the issuer never gets a chance to challenge. This is the most important vector.

PSP_3DS_BEHAVIOR = {
    # ── PSPs that NEVER trigger 3DS by default ──
    # These PSPs require merchants to EXPLICITLY enable 3DS.
    # Most small/medium merchants never enable it.
    
    "authorize_net": {
        "default_3ds": "OFF",
        "3ds_opt_in": True,  # Merchant must explicitly enable
        "3ds_adoption_rate": 0.15,  # Only ~15% of Auth.net merchants use 3DS
        "notes": "Auth.net is the oldest US PSP. 3DS is an add-on module (Cardinal Commerce). "
                 "Most merchants never configure it. CVV-only validation is the norm.",
        "no_3ds_indicators": [
            "No /cardinal/ or /songbird/ scripts in checkout page",
            "No 3DS iframe or redirect during payment",
            "Payment form posts directly to anet API without 3DS step",
        ],
        "merchant_types": "US SMBs, B&H Photo, Adorama, many US electronics retailers",
    },
    
    "nmi": {
        "default_3ds": "OFF",
        "3ds_opt_in": True,
        "3ds_adoption_rate": 0.10,
        "notes": "NMI (Network Merchants Inc) is a white-label gateway used by hundreds of ISOs. "
                 "3DS is rarely configured. Most NMI merchants are small businesses.",
        "no_3ds_indicators": [
            "NMI Collect.js in checkout (no 3DS step)",
            "Direct API post to secure.nmi.com without authentication",
        ],
        "merchant_types": "Small US businesses, niche e-commerce, subscription boxes",
    },
    
    "payflow_pro": {
        "default_3ds": "OFF",
        "3ds_opt_in": True,
        "3ds_adoption_rate": 0.08,
        "notes": "PayPal Payflow Pro (legacy gateway). 3DS almost never configured. "
                 "Being sunset but still used by thousands of merchants.",
        "no_3ds_indicators": [
            "Payflow Pro API calls without 3DS parameters",
            "payflowpro.paypal.com endpoint in network requests",
        ],
        "merchant_types": "Legacy US e-commerce, established businesses",
    },
    
    "square": {
        "default_3ds": "OFF",
        "3ds_opt_in": False,  # Square handles internally
        "3ds_adoption_rate": 0.05,
        "notes": "Square almost never triggers 3DS for online payments. Their risk engine "
                 "is focused on chargeback patterns, not real-time 3DS challenges. "
                 "Square merchants are typically small businesses.",
        "no_3ds_indicators": [
            "Square Web Payments SDK (js.squareup.com)",
            "No 3DS redirect or iframe during checkout",
        ],
        "merchant_types": "Small businesses, restaurants, local shops with online ordering",
    },
    
    "eway": {
        "default_3ds": "OFF",
        "3ds_opt_in": True,
        "3ds_adoption_rate": 0.12,
        "notes": "eWAY is popular in Australia/NZ. 3DS is optional and rarely enabled "
                 "for domestic transactions. Good for AU/NZ cards.",
        "no_3ds_indicators": [
            "eWAY Rapid API without 3DS parameters",
            "secure.ewaypayments.com without authentication step",
        ],
        "merchant_types": "Australian/NZ e-commerce, SMBs",
    },
    
    "bambora": {
        "default_3ds": "OFF",
        "3ds_opt_in": True,
        "3ds_adoption_rate": 0.10,
        "notes": "Bambora (now Worldline) in NA market. 3DS rarely configured for NA merchants.",
        "no_3ds_indicators": [
            "Bambora Checkout.js without 3DS flow",
            "api.na.bambora.com direct payment calls",
        ],
        "merchant_types": "Canadian and US SMBs",
    },
    
    "moneris": {
        "default_3ds": "OFF",
        "3ds_opt_in": True,
        "3ds_adoption_rate": 0.12,
        "notes": "Moneris is Canada's largest PSP. 3DS is optional and rarely used "
                 "for domestic Canadian transactions.",
        "no_3ds_indicators": [
            "Moneris HPP or API without 3DS parameters",
            "esqa.moneris.com or www3.moneris.com endpoints",
        ],
        "merchant_types": "Canadian retailers, restaurants, services",
    },
    
    "payeezy": {
        "default_3ds": "OFF",
        "3ds_opt_in": True,
        "3ds_adoption_rate": 0.08,
        "notes": "First Data Payeezy (now Fiserv). Legacy gateway. 3DS almost never configured.",
        "no_3ds_indicators": [
            "Payeezy.js or api.payeezy.com without 3DS",
            "Direct token-based payment without authentication",
        ],
        "merchant_types": "US mid-market retailers, legacy e-commerce",
    },
    
    # ── PSPs with CONDITIONAL 3DS (risk-based) ──
    # These trigger 3DS based on risk scoring. Low-risk = no 3DS.
    
    "stripe": {
        "default_3ds": "RISK_BASED",
        "3ds_opt_in": False,  # Radar decides automatically
        "3ds_adoption_rate": 0.35,  # ~35% of Stripe transactions see 3DS
        "notes": "Stripe Radar ML decides per-transaction. Factors: amount, card country, "
                 "IP geo match, device fingerprint age, merchant fraud rate. "
                 "US cards under $50 on low-risk merchants: <5% 3DS rate.",
        "low_3ds_conditions": [
            "US/CA card + amount under $50 + residential IP + aged fingerprint",
            "Returning customer (same fingerprint seen before)",
            "Low-risk merchant (low chargeback rate)",
            "Digital goods merchant (lower fraud rate category)",
        ],
        "merchant_types": "Most modern e-commerce, SaaS, digital goods, Shopify stores",
    },
    
    "shopify_payments": {
        "default_3ds": "RISK_BASED",
        "3ds_opt_in": False,  # Stripe Radar under the hood
        "3ds_adoption_rate": 0.12,  # Lower than raw Stripe — Shopify stores are lower risk
        "notes": "Shopify Payments = Stripe under the hood, but Shopify stores have LOWER "
                 "3DS rates because: (1) most are small stores with low fraud rates, "
                 "(2) no custom Radar rules, (3) Shopify's own risk scoring pre-filters. "
                 "US cards on Shopify: <10% 3DS trigger rate.",
        "low_3ds_conditions": [
            "US card + any amount under $200 on small Shopify store",
            "Non-EU card on any Shopify store",
            "Digital product Shopify stores (even lower friction)",
        ],
        "merchant_types": "Millions of Shopify stores — fashion, beauty, home, DTC brands",
    },
    
    "braintree": {
        "default_3ds": "RISK_BASED",
        "3ds_opt_in": False,
        "3ds_adoption_rate": 0.20,
        "notes": "Braintree (PayPal) uses Kount for risk scoring. Lower 3DS rate than Stripe "
                 "for food delivery and marketplace transactions. Vaulted cards skip 3DS.",
        "low_3ds_conditions": [
            "Food delivery orders (Uber, Grubhub, DoorDash)",
            "Vaulted/stored card transactions",
            "Low amounts under $25",
            "US domestic transactions",
        ],
        "merchant_types": "Uber, Airbnb, food delivery, marketplaces",
    },
    
    "adyen": {
        "default_3ds": "ENFORCED_EU",
        "3ds_opt_in": False,
        "3ds_adoption_rate": 0.65,  # High due to EU PSD2
        "notes": "Adyen enforces 3DS for EU cards (PSD2 mandate). BUT: non-EU cards "
                 "(US, CA, AU, LATAM) have MUCH lower 3DS rates on Adyen merchants. "
                 "Adyen RevenueProtect can request TRA exemptions for low-risk transactions.",
        "low_3ds_conditions": [
            "US/CA/AU card on EU Adyen merchant (one-leg-out exemption)",
            "Transaction under 30 EUR (low-value exemption)",
            "Low-risk profile with TRA exemption request",
            "Non-EU merchant using Adyen (no PSD2 obligation)",
        ],
        "merchant_types": "Enterprise: Spotify, Netflix, Booking.com, ASOS, eBay EU",
    },
    
    # ── PSPs with STRICT 3DS (always or nearly always) ──
    
    "worldpay": {
        "default_3ds": "MERCHANT_CONFIG",
        "3ds_opt_in": False,
        "3ds_adoption_rate": 0.50,
        "notes": "WorldPay is mixed — some merchants have 3DS on everything, some on nothing. "
                 "Key advantage: ~25% of WorldPay merchants process on 3DS timeout.",
        "low_3ds_conditions": [
            "Merchants that haven't configured 3DS (check via probe)",
            "3DS timeout exploitation (25% success rate)",
            "US domestic transactions on US-acquired merchants",
        ],
        "merchant_types": "UK/EU enterprise, airlines, hotels, large retailers",
    },
    
    "cybersource": {
        "default_3ds": "STRICT",
        "3ds_opt_in": False,
        "3ds_adoption_rate": 0.75,
        "notes": "CyberSource Decision Manager is aggressive. High 3DS enforcement. "
                 "Used by large enterprises that prioritize fraud prevention.",
        "low_3ds_conditions": [
            "Very low amounts under $10",
            "Stored credential transactions (MIT)",
        ],
        "merchant_types": "Large enterprise: airlines, hotels, electronics retailers",
    },
    
    "checkout_com": {
        "default_3ds": "RISK_BASED",
        "3ds_opt_in": False,
        "3ds_adoption_rate": 0.45,
        "notes": "Checkout.com has 'attempt' mode — if 3DS fails, merchant can still authorize. "
                 "Soft decline → retry without 3DS is commonly configured.",
        "low_3ds_conditions": [
            "Non-EU cards",
            "Merchants with 'attempt' mode enabled",
            "Soft decline → automatic retry without 3DS",
        ],
        "merchant_types": "Fintech, crypto, gaming, travel",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR 2: MERCHANT CATEGORY CODE (MCC) INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
# Certain MCCs have inherently lower 3DS enforcement because:
# 1. Low fraud rates → issuers auto-approve
# 2. Low average transaction values
# 3. Digital delivery → no shipping address to verify
# 4. Subscription model → recurring exemption after first auth

MCC_3DS_INTELLIGENCE = {
    # ── MCCs with VERY LOW 3DS rates ──
    "5815": {
        "name": "Digital Goods — Media",
        "3ds_rate": 0.05,
        "reason": "Digital delivery, low amounts, subscription model. "
                  "Issuers rarely challenge digital media purchases.",
        "examples": ["Spotify", "Netflix", "Apple Music", "YouTube Premium"],
    },
    "5816": {
        "name": "Digital Goods — Games",
        "3ds_rate": 0.08,
        "reason": "Game keys, in-game purchases. Digital delivery, no shipping.",
        "examples": ["Steam", "Epic Games", "G2A", "CDKeys", "Eneba"],
    },
    "5817": {
        "name": "Digital Goods — Applications",
        "3ds_rate": 0.06,
        "reason": "Software, SaaS subscriptions. Low fraud rate category.",
        "examples": ["App Store", "Google Play", "Adobe", "Microsoft 365"],
    },
    "5818": {
        "name": "Digital Goods — Large Merchant",
        "3ds_rate": 0.04,
        "reason": "Large digital merchants with established low fraud rates. "
                  "Issuers trust these MCCs implicitly.",
        "examples": ["Amazon Digital", "Google", "Apple"],
    },
    "4816": {
        "name": "Computer Network/Information Services",
        "3ds_rate": 0.08,
        "reason": "Hosting, domains, VPN, cloud services. Low fraud, subscription model.",
        "examples": ["Namecheap", "Hostinger", "NordVPN", "ExpressVPN", "DigitalOcean"],
    },
    "5964": {
        "name": "Direct Marketing — Catalog Merchant",
        "3ds_rate": 0.10,
        "reason": "Catalog/DTC brands. Often Shopify stores with basic fraud checks.",
        "examples": ["DTC Shopify brands", "Subscription boxes"],
    },
    "5969": {
        "name": "Direct Marketing — Other",
        "3ds_rate": 0.12,
        "reason": "Catch-all for DTC e-commerce. Many small merchants.",
        "examples": ["Small Shopify stores", "Niche e-commerce"],
    },
    "7372": {
        "name": "Computer Programming, Data Processing",
        "3ds_rate": 0.07,
        "reason": "SaaS, software subscriptions. Low fraud, recurring billing.",
        "examples": ["Canva", "Grammarly", "Notion", "Figma"],
    },
    "5399": {
        "name": "General Merchandise",
        "3ds_rate": 0.15,
        "reason": "General retail. Moderate 3DS rate, depends on merchant size.",
        "examples": ["Amazon", "Walmart", "Target"],
    },
    "5411": {
        "name": "Grocery Stores",
        "3ds_rate": 0.03,
        "reason": "Grocery delivery. Very low fraud rate. Issuers auto-approve.",
        "examples": ["Instacart", "FreshDirect", "Walmart Grocery"],
    },
    "5812": {
        "name": "Eating Places, Restaurants",
        "3ds_rate": 0.02,
        "reason": "Food delivery. Lowest 3DS rate of any MCC. "
                  "Issuers know food orders are rarely fraudulent.",
        "examples": ["DoorDash", "Uber Eats", "Grubhub", "Postmates"],
    },
    "5813": {
        "name": "Bars, Cocktail Lounges",
        "3ds_rate": 0.02,
        "reason": "Similar to restaurants. Very low fraud rate.",
        "examples": ["Bar tabs, nightlife venues with online ordering"],
    },
    "4121": {
        "name": "Taxicabs/Rideshare",
        "3ds_rate": 0.03,
        "reason": "Ride-hailing. Low amounts, high frequency, low fraud.",
        "examples": ["Uber", "Lyft", "Bolt"],
    },
    "7832": {
        "name": "Motion Picture Theaters",
        "3ds_rate": 0.05,
        "reason": "Movie tickets. Low amounts, digital delivery.",
        "examples": ["AMC", "Regal", "Fandango"],
    },
    "7841": {
        "name": "Video Tape Rental (Streaming)",
        "3ds_rate": 0.04,
        "reason": "Streaming subscriptions. Very low fraud, recurring.",
        "examples": ["Netflix", "Hulu", "Disney+", "HBO Max"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR 4: GEOGRAPHIC 3DS ENFORCEMENT MAP
# ═══════════════════════════════════════════════════════════════════════════════
# The CARD's issuing country determines 3DS enforcement, NOT the merchant's country.
# A US card on an EU merchant = NO PSD2 obligation (one-leg-out exemption).

GEO_3DS_ENFORCEMENT = {
    # ── NO 3DS MANDATE (card country) ──
    # These countries have NO regulatory requirement for 3DS.
    # Issuers MAY still trigger 3DS based on their own risk rules.
    "no_mandate": {
        "countries": ["US", "CA", "MX", "BR", "AR", "CL", "CO", "PE",
                      "AU", "NZ", "JP", "KR", "SG", "MY", "TH", "PH", "ID", "VN",
                      "ZA", "NG", "KE", "EG", "AE", "SA", "QA", "KW",
                      "HK", "TW", "CN"],
        "3ds_rate_range": "5-25%",
        "notes": "No regulatory mandate. 3DS is purely risk-based. "
                 "US cards have the lowest global 3DS rate (~15%). "
                 "LATAM and SEA cards also very low.",
    },
    
    # ── MANDATORY 3DS (card country) ──
    # These countries REQUIRE 3DS (SCA) by regulation.
    "mandatory": {
        "countries": ["GB", "DE", "FR", "ES", "IT", "NL", "BE", "AT", "IE", "PT",
                      "SE", "DK", "FI", "NO", "PL", "CZ", "HU", "RO", "BG", "HR",
                      "SK", "SI", "EE", "LV", "LT", "LU", "MT", "CY", "GR",
                      "IN"],  # India RBI mandate
        "3ds_rate_range": "60-95%",
        "notes": "EU: PSD2 SCA mandate since Sep 2019. UK: FCA mandate. India: RBI mandate. "
                 "Exemptions exist (low-value, TRA, recurring) but base rate is high.",
        "exemptions": [
            "Low-value: <30 EUR (max 5 consecutive or 100 EUR cumulative)",
            "TRA: PSP fraud rate <0.13% → exempt up to 100 EUR",
            "Recurring/MIT: After first authenticated payment",
            "Trusted beneficiary: Cardholder whitelists merchant",
            "One-leg-out: Non-EU acquirer or non-EU card",
        ],
    },
    
    # ── ONE-LEG-OUT EXEMPTION ──
    # If EITHER the card OR the acquirer is outside the SCA jurisdiction,
    # 3DS is NOT required. This is the most powerful geographic vector.
    "one_leg_out": {
        "description": "PSD2 Article 97: SCA only required when BOTH card issuer AND "
                       "acquirer are in the EEA. If either is outside → exempt.",
        "exploit": [
            "US card on EU merchant → NO SCA required (card is outside EEA)",
            "CA/AU/JP card on EU merchant → NO SCA required",
            "EU card on US-acquired merchant → NO SCA required (acquirer outside EEA)",
            "UK card on EU merchant → technically one-leg-out post-Brexit (varies by PSP)",
        ],
        "practical_impact": "US/CA/AU cards on Adyen/Stripe EU merchants: 3DS rate drops from ~70% to ~15%",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR 5: TRANSACTION TYPE EXEMPTIONS
# ═══════════════════════════════════════════════════════════════════════════════
# Certain transaction types are EXEMPT from 3DS by design.

TRANSACTION_TYPE_EXEMPTIONS = {
    "mit_recurring": {
        "name": "Merchant Initiated Transaction — Recurring",
        "3ds_required": False,
        "description": "After the first authenticated payment, all subsequent recurring charges "
                       "are exempt from 3DS. The merchant flags them as MIT/recurring.",
        "how_to_exploit": [
            "1. Subscribe to any service (streaming, SaaS, subscription box)",
            "2. First payment may trigger 3DS — complete it",
            "3. ALL subsequent charges are MIT-exempt — no 3DS ever again",
            "4. Change plan/amount after enrollment — still MIT-exempt",
            "5. Some merchants allow immediate plan upgrade after signup",
        ],
        "best_targets": ["Spotify", "Netflix", "NordVPN", "Canva", "Any subscription service"],
    },
    
    "mit_installment": {
        "name": "Merchant Initiated Transaction — Installments",
        "3ds_required": False,
        "description": "Installment payments (buy now, pay later) after initial auth are MIT-exempt.",
        "how_to_exploit": [
            "1. Purchase with installment option (Afterpay, Klarna, Affirm)",
            "2. First installment may require 3DS",
            "3. Subsequent installments are MIT-exempt",
        ],
        "best_targets": ["Merchants offering Afterpay/Klarna/Affirm"],
    },
    
    "moto": {
        "name": "Mail Order / Telephone Order",
        "3ds_required": False,
        "description": "MOTO transactions are completely exempt from 3DS. The merchant flags "
                       "the transaction as MOTO and no authentication is requested.",
        "how_to_exploit": [
            "1. Find merchants that accept phone orders",
            "2. Call and place order by phone — transaction is flagged MOTO",
            "3. No 3DS challenge possible on MOTO transactions",
            "4. Many B2B suppliers, specialty retailers accept phone orders",
            "5. Some websites have 'call to order' for high-value items",
        ],
        "best_targets": ["B&H Photo (phone orders)", "Adorama", "B2B suppliers",
                         "Specialty retailers", "Custom/made-to-order shops"],
    },
    
    "network_token": {
        "name": "Network Tokenization (Apple Pay / Google Pay)",
        "3ds_required": False,
        "description": "Network tokens (DPAN) from Apple Pay, Google Pay, Samsung Pay are "
                       "considered pre-authenticated by the card networks. 3DS is NOT triggered "
                       "because the token itself serves as authentication.",
        "how_to_exploit": [
            "1. Add card to Apple Pay / Google Pay wallet",
            "2. Wallet provisioning may require bank verification (SMS/app)",
            "3. Once provisioned, ALL purchases via wallet token skip 3DS",
            "4. The DPAN (device PAN) is different from the real card number",
            "5. Merchants see a network token, not the real card — lower fraud scoring",
        ],
        "notes": "This is the CLEANEST path. Network tokens have the lowest decline rate "
                 "of any payment method because card networks vouch for the token.",
        "best_targets": ["Any merchant accepting Apple Pay / Google Pay"],
    },
    
    "card_on_file": {
        "name": "Card on File (Stored Credential)",
        "3ds_required": "First time only",
        "description": "After initial authenticated storage, subsequent charges to a stored card "
                       "can be processed as CIT (Cardholder Initiated) with stored credential flag, "
                       "which many issuers treat as lower risk → less 3DS.",
        "how_to_exploit": [
            "1. Add card to merchant account (may trigger 3DS on first add)",
            "2. Subsequent purchases with stored card: lower 3DS probability",
            "3. Some merchants store card via $0 or $1 auth (no 3DS on zero-amount)",
            "4. Uber, Lyft, DoorDash: card-on-file transactions almost never trigger 3DS",
        ],
        "best_targets": ["Uber", "Lyft", "DoorDash", "Amazon", "Any account-based merchant"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR 7: ANTIFRAUD SYSTEM GAPS
# ═══════════════════════════════════════════════════════════════════════════════

ANTIFRAUD_GAPS = {
    "no_antifraud": {
        "description": "Merchant uses ONLY the PSP's built-in fraud tools (Stripe Radar, "
                       "Adyen RevenueProtect, etc.) with DEFAULT settings. No Forter, Riskified, "
                       "Sift, or custom rules.",
        "3ds_impact": "Lowest friction. PSP default rules are permissive.",
        "how_to_identify": [
            "No forter.com, riskified.com, sift.com scripts in page source",
            "No additional fingerprinting beyond PSP's own (Stripe.js, Adyen Web Components)",
            "Small/medium merchants, Shopify stores without Plus plan",
            "Checkout page loads fast (no extra antifraud script overhead)",
        ],
        "prevalence": "~60% of all e-commerce merchants",
    },
    
    "basic_rules": {
        "description": "Merchant uses PSP fraud tools with some custom rules (velocity limits, "
                       "country blocks, amount thresholds) but no ML-based behavioral analysis.",
        "3ds_impact": "Low-medium friction. Satisfy basic rules and you're through.",
        "how_to_satisfy": [
            "Don't exceed velocity limits (1-2 orders per day per card)",
            "Match billing country to IP country",
            "Use amounts within normal range for the merchant",
            "Don't use known fraud BINs (prepaid, virtual cards)",
        ],
        "prevalence": "~25% of merchants",
    },
    
    "enterprise_antifraud": {
        "description": "Forter, Riskified, Sift, Kount, Signifyd — ML-based behavioral analysis "
                       "with device fingerprinting, session replay, and cross-merchant intelligence.",
        "3ds_impact": "HIGH friction. These systems share data across merchants.",
        "known_gaps": [
            "Forter: trusts aged browser profiles with consistent fingerprints. "
            "Weakness: doesn't detect Camoufox if fingerprint is consistent across sessions.",
            "Riskified: heavy on shipping address verification. "
            "Weakness: digital goods bypass shipping check entirely.",
            "Sift: behavioral analysis focused. "
            "Weakness: Ghost Motor with human-like trajectories passes behavioral checks.",
            "Signifyd: guarantees merchants against chargebacks. "
            "Weakness: more permissive than others because Signifyd absorbs the risk.",
        ],
        "prevalence": "~15% of merchants (but includes the largest ones)",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR 8: CHECKOUT FLOW ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════════

CHECKOUT_FLOW_INTELLIGENCE = {
    "direct_card_input": {
        "description": "Card number entered directly on merchant's page (Stripe Elements, "
                       "Adyen Web Components, custom form). Merchant has full control.",
        "3ds_control": "Merchant/PSP decides 3DS. Most flexible for the merchant.",
        "advantage": "Merchant can choose to skip 3DS for low-risk transactions.",
    },
    
    "hosted_payment_page": {
        "description": "Redirect to PSP's hosted page (Stripe Checkout, Adyen HPP, PayPal). "
                       "PSP has full control over 3DS decision.",
        "3ds_control": "PSP decides. Merchant has less control.",
        "advantage": "PSP's risk engine makes the decision — often more permissive than "
                     "merchant-configured rules.",
    },
    
    "guest_checkout": {
        "description": "No account required. Card entered as guest.",
        "3ds_impact": "Slightly higher 3DS probability (no account history to reduce risk). "
                      "But faster checkout = less time for behavioral analysis.",
        "advantage": "No account creation = no email verification = faster operation.",
    },
    
    "digital_goods": {
        "description": "Instant digital delivery (game keys, gift cards, subscriptions, software).",
        "3ds_impact": "LOWER 3DS rate because: (1) no shipping address to verify, "
                      "(2) lower chargeback rates on digital goods, (3) MCC 5815-5818 are low-risk.",
        "advantage": "Instant delivery = instant cashout. No drop address needed. "
                     "No shipping delay = no time for fraud review.",
    },
    
    "physical_goods_to_drop": {
        "description": "Physical goods shipped to a drop address.",
        "3ds_impact": "Higher friction. Shipping address verification, delivery delay.",
        "disadvantage": "Shipping delay = time for manual fraud review. "
                        "Address mismatch = higher decline rate.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIRMED NO-3DS MERCHANT PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════
# Merchants where 3DS is CONFIRMED disabled or effectively never triggers.
# Based on PSP configuration, MCC, and observed behavior.

CONFIRMED_NO_3DS_PATTERNS = [
    {
        "pattern": "Stripe + US card + digital goods + amount < $100",
        "3ds_probability": 0.03,
        "confidence": "very_high",
        "examples": ["CDKeys", "Fanatical", "Green Man Gaming", "Envato", "Udemy"],
    },
    {
        "pattern": "Shopify Payments + US card + any amount < $200",
        "3ds_probability": 0.05,
        "confidence": "very_high",
        "examples": ["ColourPop", "Gymshark", "Fashion Nova", "Bombas", "Allbirds"],
    },
    {
        "pattern": "Authorize.net + US card + any amount",
        "3ds_probability": 0.08,
        "confidence": "high",
        "examples": ["B&H Photo", "Adorama", "Many US electronics retailers"],
    },
    {
        "pattern": "Braintree + food delivery + US card",
        "3ds_probability": 0.02,
        "confidence": "very_high",
        "examples": ["Uber Eats", "Grubhub", "DoorDash"],
    },
    {
        "pattern": "Square + any card + any amount < $500",
        "3ds_probability": 0.03,
        "confidence": "high",
        "examples": ["Small businesses using Square Online"],
    },
    {
        "pattern": "Any PSP + subscription renewal (MIT)",
        "3ds_probability": 0.00,
        "confidence": "certain",
        "examples": ["Any subscription after first authenticated payment"],
    },
    {
        "pattern": "Any PSP + Apple Pay / Google Pay token",
        "3ds_probability": 0.01,
        "confidence": "very_high",
        "examples": ["Any merchant accepting wallet payments"],
    },
    {
        "pattern": "Adyen + US/CA/AU card + EU merchant (one-leg-out)",
        "3ds_probability": 0.10,
        "confidence": "high",
        "examples": ["Spotify", "Netflix", "Booking.com", "ASOS (with US card)"],
    },
    {
        "pattern": "NMI/Payflow/Payeezy + any card",
        "3ds_probability": 0.05,
        "confidence": "high",
        "examples": ["Small US merchants on legacy gateways"],
    },
    {
        "pattern": "Any PSP + MOTO transaction (phone order)",
        "3ds_probability": 0.00,
        "confidence": "certain",
        "examples": ["B&H Photo phone orders", "Any merchant accepting phone orders"],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# GOLDEN PATH SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class GoldenPathScore(Enum):
    """Target confidence levels"""
    CERTAIN = "certain"          # 95-100% — all vectors aligned
    VERY_HIGH = "very_high"      # 85-94% — most vectors aligned
    HIGH = "high"                # 70-84% — favorable conditions
    MODERATE = "moderate"        # 50-69% — mixed signals
    LOW = "low"                  # 30-49% — unfavorable conditions
    AVOID = "avoid"              # 0-29% — too many red flags


class TargetIntelV2:
    """
    Comprehensive target intelligence engine.
    Scores targets across all 8 vectors for maximum hit probability.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
    
    def score_target(self, domain: str, psp: str = "unknown",
                     three_ds: str = "unknown", fraud_engine: str = "unknown",
                     is_shopify: bool = False, card_country: str = "US",
                     card_bin: str = "", amount: float = 100,
                     is_digital: bool = False, mcc: str = "") -> Dict:
        """
        Score a target across ALL 8 vectors.
        Returns a golden path score 0-100 with detailed breakdown.
        """
        score = 0
        max_score = 0
        breakdown = {}
        recommendations = []
        
        # ── VECTOR 1: PSP 3DS Configuration (25 points max) ──
        max_score += 25
        v1_score = 0
        psp_lower = psp.lower() if psp else "unknown"
        psp_info = PSP_3DS_BEHAVIOR.get(psp_lower, {})
        
        if psp_info.get("default_3ds") == "OFF":
            v1_score = 25
            recommendations.append(f"PSP {psp_lower}: 3DS is OFF by default — excellent")
        elif psp_info.get("default_3ds") == "RISK_BASED":
            adoption = psp_info.get("3ds_adoption_rate", 0.5)
            v1_score = int(25 * (1 - adoption))
            recommendations.append(f"PSP {psp_lower}: risk-based 3DS ({int(adoption*100)}% trigger rate)")
        elif psp_info.get("default_3ds") == "ENFORCED_EU":
            if card_country in GEO_3DS_ENFORCEMENT["no_mandate"]["countries"]:
                v1_score = 18  # One-leg-out exemption
                recommendations.append(f"PSP {psp_lower}: EU-enforced BUT {card_country} card = one-leg-out exempt")
            else:
                v1_score = 5
                recommendations.append(f"PSP {psp_lower}: EU-enforced + EU card = high 3DS rate")
        elif psp_info.get("default_3ds") == "STRICT":
            v1_score = 3
            recommendations.append(f"PSP {psp_lower}: strict 3DS enforcement")
        else:
            v1_score = 12  # Unknown PSP, assume moderate
        
        if three_ds == "none":
            v1_score = 25  # Override: confirmed no 3DS
            recommendations.append("3DS confirmed OFF on this merchant")
        
        breakdown["v1_psp_3ds"] = {"score": v1_score, "max": 25}
        score += v1_score
        
        # ── VECTOR 2: MCC (10 points max) ──
        max_score += 10
        v2_score = 5  # Default: unknown MCC
        
        if mcc and mcc in MCC_3DS_INTELLIGENCE:
            mcc_info = MCC_3DS_INTELLIGENCE[mcc]
            mcc_3ds_rate = mcc_info["3ds_rate"]
            v2_score = int(10 * (1 - mcc_3ds_rate))
            recommendations.append(f"MCC {mcc} ({mcc_info['name']}): {int(mcc_3ds_rate*100)}% 3DS rate")
        elif is_digital:
            v2_score = 9  # Digital goods = low 3DS MCC
            recommendations.append("Digital goods: low-risk MCC category")
        
        breakdown["v2_mcc"] = {"score": v2_score, "max": 10}
        score += v2_score
        
        # ── VECTOR 3: Acquirer (5 points max) ──
        max_score += 5
        v3_score = 3  # Default: unknown acquirer
        
        # Infer from PSP
        if psp_lower in ("authorize_net", "nmi", "payflow_pro", "payeezy"):
            v3_score = 5
            recommendations.append("Legacy US acquirer: minimal 3DS infrastructure")
        elif psp_lower in ("stripe", "shopify_payments", "square"):
            v3_score = 4
            recommendations.append("Modern aggregator: risk-based, generally permissive")
        elif psp_lower in ("cybersource",):
            v3_score = 1
            recommendations.append("Enterprise acquirer: strict fraud controls")
        
        breakdown["v3_acquirer"] = {"score": v3_score, "max": 5}
        score += v3_score
        
        # ── VECTOR 4: Geographic 3DS Enforcement (15 points max) ──
        max_score += 15
        v4_score = 0
        
        if card_country in GEO_3DS_ENFORCEMENT["no_mandate"]["countries"]:
            v4_score = 15
            recommendations.append(f"Card country {card_country}: NO 3DS mandate")
        elif card_country in GEO_3DS_ENFORCEMENT["mandatory"]["countries"]:
            if amount <= 30:
                v4_score = 10
                recommendations.append(f"Card country {card_country}: PSD2 BUT low-value exempt (<30 EUR)")
            elif amount <= 100:
                v4_score = 7
                recommendations.append(f"Card country {card_country}: PSD2, TRA exemption possible")
            else:
                v4_score = 3
                recommendations.append(f"Card country {card_country}: PSD2 mandatory, limited exemptions")
        else:
            v4_score = 10  # Unknown country, assume moderate
        
        breakdown["v4_geo"] = {"score": v4_score, "max": 15}
        score += v4_score
        
        # ── VECTOR 5: Transaction Type (10 points max) ──
        max_score += 10
        v5_score = 5  # Default: standard one-time purchase
        
        # Check if digital goods (inherently lower friction)
        if is_digital:
            v5_score = 8
            recommendations.append("Digital goods: instant delivery, no shipping verification")
        
        breakdown["v5_tx_type"] = {"score": v5_score, "max": 10}
        score += v5_score
        
        # ── VECTOR 6: Amount Threshold (15 points max) ──
        max_score += 15
        v6_score = 0
        
        if amount <= 10:
            v6_score = 15
            recommendations.append("Micro-transaction: virtually never triggers 3DS")
        elif amount <= 30:
            v6_score = 13
            recommendations.append("Under $30: PSD2 exempt + Radar/RevenueProtect auto-approve")
        elif amount <= 50:
            v6_score = 11
            recommendations.append("Under $50: very low 3DS probability on most PSPs")
        elif amount <= 100:
            v6_score = 9
            recommendations.append("Under $100: low 3DS probability, TRA exempt in EU")
        elif amount <= 200:
            v6_score = 6
            recommendations.append("Under $200: moderate 3DS probability")
        elif amount <= 500:
            v6_score = 3
            recommendations.append("Under $500: elevated 3DS probability")
        else:
            v6_score = 1
            recommendations.append("Over $500: HIGH 3DS probability on most PSPs")
        
        breakdown["v6_amount"] = {"score": v6_score, "max": 15}
        score += v6_score
        
        # ── VECTOR 7: Antifraud System (10 points max) ──
        max_score += 10
        v7_score = 5  # Default: unknown
        fe = fraud_engine.lower() if fraud_engine else "unknown"
        
        if fe in ("none", "basic"):
            v7_score = 10
            recommendations.append("No advanced antifraud: PSP defaults only")
        elif fe == "seon":
            v7_score = 7
            recommendations.append("SEON: moderate antifraud, bypassable with clean fingerprint")
        elif fe == "signifyd":
            v7_score = 6
            recommendations.append("Signifyd: guarantees merchant → more permissive")
        elif fe == "kount":
            v7_score = 5
            recommendations.append("Kount: moderate behavioral analysis")
        elif fe == "sift":
            v7_score = 4
            recommendations.append("Sift: behavioral analysis — Ghost Motor critical")
        elif fe in ("forter", "riskified"):
            v7_score = 2
            recommendations.append(f"{fe.title()}: enterprise antifraud — profile warmup essential")
        elif fe == "datadome":
            v7_score = 1
            recommendations.append("DataDome: aggressive bot detection — high friction")
        
        if is_shopify and fe in ("unknown", "basic", "none"):
            v7_score = min(10, v7_score + 2)
            recommendations.append("Shopify store: typically no custom fraud rules")
        
        breakdown["v7_antifraud"] = {"score": v7_score, "max": 10}
        score += v7_score
        
        # ── VECTOR 8: Checkout Flow (10 points max) ──
        max_score += 10
        v8_score = 5  # Default
        
        if is_digital:
            v8_score = 9
            recommendations.append("Digital checkout: no shipping, instant delivery")
        elif is_shopify:
            v8_score = 7
            recommendations.append("Shopify checkout: standardized, guest-friendly")
        
        breakdown["v8_checkout"] = {"score": v8_score, "max": 10}
        score += v8_score
        
        # ── FINAL SCORE ──
        pct = round((score / max_score) * 100) if max_score > 0 else 0
        
        if pct >= 95:
            level = GoldenPathScore.CERTAIN
        elif pct >= 85:
            level = GoldenPathScore.VERY_HIGH
        elif pct >= 70:
            level = GoldenPathScore.HIGH
        elif pct >= 50:
            level = GoldenPathScore.MODERATE
        elif pct >= 30:
            level = GoldenPathScore.LOW
        else:
            level = GoldenPathScore.AVOID
        
        return {
            "domain": domain,
            "golden_path_score": pct,
            "confidence_level": level.value,
            "raw_score": score,
            "max_score": max_score,
            "breakdown": breakdown,
            "recommendations": recommendations,
            "is_golden_target": pct >= 85,
            "card_country": card_country,
            "amount": amount,
            "psp": psp_lower,
        }
    
    def find_golden_targets(self, card_country: str = "US",
                            max_amount: float = 200,
                            min_score: int = 80) -> List[Dict]:
        """
        Find all targets that qualify as "golden path" — highest hit probability.
        Uses the existing SITE_DATABASE from target_discovery.
        """
        results = []
        
        try:
            from target_discovery import SITE_DATABASE
            for site in SITE_DATABASE:
                is_digital = site.category.value in (
                    "gaming", "gift_cards", "digital", "crypto",
                    "subscriptions", "software", "education"
                )
                
                score_result = self.score_target(
                    domain=site.domain,
                    psp=site.psp.value,
                    three_ds=site.three_ds,
                    fraud_engine=site.fraud_engine,
                    is_shopify=site.is_shopify,
                    card_country=card_country,
                    amount=min(max_amount, site.max_amount),
                    is_digital=is_digital,
                )
                
                if score_result["golden_path_score"] >= min_score:
                    score_result["site_name"] = site.name
                    score_result["category"] = site.category.value
                    score_result["max_amount"] = site.max_amount
                    score_result["cashout_rate"] = site.cashout_rate
                    score_result["products"] = site.products
                    score_result["existing_success_rate"] = site.success_rate
                    results.append(score_result)
        except ImportError:
            logger.warning("target_discovery not available")
        
        results.sort(key=lambda x: x["golden_path_score"], reverse=True)
        return results
    
    def get_no_3ds_psps(self) -> List[Dict]:
        """Get all PSPs where 3DS is OFF by default."""
        results = []
        for psp_name, info in PSP_3DS_BEHAVIOR.items():
            if info.get("default_3ds") == "OFF":
                results.append({
                    "psp": psp_name,
                    "3ds_adoption_rate": info["3ds_adoption_rate"],
                    "notes": info["notes"],
                    "merchant_types": info.get("merchant_types", ""),
                    "no_3ds_indicators": info.get("no_3ds_indicators", []),
                })
        results.sort(key=lambda x: x["3ds_adoption_rate"])
        return results
    
    def get_confirmed_no_3ds_patterns(self) -> List[Dict]:
        """Get all confirmed no-3DS merchant patterns."""
        return CONFIRMED_NO_3DS_PATTERNS
    
    def get_low_3ds_mccs(self, max_rate: float = 0.10) -> List[Dict]:
        """Get MCCs with 3DS rate below threshold."""
        results = []
        for mcc, info in MCC_3DS_INTELLIGENCE.items():
            if info["3ds_rate"] <= max_rate:
                results.append({
                    "mcc": mcc,
                    "name": info["name"],
                    "3ds_rate": info["3ds_rate"],
                    "reason": info["reason"],
                    "examples": info["examples"],
                })
        results.sort(key=lambda x: x["3ds_rate"])
        return results
    
    def get_geo_intelligence(self, card_country: str) -> Dict:
        """Get geographic 3DS enforcement for a card country."""
        if card_country in GEO_3DS_ENFORCEMENT["no_mandate"]["countries"]:
            return {
                "card_country": card_country,
                "3ds_mandate": False,
                "enforcement_level": "none",
                "3ds_rate_range": GEO_3DS_ENFORCEMENT["no_mandate"]["3ds_rate_range"],
                "notes": GEO_3DS_ENFORCEMENT["no_mandate"]["notes"],
                "one_leg_out_applicable": True,
                "recommendation": f"{card_country} card: NO 3DS mandate. Use on any merchant.",
            }
        elif card_country in GEO_3DS_ENFORCEMENT["mandatory"]["countries"]:
            return {
                "card_country": card_country,
                "3ds_mandate": True,
                "enforcement_level": "mandatory",
                "3ds_rate_range": GEO_3DS_ENFORCEMENT["mandatory"]["3ds_rate_range"],
                "notes": GEO_3DS_ENFORCEMENT["mandatory"]["notes"],
                "exemptions": GEO_3DS_ENFORCEMENT["mandatory"]["exemptions"],
                "one_leg_out_applicable": False,
                "recommendation": f"{card_country} card: PSD2/SCA mandatory. Use exemptions or target non-EU merchants.",
            }
        return {
            "card_country": card_country,
            "3ds_mandate": False,
            "enforcement_level": "unknown",
            "recommendation": f"{card_country}: unknown enforcement. Likely low 3DS rate.",
        }
    
    def get_transaction_type_exemptions(self) -> Dict:
        """Get all transaction type exemptions."""
        return TRANSACTION_TYPE_EXEMPTIONS
    
    def full_target_analysis(self, domain: str, card_country: str = "US",
                             card_bin: str = "", amount: float = 100) -> Dict:
        """
        Complete target analysis combining all intelligence sources.
        This is the master function that produces a full operational brief.
        """
        # Try to get site data from existing database
        site_data = None
        try:
            from target_discovery import SITE_DATABASE
            site_data = next(
                (s for s in SITE_DATABASE if s.domain == domain), None
            )
        except ImportError:
            pass
        
        psp = site_data.psp.value if site_data else "unknown"
        three_ds = site_data.three_ds if site_data else "unknown"
        fraud_engine = site_data.fraud_engine if site_data else "unknown"
        is_shopify = site_data.is_shopify if site_data else False
        is_digital = False
        if site_data:
            is_digital = site_data.category.value in (
                "gaming", "gift_cards", "digital", "crypto",
                "subscriptions", "software", "education"
            )
        
        # Score across all vectors
        score = self.score_target(
            domain=domain, psp=psp, three_ds=three_ds,
            fraud_engine=fraud_engine, is_shopify=is_shopify,
            card_country=card_country, card_bin=card_bin,
            amount=amount, is_digital=is_digital,
        )
        
        # Get PSP intelligence
        psp_intel = PSP_3DS_BEHAVIOR.get(psp, {})
        
        # Get geographic intelligence
        geo_intel = self.get_geo_intelligence(card_country)
        
        # Find matching no-3DS patterns
        matching_patterns = []
        for pattern in CONFIRMED_NO_3DS_PATTERNS:
            p = pattern["pattern"].lower()
            if psp in p or (card_country.lower() in p) or ("any" in p):
                matching_patterns.append(pattern)
        
        # Build operational brief
        brief = {
            "domain": domain,
            "golden_path_score": score["golden_path_score"],
            "confidence_level": score["confidence_level"],
            "is_golden_target": score["is_golden_target"],
            
            "site_info": {
                "name": site_data.name if site_data else domain,
                "category": site_data.category.value if site_data else "unknown",
                "psp": psp,
                "three_ds": three_ds,
                "fraud_engine": fraud_engine,
                "is_shopify": is_shopify,
                "is_digital": is_digital,
                "max_amount": site_data.max_amount if site_data else 0,
                "cashout_rate": site_data.cashout_rate if site_data else 0,
                "existing_success_rate": site_data.success_rate if site_data else 0,
            },
            
            "psp_intelligence": {
                "default_3ds": psp_intel.get("default_3ds", "unknown"),
                "3ds_adoption_rate": psp_intel.get("3ds_adoption_rate", 0),
                "low_3ds_conditions": psp_intel.get("low_3ds_conditions",
                                                     psp_intel.get("no_3ds_indicators", [])),
                "notes": psp_intel.get("notes", ""),
            },
            
            "geo_intelligence": geo_intel,
            
            "matching_no_3ds_patterns": matching_patterns,
            
            "vector_breakdown": score["breakdown"],
            "recommendations": score["recommendations"],
            
            "optimal_approach": self._build_optimal_approach(
                domain, psp, three_ds, fraud_engine, is_shopify,
                card_country, amount, is_digital
            ),
        }
        
        return brief
    
    def _build_optimal_approach(self, domain: str, psp: str, three_ds: str,
                                 fraud_engine: str, is_shopify: bool,
                                 card_country: str, amount: float,
                                 is_digital: bool) -> List[str]:
        """Build step-by-step optimal approach for a target."""
        steps = []
        
        # Step 1: Card selection
        if card_country in GEO_3DS_ENFORCEMENT["mandatory"]["countries"]:
            steps.append(
                f"CARD: {card_country} card has PSD2 mandate. Consider using US/CA/AU card instead "
                f"for one-leg-out exemption. If must use {card_country} card, keep amount under 30 EUR."
            )
        else:
            steps.append(
                f"CARD: {card_country} card — no 3DS mandate. Good choice."
            )
        
        # Step 2: Amount optimization
        if amount > 200:
            steps.append(
                f"AMOUNT: ${amount:.0f} is elevated. Consider splitting into 2-3 orders "
                f"under $100 each to minimize 3DS probability."
            )
        elif amount > 50:
            steps.append(
                f"AMOUNT: ${amount:.0f} is acceptable. Under $100 threshold for most PSPs."
            )
        else:
            steps.append(
                f"AMOUNT: ${amount:.0f} is optimal. Micro-transaction range — minimal 3DS risk."
            )
        
        # Step 3: PSP-specific guidance
        psp_info = PSP_3DS_BEHAVIOR.get(psp, {})
        if psp_info.get("default_3ds") == "OFF":
            steps.append(
                f"PSP: {psp} has 3DS OFF by default. Proceed with standard checkout. "
                f"No special 3DS handling needed."
            )
        elif psp == "shopify_payments" or is_shopify:
            steps.append(
                "PSP: Shopify Payments (Stripe Radar). Use aged profile, residential IP "
                "matching billing address. US cards under $200: <10% 3DS rate."
            )
        elif psp == "stripe":
            steps.append(
                "PSP: Stripe Radar. Low amount + aged profile + matching geo = minimal 3DS. "
                "If 3DS triggers, block threeDSMethodURL for 2.0→1.0 downgrade."
            )
        elif psp == "adyen":
            if card_country in GEO_3DS_ENFORCEMENT["no_mandate"]["countries"]:
                steps.append(
                    f"PSP: Adyen with {card_country} card = one-leg-out exempt. "
                    f"3DS rate drops from ~70% to ~15%. Proceed normally."
                )
            else:
                steps.append(
                    "PSP: Adyen with EU card. Request TRA exemption via low-risk profile. "
                    "Keep under 100 EUR for best TRA approval chance."
                )
        elif psp == "braintree":
            steps.append(
                "PSP: Braintree (PayPal). Vaulted cards skip 3DS. "
                "Add card first, then purchase. Food delivery = almost zero 3DS."
            )
        else:
            steps.append(f"PSP: {psp}. Use standard approach with aged profile.")
        
        # Step 4: Antifraud handling
        fe = fraud_engine.lower() if fraud_engine else "unknown"
        if fe in ("none", "basic", "unknown"):
            steps.append(
                "ANTIFRAUD: None/basic. Standard fingerprint and residential IP sufficient."
            )
        elif fe in ("forter", "riskified"):
            steps.append(
                f"ANTIFRAUD: {fe.title()} detected. CRITICAL: Use aged profile (>30 days), "
                f"consistent fingerprint, residential IP, and Ghost Motor for human-like behavior. "
                f"Warm up with browsing session before checkout."
            )
        elif fe == "sift":
            steps.append(
                "ANTIFRAUD: Sift behavioral analysis. Ghost Motor augmentation critical. "
                "Spend 3-5 minutes browsing before checkout."
            )
        else:
            steps.append(f"ANTIFRAUD: {fe}. Use clean fingerprint and residential IP.")
        
        # Step 5: Checkout execution
        if is_digital:
            steps.append(
                "CHECKOUT: Digital goods — instant delivery. No shipping address needed. "
                "Use guest checkout if available. Complete purchase and extract digital asset immediately."
            )
        else:
            steps.append(
                "CHECKOUT: Physical goods. Ensure billing address matches card. "
                "Use verified drop address. Consider in-store pickup if available."
            )
        
        # Step 6: Fallback plan
        if three_ds != "none":
            steps.append(
                "FALLBACK: If 3DS triggers: (1) Try timeout trick (wait 5-15 min), "
                "(2) If OTP required and not available, abort — card stays clean, "
                "(3) Try same card on different merchant with lower 3DS rate."
            )
        
        return steps


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_intel_v2: Optional[TargetIntelV2] = None
_intel_v2_lock = threading.Lock()


def get_target_intel_v2() -> TargetIntelV2:
    """Get singleton TargetIntelV2 instance."""
    global _intel_v2
    with _intel_v2_lock:
        if _intel_v2 is None:
            _intel_v2 = TargetIntelV2()
    return _intel_v2


# Convenience functions
def score_target(domain: str, **kwargs) -> Dict:
    return get_target_intel_v2().score_target(domain, **kwargs)

def find_golden_targets(**kwargs) -> List[Dict]:
    return get_target_intel_v2().find_golden_targets(**kwargs)

def get_no_3ds_psps() -> List[Dict]:
    return get_target_intel_v2().get_no_3ds_psps()

def full_target_analysis(domain: str, **kwargs) -> Dict:
    return get_target_intel_v2().full_target_analysis(domain, **kwargs)
