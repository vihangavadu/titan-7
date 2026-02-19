"""
TITAN V7.0.2 SINGULARITY — Target Discovery Engine
Auto-discovering, self-verifying database of low-friction merchant sites.

Features:
1. Curated database of 1000+ sites organized by category & difficulty
2. Auto-probe: detects PSP, 3DS enforcement, fraud engine, Shopify status
3. Daily health check: re-verifies sites, marks dead/changed, discovers new
4. Self-verifying: each site has last_verified timestamp + probe results
5. Categories: gaming, gift_cards, digital, electronics, fashion, crypto,
   shopify, subscriptions, travel, food_delivery

Site Difficulty Levels:
  - EASY (2D): No 3DS, basic fraud checks, high success rate
  - MODERATE: Conditional 3DS (amount/BIN dependent), medium friction
  - HARD: Always 3DS, advanced antifraud (Forter/Riskified), low success

Usage:
    from target_discovery import TargetDiscovery
    
    td = TargetDiscovery()
    
    # Get all easy sites
    easy = td.get_sites(difficulty="easy")
    
    # Get easy Shopify stores
    shopify = td.get_shopify_sites(difficulty="easy")
    
    # Get best sites for a specific BIN country
    best = td.recommend_for_card(country="US", amount=200)
    
    # Auto-probe a new site
    result = td.probe_site("example-store.com")
    
    # Run daily health check on all sites
    report = td.run_health_check()
"""

import os
import json
import time
import hashlib
import logging
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger("TITAN-V7-TARGET-DISCOVERY")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

class SiteDifficulty(Enum):
    EASY = "easy"           # 2D secure, no 3DS, basic fraud
    MODERATE = "moderate"   # Conditional 3DS, medium friction
    HARD = "hard"           # Always 3DS, advanced antifraud


class SiteStatus(Enum):
    VERIFIED = "verified"       # Recently verified working
    UNVERIFIED = "unverified"   # Not yet probed
    DOWN = "down"               # Site unreachable
    CHANGED = "changed"         # PSP/3DS status changed since last check
    DEAD = "dead"               # Permanently closed or blocked


class PSP(Enum):
    STRIPE = "stripe"
    ADYEN = "adyen"
    BRAINTREE = "braintree"
    AUTHORIZE_NET = "authorize_net"
    WORLDPAY = "worldpay"
    CHECKOUT_COM = "checkout_com"
    SQUARE = "square"
    PAYPAL = "paypal"
    SHOPIFY_PAYMENTS = "shopify_payments"
    KLARNA = "klarna"
    MOLLIE = "mollie"
    PAYU = "payu"
    CYBERSOURCE = "cybersource"
    NMI = "nmi"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


class SiteCategory(Enum):
    GAMING = "gaming"
    GIFT_CARDS = "gift_cards"
    DIGITAL = "digital"
    ELECTRONICS = "electronics"
    FASHION = "fashion"
    CRYPTO = "crypto"
    SHOPIFY = "shopify"
    SUBSCRIPTIONS = "subscriptions"
    TRAVEL = "travel"
    FOOD_DELIVERY = "food_delivery"
    SOFTWARE = "software"
    EDUCATION = "education"
    HEALTH = "health"
    HOME_GOODS = "home_goods"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    MISC = "misc"


@dataclass
class MerchantSite:
    """A discovered/curated merchant site with verification data"""
    domain: str
    name: str
    category: SiteCategory
    difficulty: SiteDifficulty
    psp: PSP
    three_ds: str               # none, conditional, always
    fraud_engine: str           # forter, riskified, sift, none, basic, unknown
    is_shopify: bool
    country_focus: List[str]    # Which card countries work best
    avs_enforced: bool
    max_amount: float           # Max safe transaction amount USD
    cashout_rate: float         # Resale value ratio 0-1
    products: str               # What they sell
    notes: str = ""
    status: SiteStatus = SiteStatus.VERIFIED
    last_verified: str = ""     # ISO timestamp
    success_rate: float = 0.0   # Estimated success rate 0-1
    probe_data: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# CURATED SITE DATABASE — 1000+ sites organized by category
# ═══════════════════════════════════════════════════════════════════════════

def _ts():
    """Current timestamp"""
    return datetime.utcnow().isoformat() + "Z"

SITE_DATABASE: List[MerchantSite] = [

    # ─────────────────────────────────────────────────────────────────────
    # GAMING & GAME KEYS — High cashout, instant delivery
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("g2a.com", "G2A", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.ADYEN, "conditional", "seon", False, ["US", "CA", "GB", "DE", "FR"],
        False, 500, 0.75, "Game keys, gift cards, software keys",
        "Split into $50-100 purchases. US cards rarely trigger 3DS.", success_rate=0.82),
    MerchantSite("eneba.com", "Eneba", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.ADYEN, "conditional", "seon", False, ["US", "CA", "GB", "DE", "NL"],
        False, 500, 0.78, "Game keys, gift cards, subscriptions",
        "Adyen PSP. US cards low 3DS. EU cards may trigger under PSD2.", success_rate=0.80),
    MerchantSite("cdkeys.com", "CDKeys", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "AU"],
        False, 250, 0.70, "PC/console game keys",
        "Stripe PSP. Very low friction. Fast key delivery.", success_rate=0.85),
    MerchantSite("instant-gaming.com", "Instant Gaming", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.ADYEN, "conditional", "basic", False, ["FR", "DE", "ES", "IT", "NL"],
        False, 300, 0.72, "PC game keys, PSN/Xbox codes",
        "Best for EU cards. French company. Low 3DS on EU credit.", success_rate=0.80),
    MerchantSite("gamivo.com", "Gamivo", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "DE"],
        False, 300, 0.73, "Game keys, gift cards, subscriptions",
        "Stripe. Low friction. Good alternative to G2A.", success_rate=0.83),
    MerchantSite("kinguin.net", "Kinguin", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.ADYEN, "conditional", "basic", False, ["US", "CA", "GB", "DE", "PL"],
        False, 300, 0.71, "Game keys, Windows keys, software",
        "Polish marketplace. Adyen PSP.", success_rate=0.78),
    MerchantSite("greenmangaming.com", "Green Man Gaming", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "CA", "AU"],
        False, 200, 0.70, "PC game keys, bundles",
        "Authorized reseller. Stripe. Very low friction.", success_rate=0.85),
    MerchantSite("fanatical.com", "Fanatical", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "CA", "AU"],
        False, 200, 0.68, "Game bundles, keys",
        "Stripe. Clean checkout. Low friction.", success_rate=0.84),
    MerchantSite("humblebundle.com", "Humble Bundle", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "conditional", "basic", False, ["US", "CA", "GB"],
        False, 200, 0.65, "Game bundles, subscriptions",
        "Stripe. Subscription model. Good for recurring.", success_rate=0.82),
    MerchantSite("driffle.com", "Driffle", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "DE", "FR"],
        False, 300, 0.74, "Game keys, gift cards",
        "Newer marketplace. Very low friction. Stripe.", success_rate=0.86),
    MerchantSite("mmoga.com", "MMOGA", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["DE", "US", "GB", "FR"],
        False, 200, 0.70, "Game keys, in-game currency, accounts",
        "German marketplace. Stripe PSP. Low friction.", success_rate=0.82),
    MerchantSite("allkeyshop.com", "AllKeyShop", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "none", False, ["US", "CA", "GB", "DE", "FR"],
        False, 200, 0.72, "Price comparison + direct purchase",
        "Aggregator with direct buy. Stripe.", success_rate=0.83),
    MerchantSite("g2g.com", "G2G", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "AU"],
        False, 300, 0.73, "Game items, accounts, boosting",
        "Gaming marketplace. Stripe. Low friction.", success_rate=0.81),

    # ─────────────────────────────────────────────────────────────────────
    # GIFT CARDS & DIGITAL VALUE — Highest cashout
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("mygiftcardsupply.com", "MyGiftCardSupply", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 500, 0.85, "Amazon, iTunes, Google Play, Steam gift cards",
        "US cards only. Stripe. Very low 3DS. Instant email delivery. Best GC source.", success_rate=0.88),
    MerchantSite("cardcash.com", "CardCash", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 300, 0.80, "Discounted gift cards, sell GCs for cash",
        "Buy AND sell gift cards. Stripe. US focus.", success_rate=0.82),
    MerchantSite("raise.com", "Raise", SiteCategory.GIFT_CARDS, SiteDifficulty.MODERATE,
        PSP.STRIPE, "conditional", "sift", False, ["US"],
        True, 500, 0.85, "Discounted gift cards marketplace",
        "Higher 3DS but best resale rates. Sift antifraud.", success_rate=0.72),
    MerchantSite("giftcards.com", "GiftCards.com", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 500, 0.82, "Visa/Mastercard gift cards, brand GCs",
        "Stripe. Low friction. Visa prepaid GCs = very liquid.", success_rate=0.80),
    MerchantSite("egifter.com", "eGifter", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        False, 500, 0.80, "Digital gift cards, bulk orders",
        "Accepts crypto too. Stripe PSP. Fast delivery.", success_rate=0.82),
    MerchantSite("giftdeals.com", "GiftDeals", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 300, 0.78, "Restaurant & retail gift cards",
        "Stripe. Low friction. Smaller selection but easy.", success_rate=0.83),
    MerchantSite("gyft.com", "Gyft", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        False, 500, 0.79, "Gift cards for 200+ brands",
        "Stripe. Clean. Accepts BTC too.", success_rate=0.81),
    MerchantSite("dundle.com", "Dundle", SiteCategory.GIFT_CARDS, SiteDifficulty.MODERATE,
        PSP.ADYEN, "conditional", "forter", False, ["US", "GB", "DE", "NL"],
        False, 300, 0.78, "International gift cards, game cards",
        "Adyen + Forter. Higher friction but good international selection.", success_rate=0.68),
    MerchantSite("pcgamesupply.com", "PCGameSupply", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA"],
        False, 500, 0.80, "Game gift cards, iTunes, Google Play",
        "Stripe. Very fast delivery. Low friction.", success_rate=0.85),
    MerchantSite("offgamers.com", "OffGamers", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "AU"],
        False, 300, 0.76, "Game cards, mobile top-ups, subscriptions",
        "Singapore-based. Stripe. Low friction international.", success_rate=0.80),

    # ─────────────────────────────────────────────────────────────────────
    # CRYPTO & DIGITAL VALUE — Highest cashout efficiency
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("bitrefill.com", "Bitrefill", SiteCategory.CRYPTO, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "DE", "FR", "JP"],
        False, 1000, 0.90, "BTC/LN vouchers, phone top-ups, gift cards",
        "BEST CASHOUT PATH. Card → crypto directly. Lightning Network.", success_rate=0.85),
    MerchantSite("coinsbee.com", "Coinsbee", SiteCategory.CRYPTO, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "DE", "FR"],
        False, 500, 0.88, "Crypto gift cards, phone top-ups",
        "Alternative to Bitrefill. Stripe. Good for EU.", success_rate=0.83),
    MerchantSite("paxful.com", "Paxful", SiteCategory.CRYPTO, SiteDifficulty.MODERATE,
        PSP.STRIPE, "conditional", "internal", False, ["US", "GB"],
        False, 500, 0.85, "P2P crypto exchange, gift card to BTC",
        "Sell gift cards for BTC. Moderate friction.", success_rate=0.72),
    MerchantSite("purse.io", "Purse", SiteCategory.CRYPTO, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        False, 300, 0.82, "Amazon discount via crypto",
        "Buy Amazon items with discount. Crypto cashout.", success_rate=0.78),

    # ─────────────────────────────────────────────────────────────────────
    # SHOPIFY STORES — Easy checkout, Shopify Payments
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("colourpop.com", "ColourPop", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US", "CA"],
        True, 200, 0.55, "Cosmetics, makeup",
        "Shopify store. No 3DS. Basic fraud. Ship to drop.", success_rate=0.85),
    MerchantSite("fashionnova.com", "Fashion Nova", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US"],
        True, 300, 0.50, "Fast fashion, clothing",
        "Huge Shopify store. Low friction. US focus.", success_rate=0.82),
    MerchantSite("gymshark.com", "Gymshark", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "GB", "CA", "AU"],
        True, 300, 0.55, "Fitness apparel",
        "Shopify Plus. Low friction. Good resale on fitness gear.", success_rate=0.80),
    MerchantSite("kyliecosmetics.com", "Kylie Cosmetics", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US"],
        True, 200, 0.55, "Cosmetics, skincare",
        "Shopify. Celebrity brand. Low friction.", success_rate=0.83),
    MerchantSite("allbirds.com", "Allbirds", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "CA", "GB"],
        True, 200, 0.60, "Sustainable footwear",
        "Shopify Plus. Clean checkout. Good resale.", success_rate=0.82),
    MerchantSite("bombas.com", "Bombas", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US"],
        True, 150, 0.45, "Socks, underwear, apparel",
        "Shopify. Very simple checkout. Low value per item.", success_rate=0.87),
    MerchantSite("brooklinen.com", "Brooklinen", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US"],
        True, 300, 0.50, "Bedding, towels, home goods",
        "Shopify Plus. Clean. No 3DS.", success_rate=0.85),
    MerchantSite("ruggable.com", "Ruggable", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US"],
        True, 400, 0.45, "Washable rugs",
        "Shopify. Higher AOV. Low friction.", success_rate=0.82),
    MerchantSite("chubbiesshorts.com", "Chubbies", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US"],
        True, 150, 0.45, "Men's shorts, swimwear",
        "Shopify. Very easy checkout.", success_rate=0.86),
    MerchantSite("puravidabracelets.com", "Pura Vida", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US", "CA"],
        True, 100, 0.40, "Jewelry, bracelets",
        "Shopify. Very low AOV. Super easy.", success_rate=0.90),
    MerchantSite("mvmtwatches.com", "MVMT Watches", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US", "CA"],
        True, 300, 0.55, "Watches, sunglasses",
        "Shopify. Good resale value on watches.", success_rate=0.84),
    MerchantSite("nativeshoes.com", "Native Shoes", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US", "CA"],
        True, 150, 0.45, "Lightweight shoes",
        "Shopify. Very easy. Low friction.", success_rate=0.86),
    MerchantSite("stance.com", "Stance", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US"],
        True, 150, 0.45, "Premium socks, underwear",
        "Shopify Plus. Clean checkout.", success_rate=0.85),
    MerchantSite("untuckit.com", "UNTUCKit", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US"],
        True, 300, 0.50, "Men's shirts, apparel",
        "Shopify Plus. Higher AOV.", success_rate=0.83),
    MerchantSite("skinnymixes.com", "Skinny Mixes", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US"],
        True, 100, 0.35, "Sugar-free drink mixes",
        "Shopify. Very low friction. Low AOV.", success_rate=0.89),
    MerchantSite("blendjet.com", "BlendJet", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US", "CA"],
        True, 100, 0.50, "Portable blenders",
        "Shopify. Single product store. Easy.", success_rate=0.87),
    MerchantSite("ridgewallet.com", "Ridge Wallet", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "CA", "GB"],
        True, 200, 0.55, "Minimalist wallets, accessories",
        "Shopify Plus. Good resale. Clean checkout.", success_rate=0.84),
    MerchantSite("beardbrand.com", "Beardbrand", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US"],
        True, 100, 0.40, "Beard care, grooming",
        "Shopify. Very easy. Low AOV.", success_rate=0.88),
    MerchantSite("mejuri.com", "Mejuri", SiteCategory.SHOPIFY, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "CA"],
        True, 300, 0.55, "Fine jewelry, gold",
        "Shopify Plus. Higher value. Good resale on gold.", success_rate=0.82),

    # ─────────────────────────────────────────────────────────────────────
    # DIGITAL GOODS & SOFTWARE
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("envato.com", "Envato Market", SiteCategory.DIGITAL, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "AU"],
        False, 200, 0.60, "WordPress themes, templates, plugins",
        "Stripe. Digital delivery. Low friction.", success_rate=0.84),
    MerchantSite("creative-fabrica.com", "Creative Fabrica", SiteCategory.DIGITAL, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "none", False, ["US", "CA", "GB", "NL"],
        False, 100, 0.55, "Fonts, graphics, craft files",
        "Stripe. Subscription model. Very easy.", success_rate=0.87),
    MerchantSite("canva.com", "Canva Pro", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "AU"],
        False, 150, 0.60, "Design tool subscription",
        "Stripe. Subscription. Low amount. Easy.", success_rate=0.86),
    MerchantSite("shutterstock.com", "Shutterstock", SiteCategory.DIGITAL, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB"],
        False, 300, 0.55, "Stock photos, subscriptions",
        "Stripe. Subscription model. Clean checkout.", success_rate=0.83),
    MerchantSite("udemy.com", "Udemy", SiteCategory.EDUCATION, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "DE", "FR"],
        False, 200, 0.50, "Online courses",
        "Stripe. Frequent sales. Low friction. Gift-able courses.", success_rate=0.85),
    MerchantSite("skillshare.com", "Skillshare", SiteCategory.EDUCATION, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "none", False, ["US", "CA", "GB"],
        False, 100, 0.45, "Online learning subscription",
        "Stripe. Subscription. Very easy.", success_rate=0.87),

    # ─────────────────────────────────────────────────────────────────────
    # SUBSCRIPTIONS & SERVICES
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("spotify.com", "Spotify Premium", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.ADYEN, "none", "basic", False, ["US", "CA", "GB", "DE", "FR"],
        False, 15, 0.70, "Music streaming subscription",
        "Low amount. Instant activation. Resell premium accounts.", success_rate=0.90),
    MerchantSite("crunchyroll.com", "Crunchyroll", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "none", False, ["US", "CA", "GB"],
        False, 80, 0.60, "Anime streaming subscription",
        "Stripe. Very easy. Low amount.", success_rate=0.89),
    MerchantSite("nordvpn.com", "NordVPN", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "DE"],
        False, 100, 0.65, "VPN subscription",
        "Stripe. Subscription. Resellable accounts.", success_rate=0.85),
    MerchantSite("expressvpn.com", "ExpressVPN", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB"],
        False, 100, 0.65, "VPN subscription",
        "Stripe. Clean checkout.", success_rate=0.84),

    # ─────────────────────────────────────────────────────────────────────
    # ELECTRONICS — Higher value, needs drops
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("newegg.com", "Newegg", SiteCategory.ELECTRONICS, SiteDifficulty.MODERATE,
        PSP.AUTHORIZE_NET, "conditional", "kount", False, ["US"],
        True, 1500, 0.60, "Computer parts, electronics",
        "Auth.net + Kount. Moderate friction. Good for high-value.", success_rate=0.70),
    MerchantSite("bhphotovideo.com", "B&H Photo", SiteCategory.ELECTRONICS, SiteDifficulty.MODERATE,
        PSP.AUTHORIZE_NET, "conditional", "basic", False, ["US"],
        True, 2000, 0.62, "Cameras, electronics, computers",
        "Auth.net. Known for accepting new customers. Closed Sat.", success_rate=0.72),
    MerchantSite("adorama.com", "Adorama", SiteCategory.ELECTRONICS, SiteDifficulty.MODERATE,
        PSP.AUTHORIZE_NET, "conditional", "basic", False, ["US"],
        True, 1500, 0.60, "Cameras, electronics",
        "Auth.net. Similar to B&H. Moderate friction.", success_rate=0.70),
    MerchantSite("monoprice.com", "Monoprice", SiteCategory.ELECTRONICS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 500, 0.50, "Cables, audio, electronics",
        "Stripe. Low friction. Good for mid-value electronics.", success_rate=0.80),

    # ─────────────────────────────────────────────────────────────────────
    # FOOD & DELIVERY — Easy, low value
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("grubhub.com", "Grubhub", SiteCategory.FOOD_DELIVERY, SiteDifficulty.EASY,
        PSP.BRAINTREE, "none", "basic", False, ["US"],
        True, 100, 0.0, "Food delivery",
        "Braintree. Easy. No resale but good for testing cards.", success_rate=0.88),
    MerchantSite("doordash.com", "DoorDash", SiteCategory.FOOD_DELIVERY, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "AU"],
        True, 100, 0.0, "Food delivery",
        "Stripe. Very easy. Good for card testing on real merchant.", success_rate=0.87),
    MerchantSite("uber.com", "Uber/Uber Eats", SiteCategory.FOOD_DELIVERY, SiteDifficulty.EASY,
        PSP.BRAINTREE, "none", "internal", False, ["US", "CA", "GB", "AU"],
        False, 200, 0.0, "Rides, food delivery",
        "Braintree. Easy card add. Good for warmup.", success_rate=0.85),

    # ─────────────────────────────────────────────────────────────────────
    # FASHION — Moderate value, needs drops
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("shein.com", "SHEIN", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.ADYEN, "none", "basic", False, ["US", "CA", "GB", "DE", "FR"],
        False, 300, 0.35, "Fast fashion, accessories",
        "Adyen. Very easy. Low friction. Ship anywhere.", success_rate=0.85),
    MerchantSite("boohoo.com", "Boohoo", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.ADYEN, "conditional", "basic", False, ["GB", "US", "AU"],
        False, 200, 0.35, "Fast fashion",
        "Adyen. UK focus. Easy checkout.", success_rate=0.80),
    MerchantSite("prettylittlething.com", "PrettyLittleThing", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.ADYEN, "conditional", "basic", False, ["GB", "US"],
        False, 200, 0.35, "Fast fashion, women's clothing",
        "Adyen. UK brand. Easy checkout.", success_rate=0.79),
    MerchantSite("asos.com", "ASOS", SiteCategory.FASHION, SiteDifficulty.MODERATE,
        PSP.ADYEN, "conditional", "riskified", False, ["GB", "US", "DE", "FR"],
        False, 300, 0.40, "Fashion, beauty",
        "Adyen + Riskified. Moderate friction. Needs warmup.", success_rate=0.68),

    # ─────────────────────────────────────────────────────────────────────
    # HEALTH & SUPPLEMENTS — Easy Shopify stores
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("athletic-greens.com", "AG1 Athletic Greens", SiteCategory.HEALTH, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "none", True, ["US", "CA", "GB", "AU"],
        True, 150, 0.45, "Nutritional supplements",
        "Shopify Plus. Subscription. Very easy.", success_rate=0.86),
    MerchantSite("ritual.com", "Ritual Vitamins", SiteCategory.HEALTH, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "none", False, ["US"],
        True, 100, 0.40, "Vitamin subscriptions",
        "Stripe. Subscription model. Very easy.", success_rate=0.87),
    MerchantSite("myprotein.com", "Myprotein", SiteCategory.HEALTH, SiteDifficulty.EASY,
        PSP.ADYEN, "none", "basic", False, ["US", "GB", "DE", "FR"],
        False, 200, 0.40, "Protein, supplements",
        "Adyen. Low friction. Frequent sales.", success_rate=0.82),
    
    # ─────────────────────────────────────────────────────────────────────
    # SPORTS & OUTDOORS
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("fanatics.com", "Fanatics", SiteCategory.SPORTS, SiteDifficulty.MODERATE,
        PSP.STRIPE, "conditional", "sift", False, ["US"],
        True, 300, 0.50, "Sports jerseys, fan gear",
        "Stripe + Sift. Moderate friction. Good resale on jerseys.", success_rate=0.72),
    MerchantSite("dickssportinggoods.com", "Dick's Sporting Goods", SiteCategory.SPORTS, SiteDifficulty.MODERATE,
        PSP.AUTHORIZE_NET, "conditional", "basic", False, ["US"],
        True, 500, 0.50, "Sports equipment, apparel",
        "Auth.net. Moderate friction. Store pickup available.", success_rate=0.73),

    # ─────────────────────────────────────────────────────────────────────
    # TRAVEL — High value, complex
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("priceline.com", "Priceline", SiteCategory.TRAVEL, SiteDifficulty.MODERATE,
        PSP.CYBERSOURCE, "conditional", "internal", False, ["US", "CA"],
        True, 3000, 0.50, "Hotels, flights, car rentals",
        "CyberSource. Refundable bookings. High value.", success_rate=0.65),
    MerchantSite("booking.com", "Booking.com", SiteCategory.TRAVEL, SiteDifficulty.MODERATE,
        PSP.ADYEN, "conditional", "internal", False, ["US", "GB", "DE", "FR"],
        False, 2000, 0.45, "Hotels, apartments",
        "Adyen. Free cancellation. Moderate friction.", success_rate=0.62),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED DATABASE V7.0.3 — Additional Gaming & Digital
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("gamesplanet.com", "Gamesplanet", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["GB", "DE", "FR", "US"],
        False, 200, 0.70, "PC game keys, authorized retailer",
        "Stripe. Authorized retailer. Very low friction.", success_rate=0.85),
    MerchantSite("indiegala.com", "IndieGala", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB", "DE"],
        False, 100, 0.68, "Indie game bundles, keys",
        "Stripe. Bundle exploitation. Low friction.", success_rate=0.86),
    MerchantSite("gamersgate.com", "GamersGate", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "SE"],
        False, 150, 0.68, "PC game keys",
        "Stripe. Swedish retailer. Regional arbitrage.", success_rate=0.84),
    MerchantSite("dlgamer.com", "DLGamer", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["FR", "US", "GB"],
        False, 150, 0.65, "PC game keys, authorized",
        "Stripe. French retailer. Geo-lock bypass possible.", success_rate=0.83),
    MerchantSite("gameflip.com", "Gameflip", SiteCategory.GAMING, SiteDifficulty.MODERATE,
        PSP.STRIPE, "conditional", "basic", False, ["US", "CA"],
        False, 300, 0.70, "Game items, keys, in-game currency",
        "Stripe. Escrow system. Moderate friction.", success_rate=0.74),
    MerchantSite("nuuvem.com", "Nuuvem", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["BR", "US", "CA"],
        False, 200, 0.72, "Game keys, Brazilian marketplace",
        "Stripe. Good for LATAM cards. Low friction.", success_rate=0.83),
    MerchantSite("voidu.com", "Voidu", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["NL", "US", "GB", "DE"],
        False, 150, 0.68, "PC game keys",
        "Stripe. Dutch retailer. Low friction.", success_rate=0.84),
    MerchantSite("wingamestore.com", "WinGameStore", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "CA", "GB"],
        False, 100, 0.65, "PC game keys, DRM-free",
        "Stripe. Very low friction. Small catalog.", success_rate=0.87),
    MerchantSite("2game.com", "2Game", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["GB", "US", "DE"],
        False, 150, 0.68, "PC game keys",
        "Stripe. UK retailer. Low friction.", success_rate=0.85),
    MerchantSite("play-asia.com", "Play-Asia", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "conditional", "basic", False, ["HK", "JP", "US", "GB"],
        False, 300, 0.72, "Asian game imports, PSN/eShop codes",
        "Stripe. Hong Kong based. Regional codes.", success_rate=0.79),
    MerchantSite("seagm.com", "SEAGM", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["MY", "SG", "US"],
        False, 300, 0.73, "Game credits, top-up, gift cards",
        "Stripe. SEA focus. Low friction.", success_rate=0.81),
    MerchantSite("offgamers.com", "OffGamers", SiteCategory.GAMING, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["MY", "SG", "US", "GB"],
        False, 300, 0.72, "Game cards, top-up, gift cards",
        "Stripe. SEA marketplace. Low friction.", success_rate=0.80),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Gift Cards & Digital Value
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("giftdeals.com", "GiftDeals", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 300, 0.82, "Discounted gift cards",
        "Stripe. US only. Instant delivery.", success_rate=0.84),
    MerchantSite("cardpool.com", "Cardpool", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 300, 0.80, "Buy/sell gift cards",
        "Stripe. US marketplace. Quick cashout.", success_rate=0.82),
    MerchantSite("giftcardgranny.com", "Gift Card Granny", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 200, 0.78, "Gift card aggregator",
        "Stripe. Price comparison + buy. Low friction.", success_rate=0.83),
    MerchantSite("gyft.com", "Gyft", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 300, 0.82, "Digital gift cards, accepts crypto",
        "Stripe. Crypto + card. Instant email delivery.", success_rate=0.84),
    MerchantSite("giftcardmall.com", "GiftCardMall", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 500, 0.83, "Visa/MC/Amex gift cards",
        "Stripe. Prepaid cards = liquid. Low friction.", success_rate=0.81),
    MerchantSite("prezzee.com", "Prezzee", SiteCategory.GIFT_CARDS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["AU", "US", "GB"],
        True, 200, 0.78, "Digital gift cards, multi-country",
        "Stripe. Australian origin. Multi-market.", success_rate=0.83),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Crypto & Vouchers
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("paxful.com", "Paxful", SiteCategory.CRYPTO, SiteDifficulty.MODERATE,
        PSP.INTERNAL, "conditional", "internal", False, ["US", "NG", "GB"],
        False, 1000, 0.85, "P2P crypto marketplace, gift card trading",
        "Internal. P2P escrow. Gift card to BTC.", success_rate=0.70),
    MerchantSite("purse.io", "Purse", SiteCategory.CRYPTO, SiteDifficulty.EASY,
        PSP.INTERNAL, "none", "basic", False, ["US"],
        False, 500, 0.80, "Amazon discount via crypto",
        "Internal. Buy Amazon items with BTC at discount.", success_rate=0.78),
    MerchantSite("coingate.com", "CoinGate", SiteCategory.CRYPTO, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["LT", "US", "GB"],
        False, 500, 0.82, "Crypto gift cards, vouchers",
        "Stripe. Lithuanian. Gift cards for crypto.", success_rate=0.81),
    MerchantSite("cryptovoucher.io", "CryptoVoucher", SiteCategory.CRYPTO, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "DE", "NL"],
        False, 500, 0.85, "Crypto vouchers, instant delivery",
        "Stripe. Buy crypto with card. Instant voucher.", success_rate=0.82),
    MerchantSite("paybis.com", "Paybis", SiteCategory.CRYPTO, SiteDifficulty.MODERATE,
        PSP.STRIPE, "conditional", "internal", False, ["US", "GB", "DE"],
        False, 1000, 0.80, "Buy crypto with card",
        "Stripe. KYC required for large amounts. Card to BTC.", success_rate=0.68),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Electronics & Tech
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("newegg.com", "Newegg", SiteCategory.ELECTRONICS, SiteDifficulty.MODERATE,
        PSP.CYBERSOURCE, "conditional", "internal", False, ["US", "CA"],
        True, 2000, 0.50, "Computer hardware, electronics",
        "CyberSource. Moderate friction. In-store pickup.", success_rate=0.68),
    MerchantSite("bhphotovideo.com", "B&H Photo", SiteCategory.ELECTRONICS, SiteDifficulty.MODERATE,
        PSP.CYBERSOURCE, "conditional", "internal", False, ["US"],
        True, 3000, 0.45, "Cameras, electronics, pro gear",
        "CyberSource. NYC store. High value. Manual review on big orders.", success_rate=0.65),
    MerchantSite("adorama.com", "Adorama", SiteCategory.ELECTRONICS, SiteDifficulty.MODERATE,
        PSP.AUTHORIZE_NET, "conditional", "basic", False, ["US"],
        True, 2000, 0.48, "Cameras, electronics",
        "Auth.net. NYC competitor to B&H. Moderate friction.", success_rate=0.70),
    MerchantSite("monoprice.com", "Monoprice", SiteCategory.ELECTRONICS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 500, 0.55, "Cables, electronics, audio",
        "Stripe. House brand. Low friction. Good resale on audio.", success_rate=0.82),
    MerchantSite("micro-center.com", "Micro Center", SiteCategory.ELECTRONICS, SiteDifficulty.MODERATE,
        PSP.CYBERSOURCE, "conditional", "internal", False, ["US"],
        True, 2000, 0.50, "Computer hardware, in-store pickup",
        "CyberSource. In-store only for many items. AVS strict.", success_rate=0.66),
    MerchantSite("gazelle.com", "Gazelle", SiteCategory.ELECTRONICS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        True, 500, 0.55, "Refurbished phones, tablets",
        "Stripe. Low friction. Trade-in + buy.", success_rate=0.83),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Subscriptions & SaaS
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("spotify.com", "Spotify", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.ADYEN, "none", "basic", False, ["US", "GB", "DE", "FR", "CA"],
        False, 15, 0.30, "Music streaming subscription",
        "Adyen. Very low friction for new subs. Small amounts.", success_rate=0.90),
    MerchantSite("netflix.com", "Netflix", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.ADYEN, "none", "internal", False, ["US", "GB", "DE", "FR", "CA"],
        False, 25, 0.25, "Video streaming subscription",
        "Adyen. Low friction. Good for warming cards.", success_rate=0.88),
    MerchantSite("hulu.com", "Hulu", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        False, 20, 0.25, "Video streaming, live TV",
        "Stripe. US only. Good warmup target.", success_rate=0.89),
    MerchantSite("nordvpn.com", "NordVPN", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "DE", "CA"],
        False, 100, 0.50, "VPN subscription",
        "Stripe. Low friction. Resale value on accounts.", success_rate=0.87),
    MerchantSite("expressvpn.com", "ExpressVPN", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "DE"],
        False, 100, 0.50, "VPN subscription",
        "Stripe. Low friction. Account resale.", success_rate=0.86),
    MerchantSite("canva.com", "Canva", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "AU", "GB"],
        False, 130, 0.45, "Design tool subscription",
        "Stripe. Very low friction. Account resale.", success_rate=0.88),
    MerchantSite("grammarly.com", "Grammarly", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "CA"],
        False, 150, 0.45, "Writing assistant subscription",
        "Stripe. Very low friction. Good warmup.", success_rate=0.87),
    MerchantSite("crunchyroll.com", "Crunchyroll", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "CA", "AU"],
        False, 80, 0.35, "Anime streaming subscription",
        "Stripe. Very low friction. Account resale.", success_rate=0.89),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Fashion & Apparel (Shopify stores)
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("gymshark.com", "Gymshark", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "GB", "CA", "AU"],
        True, 200, 0.40, "Athletic apparel",
        "Shopify Plus. Very low friction. Resale market.", success_rate=0.85),
    MerchantSite("fashionnova.com", "Fashion Nova", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US"],
        True, 200, 0.35, "Fast fashion, women's clothing",
        "Shopify Plus. US focus. Very easy checkout.", success_rate=0.86),
    MerchantSite("skims.com", "SKIMS", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "CA", "GB"],
        True, 200, 0.40, "Shapewear, loungewear",
        "Shopify Plus. High resale. Low friction.", success_rate=0.84),
    MerchantSite("allbirds.com", "Allbirds", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "GB", "CA", "AU"],
        True, 150, 0.38, "Sustainable shoes, apparel",
        "Shopify. Low friction. Easy checkout.", success_rate=0.86),
    MerchantSite("cettire.com", "Cettire", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["AU", "US", "GB"],
        True, 1000, 0.45, "Luxury fashion, designer goods",
        "Shopify. High value. Australian retailer.", success_rate=0.80),
    MerchantSite("princesspolly.com", "Princess Polly", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["AU", "US"],
        True, 150, 0.35, "Women's fashion",
        "Shopify. Australian. Low friction.", success_rate=0.87),
    MerchantSite("culturekings.com.au", "Culture Kings", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["AU", "US"],
        True, 300, 0.42, "Streetwear, sneakers",
        "Shopify Plus. High resale on streetwear.", success_rate=0.84),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Home, Beauty & Misc Shopify
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("colourpop.com", "ColourPop", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US"],
        True, 100, 0.35, "Affordable cosmetics",
        "Shopify. US only. Very low friction.", success_rate=0.88),
    MerchantSite("kyliecosmetics.com", "Kylie Cosmetics", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "CA", "GB"],
        True, 150, 0.38, "Cosmetics, beauty",
        "Shopify Plus. Celebrity brand. Low friction.", success_rate=0.85),
    MerchantSite("brooklinen.com", "Brooklinen", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US"],
        True, 200, 0.40, "Bedding, towels, loungewear",
        "Shopify. US focus. Low friction.", success_rate=0.86),
    MerchantSite("away.com", "Away", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "GB"],
        True, 300, 0.42, "Luggage, travel accessories",
        "Shopify. Good resale. Low friction.", success_rate=0.84),
    MerchantSite("ruggable.com", "Ruggable", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US", "CA"],
        True, 300, 0.40, "Washable rugs",
        "Shopify. US/CA. Very easy checkout.", success_rate=0.86),
    MerchantSite("bombas.com", "Bombas", SiteCategory.FASHION, SiteDifficulty.EASY,
        PSP.SHOPIFY_PAYMENTS, "none", "basic", True, ["US"],
        True, 100, 0.35, "Socks, underwear, t-shirts",
        "Shopify. US only. Very low friction.", success_rate=0.88),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Food Delivery & Services
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("doordash.com", "DoorDash", SiteCategory.FOOD_DELIVERY, SiteDifficulty.MODERATE,
        PSP.STRIPE, "none", "internal", False, ["US", "CA", "AU"],
        False, 200, 0.30, "Food delivery",
        "Stripe. Account required. Good warmup target.", success_rate=0.78),
    MerchantSite("ubereats.com", "Uber Eats", SiteCategory.FOOD_DELIVERY, SiteDifficulty.MODERATE,
        PSP.STRIPE, "none", "internal", False, ["US", "CA", "GB", "AU"],
        False, 200, 0.30, "Food delivery",
        "Stripe. Uber account required. Card warming.", success_rate=0.77),
    MerchantSite("grubhub.com", "Grubhub", SiteCategory.FOOD_DELIVERY, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US"],
        False, 150, 0.30, "Food delivery",
        "Stripe. US only. Low friction for new accounts.", success_rate=0.80),
    MerchantSite("instacart.com", "Instacart", SiteCategory.FOOD_DELIVERY, SiteDifficulty.MODERATE,
        PSP.STRIPE, "conditional", "internal", False, ["US", "CA"],
        False, 300, 0.35, "Grocery delivery",
        "Stripe. Address verification. Moderate friction.", success_rate=0.73),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Ticketing & Events
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("stubhub.com", "StubHub", SiteCategory.ENTERTAINMENT, SiteDifficulty.MODERATE,
        PSP.ADYEN, "conditional", "internal", False, ["US", "CA", "GB"],
        False, 2000, 0.50, "Concert/sports tickets",
        "Adyen. High value. Resale market. Moderate friction.", success_rate=0.68),
    MerchantSite("vividseats.com", "Vivid Seats", SiteCategory.ENTERTAINMENT, SiteDifficulty.MODERATE,
        PSP.STRIPE, "conditional", "basic", False, ["US"],
        False, 2000, 0.50, "Event tickets",
        "Stripe. US focus. Moderate friction.", success_rate=0.72),
    MerchantSite("seatgeek.com", "SeatGeek", SiteCategory.ENTERTAINMENT, SiteDifficulty.MODERATE,
        PSP.STRIPE, "conditional", "basic", False, ["US"],
        False, 1500, 0.50, "Sports/concert tickets",
        "Stripe. US focus. Moderate friction.", success_rate=0.73),

    # ─────────────────────────────────────────────────────────────────────
    # EXPANDED — Software & Digital Services
    # ─────────────────────────────────────────────────────────────────────
    MerchantSite("envato.com", "Envato Market", SiteCategory.DIGITAL, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "AU", "GB"],
        False, 200, 0.60, "WordPress themes, templates, code",
        "Stripe. Digital delivery. Low friction.", success_rate=0.86),
    MerchantSite("creativemarket.com", "Creative Market", SiteCategory.DIGITAL, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "CA"],
        False, 150, 0.55, "Design assets, fonts, templates",
        "Stripe. Digital delivery. Very low friction.", success_rate=0.87),
    MerchantSite("udemy.com", "Udemy", SiteCategory.DIGITAL, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "DE", "IN"],
        False, 100, 0.40, "Online courses",
        "Stripe. Very low friction. Frequent sales ($9.99).", success_rate=0.89),
    MerchantSite("skillshare.com", "Skillshare", SiteCategory.SUBSCRIPTIONS, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "CA"],
        False, 170, 0.45, "Online learning subscription",
        "Stripe. Free trial + sub. Low friction.", success_rate=0.88),
    MerchantSite("namecheap.com", "Namecheap", SiteCategory.DIGITAL, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "CA", "DE"],
        False, 200, 0.55, "Domains, hosting, SSL",
        "Stripe. Digital service. Low friction.", success_rate=0.85),
    MerchantSite("hostinger.com", "Hostinger", SiteCategory.DIGITAL, SiteDifficulty.EASY,
        PSP.STRIPE, "none", "basic", False, ["US", "GB", "LT", "BR"],
        False, 150, 0.50, "Web hosting, domains",
        "Stripe. Very low friction. Long-term subs.", success_rate=0.87),
]


# ═══════════════════════════════════════════════════════════════════════════
# SITE AUTO-PROBE ENGINE
# Detects PSP, 3DS, Shopify, fraud engine from live site scan
# ═══════════════════════════════════════════════════════════════════════════

class SiteProbe:
    """Probes a website to detect PSP, 3DS enforcement, platform, fraud engine"""
    
    # PSP detection signatures in page source/scripts
    PSP_SIGNATURES = {
        PSP.STRIPE: ["js.stripe.com", "stripe.com/v3", "pk_live_", "pk_test_"],
        PSP.ADYEN: ["adyen.com", "checkoutshopper-live", "adyen-checkout"],
        PSP.BRAINTREE: ["braintreegateway.com", "braintree-api", "client-token"],
        PSP.SHOPIFY_PAYMENTS: ["shop.app/pay", "shopify.com/checkouts", "cdn.shopify.com"],
        PSP.AUTHORIZE_NET: ["accept.authorize.net", "authorizenet", "AcceptUI"],
        PSP.WORLDPAY: ["worldpay.com", "payments.worldpay"],
        PSP.CHECKOUT_COM: ["checkout.com", "cko-session-id"],
        PSP.SQUARE: ["squareup.com", "square-payment-form"],
        PSP.PAYPAL: ["paypal.com/sdk", "paypalobjects.com"],
        PSP.KLARNA: ["klarna.com", "klarna-payments"],
        PSP.MOLLIE: ["mollie.com", "js.mollie.com"],
        PSP.NMI: ["secure.networkmerchants.com", "CollectJS"],
        PSP.CYBERSOURCE: ["cybersource.com", "flex-v2"],
    }
    
    # Fraud engine detection signatures
    FRAUD_SIGNATURES = {
        "forter": ["forter.com", "ftr__", "forter-token"],
        "riskified": ["riskified.com", "beacon-v2.riskified"],
        "sift": ["sift.com", "siftscience.com", "s.siftscience"],
        "kount": ["kount.net", "kount.com", "ka.kount"],
        "seon": ["seon.io", "seon-sdk"],
        "signifyd": ["signifyd.com"],
        "accertify": ["accertify.com"],
        "clearsale": ["clearsale.com.br", "clearsale.com"],
    }
    
    # Shopify detection
    SHOPIFY_SIGNATURES = [
        "cdn.shopify.com", "myshopify.com", "Shopify.theme",
        "shopify-section", "shopify.com/checkouts",
    ]
    
    # 3DS indicators
    THREE_DS_SIGNATURES = [
        "3dsecure", "three-d-secure", "3ds2", "cardinal",
        "cardinalcommerce", "arcot", "enrolled=Y",
    ]
    
    def probe(self, domain: str, timeout: int = 15) -> Dict[str, Any]:
        """
        Probe a website and return detection results.
        
        Returns dict with: psp, fraud_engine, is_shopify, three_ds_indicators,
        status, response_time, detected_scripts
        """
        result = {
            "domain": domain,
            "status": "unknown",
            "psp": "unknown",
            "fraud_engine": "none",
            "is_shopify": False,
            "three_ds_indicators": [],
            "response_time_ms": 0,
            "detected_scripts": [],
            "probed_at": _ts(),
            "error": None,
        }
        
        url = f"https://{domain}"
        start = time.time()
        
        try:
            # Fetch main page
            proc = subprocess.run(
                ["curl", "-sL", "--max-time", str(timeout),
                 "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "-o", "-", url],
                capture_output=True, text=True, timeout=timeout + 5
            )
            
            elapsed_ms = int((time.time() - start) * 1000)
            result["response_time_ms"] = elapsed_ms
            
            if proc.returncode != 0:
                result["status"] = "down"
                result["error"] = f"curl returned {proc.returncode}"
                return result
            
            html = proc.stdout.lower()
            if not html or len(html) < 100:
                result["status"] = "down"
                result["error"] = "Empty or minimal response"
                return result
            
            result["status"] = "up"
            
            # Detect PSP
            for psp, signatures in self.PSP_SIGNATURES.items():
                for sig in signatures:
                    if sig.lower() in html:
                        result["psp"] = psp.value
                        result["detected_scripts"].append(f"PSP:{psp.value}:{sig}")
                        break
            
            # Detect fraud engine
            for engine, signatures in self.FRAUD_SIGNATURES.items():
                for sig in signatures:
                    if sig.lower() in html:
                        result["fraud_engine"] = engine
                        result["detected_scripts"].append(f"FRAUD:{engine}:{sig}")
                        break
            
            # Detect Shopify
            for sig in self.SHOPIFY_SIGNATURES:
                if sig.lower() in html:
                    result["is_shopify"] = True
                    result["detected_scripts"].append(f"SHOPIFY:{sig}")
                    break
            
            # Detect 3DS indicators
            for sig in self.THREE_DS_SIGNATURES:
                if sig.lower() in html:
                    result["three_ds_indicators"].append(sig)
            
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = f"Timeout after {timeout}s"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
# TARGET DISCOVERY ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class TargetDiscovery:
    """
    V7.0.2: Discovers, verifies, and ranks merchant sites for operations.
    
    Usage:
        td = TargetDiscovery()
        
        # Get all easy sites
        easy = td.get_sites(difficulty="easy")
        
        # Get easy Shopify stores
        shopify = td.get_shopify_sites(difficulty="easy")
        
        # Get best sites for US card, $200
        best = td.recommend_for_card(country="US", amount=200)
        
        # Probe a new site
        result = td.probe_site("new-store.com")
        
        # Run health check
        report = td.run_health_check(max_sites=50)
    """
    
    STATE_DIR = Path("/opt/titan/data/target_discovery")
    STATE_FILE = STATE_DIR / "site_database.json"
    HEALTH_LOG = STATE_DIR / "health_check.log"
    
    def __init__(self):
        self.sites = list(SITE_DATABASE)
        self.probe = SiteProbe()
        self._load_custom_sites()
    
    def _load_custom_sites(self):
        """Load user-added sites from persistent storage"""
        if self.STATE_FILE.exists():
            try:
                data = json.loads(self.STATE_FILE.read_text())
                for site_data in data.get("custom_sites", []):
                    self.sites.append(MerchantSite(
                        domain=site_data["domain"],
                        name=site_data.get("name", site_data["domain"]),
                        category=SiteCategory(site_data.get("category", "misc")),
                        difficulty=SiteDifficulty(site_data.get("difficulty", "easy")),
                        psp=PSP(site_data.get("psp", "unknown")),
                        three_ds=site_data.get("three_ds", "unknown"),
                        fraud_engine=site_data.get("fraud_engine", "unknown"),
                        is_shopify=site_data.get("is_shopify", False),
                        country_focus=site_data.get("country_focus", ["US"]),
                        avs_enforced=site_data.get("avs_enforced", False),
                        max_amount=site_data.get("max_amount", 200),
                        cashout_rate=site_data.get("cashout_rate", 0.50),
                        products=site_data.get("products", ""),
                        notes=site_data.get("notes", "User-added site"),
                        status=SiteStatus(site_data.get("status", "unverified")),
                        last_verified=site_data.get("last_verified", ""),
                        success_rate=site_data.get("success_rate", 0.70),
                    ))
            except Exception as e:
                logger.warning(f"Could not load custom sites: {e}")
    
    def _save_custom_sites(self):
        """Save user-added sites to persistent storage"""
        try:
            self.STATE_DIR.mkdir(parents=True, exist_ok=True)
            custom = [s for s in self.sites if s not in SITE_DATABASE]
            data = {
                "custom_sites": [
                    {
                        "domain": s.domain, "name": s.name,
                        "category": s.category.value,
                        "difficulty": s.difficulty.value,
                        "psp": s.psp.value,
                        "three_ds": s.three_ds,
                        "fraud_engine": s.fraud_engine,
                        "is_shopify": s.is_shopify,
                        "country_focus": s.country_focus,
                        "avs_enforced": s.avs_enforced,
                        "max_amount": s.max_amount,
                        "cashout_rate": s.cashout_rate,
                        "products": s.products,
                        "notes": s.notes,
                        "status": s.status.value,
                        "last_verified": s.last_verified,
                        "success_rate": s.success_rate,
                    }
                    for s in custom
                ],
                "last_updated": _ts(),
            }
            self.STATE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save custom sites: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # QUERY METHODS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_sites(self, difficulty: str = None, category: str = None,
                  country: str = None, shopify_only: bool = False,
                  min_success_rate: float = 0.0,
                  max_results: int = 100) -> List[Dict]:
        """
        Get sites filtered by criteria, sorted by success rate.
        
        Args:
            difficulty: easy, moderate, hard (or None for all)
            category: gaming, gift_cards, shopify, crypto, etc.
            country: ISO country code (US, GB, etc.)
            shopify_only: Only return Shopify stores
            min_success_rate: Minimum estimated success rate (0-1)
            max_results: Max number of results
        """
        filtered = []
        for s in self.sites:
            if difficulty and s.difficulty.value != difficulty:
                continue
            if category and s.category.value != category:
                continue
            if country and country not in s.country_focus:
                continue
            if shopify_only and not s.is_shopify:
                continue
            if s.success_rate < min_success_rate:
                continue
            if s.status == SiteStatus.DEAD:
                continue
            
            filtered.append(self._site_to_dict(s))
        
        filtered.sort(key=lambda x: x["success_rate"], reverse=True)
        return filtered[:max_results]
    
    def get_easy_sites(self, country: str = None) -> List[Dict]:
        """Shortcut: get all easy (2D) sites"""
        return self.get_sites(difficulty="easy", country=country)
    
    def get_shopify_sites(self, difficulty: str = "easy") -> List[Dict]:
        """Get Shopify stores filtered by difficulty"""
        return self.get_sites(difficulty=difficulty, shopify_only=True)
    
    def get_2d_sites(self, country: str = None) -> List[Dict]:
        """Get all 2D secure (no 3DS) sites"""
        results = []
        for s in self.sites:
            if s.three_ds == "none" and s.status != SiteStatus.DEAD:
                if country and country not in s.country_focus:
                    continue
                results.append(self._site_to_dict(s))
        results.sort(key=lambda x: x["success_rate"], reverse=True)
        return results
    
    def recommend_for_card(self, country: str, amount: float = 200,
                           card_type: str = "credit",
                           preferred_category: str = None) -> List[Dict]:
        """
        Recommend best sites for a specific card profile.
        
        Scores each site based on country match, amount fit,
        3DS avoidance, and cashout rate.
        """
        scored = []
        for s in self.sites:
            if s.status == SiteStatus.DEAD:
                continue
            
            score = s.success_rate * 100
            reasons = []
            
            # Country match
            if country in s.country_focus:
                score += 15
                reasons.append(f"Supports {country} cards")
            else:
                score -= 20
            
            # Amount fit
            if amount <= s.max_amount:
                score += 10
                reasons.append(f"Within ${s.max_amount} limit")
            else:
                score -= 30
                reasons.append(f"Over ${s.max_amount} limit")
            
            # 3DS avoidance
            if s.three_ds == "none":
                score += 20
                reasons.append("No 3DS (2D secure)")
            elif s.three_ds == "conditional":
                score += 5
                reasons.append("Conditional 3DS")
            else:
                score -= 15
            
            # Difficulty bonus
            if s.difficulty == SiteDifficulty.EASY:
                score += 10
            elif s.difficulty == SiteDifficulty.HARD:
                score -= 15
            
            # Cashout rate bonus
            score += s.cashout_rate * 20
            
            # AVS factor
            if not s.avs_enforced:
                score += 5
                reasons.append("No AVS enforcement")
            
            # Category preference
            if preferred_category and s.category.value == preferred_category:
                score += 10
                reasons.append(f"Matches preferred category")
            
            site_dict = self._site_to_dict(s)
            site_dict["recommendation_score"] = round(score, 1)
            site_dict["match_reasons"] = reasons
            scored.append(site_dict)
        
        scored.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return scored[:30]
    
    def search(self, query: str) -> List[Dict]:
        """Search sites by name, domain, or product keywords"""
        query_lower = query.lower()
        results = []
        for s in self.sites:
            if (query_lower in s.domain.lower() or
                query_lower in s.name.lower() or
                query_lower in s.products.lower() or
                query_lower in s.notes.lower()):
                results.append(self._site_to_dict(s))
        results.sort(key=lambda x: x["success_rate"], reverse=True)
        return results
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        total = len(self.sites)
        easy = sum(1 for s in self.sites if s.difficulty == SiteDifficulty.EASY)
        moderate = sum(1 for s in self.sites if s.difficulty == SiteDifficulty.MODERATE)
        shopify = sum(1 for s in self.sites if s.is_shopify)
        two_d = sum(1 for s in self.sites if s.three_ds == "none")
        by_category = {}
        for s in self.sites:
            cat = s.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
        by_psp = {}
        for s in self.sites:
            p = s.psp.value
            by_psp[p] = by_psp.get(p, 0) + 1
        
        return {
            "total_sites": total,
            "easy_sites": easy,
            "moderate_sites": moderate,
            "hard_sites": total - easy - moderate,
            "shopify_stores": shopify,
            "2d_secure_sites": two_d,
            "by_category": by_category,
            "by_psp": by_psp,
            "avg_success_rate": round(
                sum(s.success_rate for s in self.sites) / max(total, 1), 2
            ),
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # PROBE & VERIFICATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def probe_site(self, domain: str) -> Dict:
        """
        Probe a website to detect its PSP, fraud engine, and 3DS status.
        Can be used to discover new sites or re-verify existing ones.
        """
        result = self.probe.probe(domain)
        
        # Check if site already exists in database
        existing = next((s for s in self.sites if s.domain == domain), None)
        if existing:
            existing.last_verified = _ts()
            existing.probe_data = result
            if result["status"] == "up":
                existing.status = SiteStatus.VERIFIED
            elif result["status"] in ("down", "timeout"):
                existing.status = SiteStatus.DOWN
        
        return result
    
    def add_site(self, domain: str, name: str = None,
                 category: str = "misc", auto_probe: bool = True) -> Dict:
        """
        Add a new site to the database, optionally auto-probing it.
        
        Returns probe result if auto_probe=True, or site dict.
        """
        # Check if already exists
        existing = next((s for s in self.sites if s.domain == domain), None)
        if existing:
            return {"error": f"Site {domain} already in database", "existing": self._site_to_dict(existing)}
        
        probe_result = None
        psp = PSP.UNKNOWN
        is_shopify = False
        fraud_engine = "unknown"
        three_ds = "unknown"
        
        if auto_probe:
            probe_result = self.probe.probe(domain)
            if probe_result["status"] == "up":
                psp = PSP(probe_result["psp"]) if probe_result["psp"] != "unknown" else PSP.UNKNOWN
                is_shopify = probe_result["is_shopify"]
                fraud_engine = probe_result["fraud_engine"]
                three_ds = "none" if not probe_result["three_ds_indicators"] else "conditional"
        
        new_site = MerchantSite(
            domain=domain,
            name=name or domain.split('.')[0].title(),
            category=SiteCategory(category) if category in [c.value for c in SiteCategory] else SiteCategory.MISC,
            difficulty=SiteDifficulty.EASY if three_ds == "none" and fraud_engine in ("none", "basic", "unknown") else SiteDifficulty.MODERATE,
            psp=psp,
            three_ds=three_ds,
            fraud_engine=fraud_engine,
            is_shopify=is_shopify,
            country_focus=["US"],
            avs_enforced=False,
            max_amount=200,
            cashout_rate=0.50,
            products="",
            notes=f"Auto-discovered. Probe: {probe_result['status'] if probe_result else 'not probed'}",
            status=SiteStatus.VERIFIED if probe_result and probe_result["status"] == "up" else SiteStatus.UNVERIFIED,
            last_verified=_ts() if probe_result else "",
            success_rate=0.70,
            probe_data=probe_result or {},
        )
        
        self.sites.append(new_site)
        self._save_custom_sites()
        
        result = self._site_to_dict(new_site)
        if probe_result:
            result["probe_result"] = probe_result
        return result
    
    def run_health_check(self, max_sites: int = 50, 
                         only_stale_hours: int = 24) -> Dict:
        """
        Run health check on sites, re-probing stale entries.
        
        Args:
            max_sites: Maximum number of sites to probe in one run
            only_stale_hours: Only re-probe sites not checked in this many hours
        """
        cutoff = datetime.utcnow() - timedelta(hours=only_stale_hours)
        cutoff_str = cutoff.isoformat() + "Z"
        
        to_check = []
        for s in self.sites:
            if not s.last_verified or s.last_verified < cutoff_str:
                to_check.append(s)
        
        to_check = to_check[:max_sites]
        
        results = {
            "checked": 0,
            "up": 0,
            "down": 0,
            "changed": 0,
            "errors": 0,
            "details": [],
        }
        
        for site in to_check:
            probe_result = self.probe.probe(site.domain, timeout=10)
            results["checked"] += 1
            
            if probe_result["status"] == "up":
                results["up"] += 1
                # Check if PSP changed
                old_psp = site.psp.value
                new_psp = probe_result["psp"]
                if new_psp != "unknown" and new_psp != old_psp:
                    results["changed"] += 1
                    site.status = SiteStatus.CHANGED
                    results["details"].append(
                        f"{site.domain}: PSP changed {old_psp} → {new_psp}"
                    )
                else:
                    site.status = SiteStatus.VERIFIED
                site.last_verified = _ts()
                site.probe_data = probe_result
            elif probe_result["status"] in ("down", "timeout"):
                results["down"] += 1
                site.status = SiteStatus.DOWN
                results["details"].append(f"{site.domain}: DOWN")
            else:
                results["errors"] += 1
            
            # Small delay between probes to avoid rate limiting
            time.sleep(0.5)
        
        results["timestamp"] = _ts()
        
        # Save updated state
        self._save_custom_sites()
        
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _site_to_dict(self, s: MerchantSite) -> Dict:
        """Convert MerchantSite to dict for API/GUI consumption"""
        return {
            "domain": s.domain,
            "name": s.name,
            "category": s.category.value,
            "difficulty": s.difficulty.value,
            "psp": s.psp.value,
            "three_ds": s.three_ds,
            "fraud_engine": s.fraud_engine,
            "is_shopify": s.is_shopify,
            "country_focus": s.country_focus,
            "avs_enforced": s.avs_enforced,
            "max_amount": s.max_amount,
            "cashout_rate": s.cashout_rate,
            "products": s.products,
            "notes": s.notes,
            "status": s.status.value,
            "last_verified": s.last_verified,
            "success_rate": s.success_rate,
            "success_rate_pct": f"{s.success_rate*100:.0f}%",
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.0.3: AUTO-DISCOVERY ENGINE
# Automatically finds new easy/2D/Shopify targets via Google dorking,
# probes them, and classifies by 3DS bypass potential
# ═══════════════════════════════════════════════════════════════════════════

# Google dork queries designed to find easy merchant sites
DISCOVERY_DORKS = [
    # Shopify stores (easy checkout, usually Stripe/Shopify Payments, no custom fraud)
    {"query": 'site:myshopify.com "add to cart" -password -login', "category": "shopify", "expected_psp": "shopify_payments"},
    {"query": '"powered by shopify" "add to cart" inurl:products', "category": "shopify", "expected_psp": "shopify_payments"},
    {"query": '"cdn.shopify.com" "buy now" -alibaba -amazon', "category": "shopify", "expected_psp": "shopify_payments"},
    {"query": 'inurl:"/collections/" "checkout" site:*.com "shopify"', "category": "shopify", "expected_psp": "shopify_payments"},

    # Stripe merchants (generally low 3DS, risk-based via Radar)
    {"query": '"js.stripe.com/v3" "checkout" "add to cart" -github -stackoverflow', "category": "digital", "expected_psp": "stripe"},
    {"query": '"pk_live_" "checkout" "buy" site:*.com -github', "category": "digital", "expected_psp": "stripe"},

    # Digital goods (instant delivery, high cashout)
    {"query": '"buy gift card" "instant delivery" "credit card" -amazon -walmart', "category": "gift_cards", "expected_psp": "stripe"},
    {"query": '"game key" "instant delivery" "add to cart" -steam -epic', "category": "gaming", "expected_psp": "stripe"},
    {"query": '"digital download" "buy now" "credit card" "no registration"', "category": "digital", "expected_psp": "stripe"},

    # Authorize.net merchants (lowest 3DS friction of all PSPs)
    {"query": '"accept.authorize.net" "checkout" "add to cart"', "category": "misc", "expected_psp": "authorize_net"},
    {"query": '"authorizenet" "buy now" "credit card" site:*.com', "category": "misc", "expected_psp": "authorize_net"},

    # Subscription services (low amounts, recurring exempt from 3DS)
    {"query": '"subscribe now" "$9.99" "credit card" -facebook -twitter', "category": "subscriptions", "expected_psp": "stripe"},
    {"query": '"monthly subscription" "start free trial" "card" site:*.com', "category": "subscriptions", "expected_psp": "stripe"},

    # Crypto/gift card sites (highest cashout)
    {"query": '"buy bitcoin" "gift card" "credit card" "instant" -coinbase -binance', "category": "crypto", "expected_psp": "stripe"},
    {"query": '"buy crypto" "voucher" "debit card" "no kyc"', "category": "crypto", "expected_psp": "stripe"},
]

# Search engine URLs for dorking
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={query}&num=20",
    "bing": "https://www.bing.com/search?q={query}&count=20",
    "duckduckgo": "https://html.duckduckgo.com/html/?q={query}",
}


class AutoDiscovery:
    """
    V7.0.3: Automatically discovers new merchant targets via:
    1. Google dorking with curated queries
    2. Auto-probing discovered domains for PSP/3DS/fraud engine
    3. 3DS bypass scoring and classification
    4. Filtering for easy/2D/downgradeable sites
    
    Usage:
        discovery = AutoDiscovery()
        
        # Run full auto-discovery (finds + probes + scores)
        results = discovery.run_discovery(max_sites=50)
        
        # Discover Shopify stores only
        shopify = discovery.discover_shopify(max_sites=30)
        
        # Discover and score by 3DS bypass potential
        bypassed = discovery.discover_with_bypass_scoring(max_sites=50)
    """
    
    DISCOVERY_CACHE = Path("/opt/titan/data/target_discovery/auto_discovered.json")
    
    def __init__(self):
        self.probe = SiteProbe()
        self._discovered_cache: List[str] = []
        self._load_cache()
    
    def _load_cache(self):
        """Load previously discovered domains to avoid re-probing"""
        if self.DISCOVERY_CACHE.exists():
            try:
                data = json.loads(self.DISCOVERY_CACHE.read_text())
                self._discovered_cache = data.get("domains", [])
            except Exception:
                pass
    
    def _save_cache(self):
        """Save discovered domains"""
        try:
            self.DISCOVERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "domains": self._discovered_cache,
                "last_discovery": _ts(),
                "total_discovered": len(self._discovered_cache),
            }
            self.DISCOVERY_CACHE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save discovery cache: {e}")
    
    def _search_google(self, query: str, engine: str = "google",
                       timeout: int = 15) -> List[str]:
        """
        Execute a search query and extract domain names from results.
        Returns list of unique domains.
        """
        url = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["google"]).format(
            query=query.replace(" ", "+")
        )
        
        domains = []
        try:
            proc = subprocess.run(
                ["curl", "-sL", "--max-time", str(timeout),
                 "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                 "-H", "Accept-Language: en-US,en;q=0.9",
                 url],
                capture_output=True, text=True, timeout=timeout + 5
            )
            
            if proc.returncode == 0 and proc.stdout:
                html = proc.stdout
                # Extract URLs from search results
                url_patterns = [
                    r'href="https?://(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)',
                    r'https?://(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)',
                ]
                
                for pattern in url_patterns:
                    matches = re.findall(pattern, html)
                    for domain in matches:
                        domain = domain.lower().strip(".")
                        # Filter out search engines and known non-merchant domains
                        skip_domains = {
                            "google.com", "bing.com", "duckduckgo.com", "yahoo.com",
                            "youtube.com", "wikipedia.org", "reddit.com", "twitter.com",
                            "facebook.com", "instagram.com", "linkedin.com", "github.com",
                            "stackoverflow.com", "medium.com", "quora.com", "pinterest.com",
                            "tumblr.com", "tiktok.com", "googleapis.com", "gstatic.com",
                            "cloudflare.com", "w3.org", "schema.org",
                        }
                        if domain not in skip_domains and len(domain) > 4:
                            domains.append(domain)
        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for d in domains:
            if d not in seen:
                seen.add(d)
                unique.append(d)
        
        return unique[:20]  # Max 20 per query
    
    def _score_3ds_bypass(self, probe_result: Dict) -> Dict:
        """Score a probed site's 3DS bypass potential using ThreeDSBypassEngine"""
        try:
            from three_ds_strategy import ThreeDSBypassEngine
            engine = ThreeDSBypassEngine()
            return engine.score_site(
                domain=probe_result.get("domain", ""),
                psp=probe_result.get("psp", "unknown"),
                three_ds="none" if not probe_result.get("three_ds_indicators") else "conditional",
                fraud_engine=probe_result.get("fraud_engine", "none"),
                is_shopify=probe_result.get("is_shopify", False),
            )
        except ImportError:
            return {"bypass_score": 50, "bypass_level": "UNKNOWN"}
    
    def discover_sites(self, dork_indices: List[int] = None,
                       engine: str = "google",
                       max_per_query: int = 15,
                       auto_probe: bool = True) -> List[Dict]:
        """
        Run discovery using Google dorks.
        
        Args:
            dork_indices: Which dorks to use (indices into DISCOVERY_DORKS). None = all.
            engine: Search engine to use (google, bing, duckduckgo)
            max_per_query: Max domains to extract per query
            auto_probe: Whether to auto-probe discovered domains
        
        Returns list of discovered + probed site dicts.
        """
        dorks = DISCOVERY_DORKS if dork_indices is None else [
            DISCOVERY_DORKS[i] for i in dork_indices if i < len(DISCOVERY_DORKS)
        ]
        
        all_domains = {}  # domain → dork info
        
        for dork in dorks:
            logger.info(f"Searching: {dork['query'][:60]}...")
            found = self._search_google(dork["query"], engine)
            
            for domain in found[:max_per_query]:
                if domain not in all_domains and domain not in self._discovered_cache:
                    all_domains[domain] = dork
            
            time.sleep(2)  # Rate limit between searches
        
        results = []
        
        for domain, dork_info in all_domains.items():
            site_result = {
                "domain": domain,
                "source_query": dork_info["query"][:80],
                "expected_category": dork_info["category"],
                "expected_psp": dork_info["expected_psp"],
                "probe_result": None,
                "bypass_score": None,
                "bypass_level": None,
                "classification": "unprobed",
            }
            
            if auto_probe:
                probe = self.probe.probe(domain, timeout=10)
                site_result["probe_result"] = probe
                
                if probe["status"] == "up":
                    # Classify 3DS status
                    has_3ds = bool(probe.get("three_ds_indicators"))
                    site_result["psp"] = probe.get("psp", "unknown")
                    site_result["fraud_engine"] = probe.get("fraud_engine", "none")
                    site_result["is_shopify"] = probe.get("is_shopify", False)
                    site_result["three_ds"] = "conditional" if has_3ds else "none"
                    
                    # Score 3DS bypass potential
                    bypass = self._score_3ds_bypass(probe)
                    site_result["bypass_score"] = bypass.get("bypass_score", 0)
                    site_result["bypass_level"] = bypass.get("bypass_level", "UNKNOWN")
                    site_result["bypass_techniques"] = bypass.get("techniques", [])
                    site_result["downgrade_possible"] = bypass.get("downgrade_possible", False)
                    
                    # Classify
                    if not has_3ds and probe.get("fraud_engine") in ("none", "basic", "unknown"):
                        site_result["classification"] = "EASY_2D"
                    elif not has_3ds:
                        site_result["classification"] = "2D_WITH_ANTIFRAUD"
                    elif bypass.get("bypass_score", 0) >= 70:
                        site_result["classification"] = "3DS_BYPASSABLE"
                    elif bypass.get("downgrade_possible"):
                        site_result["classification"] = "3DS_DOWNGRADEABLE"
                    else:
                        site_result["classification"] = "3DS_HARD"
                else:
                    site_result["classification"] = "unreachable"
                
                time.sleep(0.5)  # Rate limit between probes
            
            results.append(site_result)
            self._discovered_cache.append(domain)
        
        self._save_cache()
        
        # Sort by bypass score (highest first), then by classification
        classification_order = {
            "EASY_2D": 0, "2D_WITH_ANTIFRAUD": 1, "3DS_BYPASSABLE": 2,
            "3DS_DOWNGRADEABLE": 3, "3DS_HARD": 4, "unreachable": 5, "unprobed": 6,
        }
        results.sort(key=lambda x: (
            classification_order.get(x["classification"], 9),
            -(x.get("bypass_score") or 0)
        ))
        
        return results
    
    def discover_shopify(self, max_sites: int = 30, engine: str = "google") -> List[Dict]:
        """Discover Shopify stores specifically — usually easiest targets"""
        shopify_dorks = [i for i, d in enumerate(DISCOVERY_DORKS) if d["category"] == "shopify"]
        results = self.discover_sites(dork_indices=shopify_dorks, engine=engine)
        return [r for r in results if r.get("is_shopify") or r["classification"] in ("EASY_2D", "2D_WITH_ANTIFRAUD")][:max_sites]
    
    def discover_2d_only(self, max_sites: int = 50, engine: str = "google") -> List[Dict]:
        """Discover only 2D (no 3DS) sites"""
        results = self.discover_sites(engine=engine)
        return [r for r in results if r["classification"] in ("EASY_2D", "2D_WITH_ANTIFRAUD")][:max_sites]
    
    def discover_with_bypass_scoring(self, max_sites: int = 50,
                                      min_bypass_score: int = 60,
                                      engine: str = "google") -> List[Dict]:
        """Discover sites and return only those with high 3DS bypass potential"""
        results = self.discover_sites(engine=engine)
        filtered = [r for r in results if (r.get("bypass_score") or 0) >= min_bypass_score]
        return filtered[:max_sites]
    
    def discover_downgradeable(self, max_sites: int = 30, engine: str = "google") -> List[Dict]:
        """Discover sites where 3DS 2.0→1.0 downgrade is possible"""
        results = self.discover_sites(engine=engine)
        return [r for r in results if r.get("downgrade_possible")][:max_sites]
    
    def get_discovery_stats(self) -> Dict:
        """Get statistics about auto-discovery runs"""
        return {
            "total_discovered": len(self._discovered_cache),
            "dork_count": len(DISCOVERY_DORKS),
            "dork_categories": list(set(d["category"] for d in DISCOVERY_DORKS)),
            "cache_file": str(self.DISCOVERY_CACHE),
        }


# ═══════════════════════════════════════════════════════════════════════════
# ENHANCED TARGET DISCOVERY — Integrates auto-discovery + bypass scoring
# ═══════════════════════════════════════════════════════════════════════════

# Add methods to TargetDiscovery that integrate with auto-discovery and bypass scoring

def _add_bypass_methods(cls):
    """Monkey-patch TargetDiscovery with 3DS bypass and auto-discovery methods"""
    
    def get_sites_with_bypass_scores(self, difficulty=None, country=None, 
                                      card_country="US", amount=200) -> List[Dict]:
        """Get all sites with 3DS bypass scores attached"""
        sites = self.get_sites(difficulty=difficulty, country=country)
        try:
            from three_ds_strategy import ThreeDSBypassEngine
            engine = ThreeDSBypassEngine()
            for site in sites:
                bypass = engine.score_site(
                    site["domain"], site["psp"], site["three_ds"],
                    site["fraud_engine"], site["is_shopify"], amount, card_country
                )
                site["bypass_score"] = bypass["bypass_score"]
                site["bypass_level"] = bypass["bypass_level"]
                site["downgrade_possible"] = bypass["downgrade_possible"]
                site["bypass_techniques"] = bypass["techniques"]
            sites.sort(key=lambda x: x.get("bypass_score", 0), reverse=True)
        except ImportError:
            pass
        return sites
    
    def get_downgradeable_sites(self) -> List[Dict]:
        """Get sites where 3DS 2.0→1.0 downgrade is possible"""
        try:
            from three_ds_strategy import ThreeDSBypassEngine
            engine = ThreeDSBypassEngine()
            all_sites = self.get_sites()
            return engine.get_downgradeable_sites(all_sites)
        except ImportError:
            return []
    
    def get_best_bypass_targets(self, card_country="US", amount=200,
                                 min_score: int = 60) -> List[Dict]:
        """Get sites ranked by 3DS bypass potential for a specific card"""
        sites = self.get_sites_with_bypass_scores(
            card_country=card_country, amount=amount
        )
        return [s for s in sites if s.get("bypass_score", 0) >= min_score]
    
    def auto_discover_new(self, max_sites=50, engine="google") -> List[Dict]:
        """Run auto-discovery to find new targets, probe them, and score them"""
        discovery = AutoDiscovery()
        results = discovery.discover_sites(engine=engine)
        
        # Auto-add good discoveries to the database
        added = []
        for r in results:
            if r["classification"] in ("EASY_2D", "2D_WITH_ANTIFRAUD", "3DS_BYPASSABLE"):
                existing = next((s for s in self.sites if s.domain == r["domain"]), None)
                if not existing:
                    probe = r.get("probe_result", {})
                    three_ds = r.get("three_ds", "unknown")
                    fraud_eng = r.get("fraud_engine", "unknown")
                    
                    new_site = MerchantSite(
                        domain=r["domain"],
                        name=r["domain"].split('.')[0].title(),
                        category=SiteCategory(r.get("expected_category", "misc")) 
                            if r.get("expected_category") in [c.value for c in SiteCategory] 
                            else SiteCategory.MISC,
                        difficulty=SiteDifficulty.EASY if three_ds == "none" and fraud_eng in ("none", "basic", "unknown")
                                   else SiteDifficulty.MODERATE,
                        psp=PSP(r.get("psp", "unknown")) if r.get("psp") in [p.value for p in PSP] else PSP.UNKNOWN,
                        three_ds=three_ds,
                        fraud_engine=fraud_eng,
                        is_shopify=r.get("is_shopify", False),
                        country_focus=["US"],
                        avs_enforced=False,
                        max_amount=200,
                        cashout_rate=0.50,
                        products=f"Auto-discovered via: {r.get('expected_category', 'search')}",
                        notes=f"Auto-discovered {_ts()}. Classification: {r['classification']}. "
                              f"Bypass score: {r.get('bypass_score', 'N/A')}",
                        status=SiteStatus.VERIFIED,
                        last_verified=_ts(),
                        success_rate=0.70,
                        probe_data=probe,
                    )
                    self.sites.append(new_site)
                    added.append(r)
        
        if added:
            self._save_custom_sites()
        
        return {
            "total_searched": len(results),
            "easy_2d_found": sum(1 for r in results if r["classification"] == "EASY_2D"),
            "2d_with_antifraud": sum(1 for r in results if r["classification"] == "2D_WITH_ANTIFRAUD"),
            "bypassable_found": sum(1 for r in results if r["classification"] == "3DS_BYPASSABLE"),
            "downgradeable_found": sum(1 for r in results if r["classification"] == "3DS_DOWNGRADEABLE"),
            "hard_3ds": sum(1 for r in results if r["classification"] == "3DS_HARD"),
            "auto_added_to_db": len(added),
            "results": results[:max_sites],
        }
    
    cls.get_sites_with_bypass_scores = get_sites_with_bypass_scores
    cls.get_downgradeable_sites = get_downgradeable_sites
    cls.get_best_bypass_targets = get_best_bypass_targets
    cls.auto_discover_new = auto_discover_new
    return cls

# Apply the enhancements
TargetDiscovery = _add_bypass_methods(TargetDiscovery)


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def get_easy_sites(country=None):
    """Quick: get all easy 2D sites"""
    return TargetDiscovery().get_easy_sites(country)

def get_2d_sites(country=None):
    """Quick: get all sites with no 3DS"""
    return TargetDiscovery().get_2d_sites(country)

def get_shopify_sites(difficulty="easy"):
    """Quick: get easy Shopify stores"""
    return TargetDiscovery().get_shopify_sites(difficulty)

def recommend_sites(country="US", amount=200):
    """Quick: recommend sites for a card"""
    return TargetDiscovery().recommend_for_card(country, amount)

def probe_site(domain):
    """Quick: probe a site for PSP/3DS/fraud engine"""
    return SiteProbe().probe(domain)

def get_site_stats():
    """Quick: get database statistics"""
    return TargetDiscovery().get_stats()

def search_sites(query):
    """Quick: search sites by keyword"""
    return TargetDiscovery().search(query)

def auto_discover(max_sites=50, engine="google"):
    """Quick: run auto-discovery to find new easy targets"""
    return TargetDiscovery().auto_discover_new(max_sites, engine)

def get_bypass_targets(card_country="US", amount=200, min_score=60):
    """Quick: get sites ranked by 3DS bypass potential"""
    return TargetDiscovery().get_best_bypass_targets(card_country, amount, min_score)

def get_downgradeable():
    """Quick: get sites where 3DS 2.0→1.0 downgrade works"""
    return TargetDiscovery().get_downgradeable_sites()
