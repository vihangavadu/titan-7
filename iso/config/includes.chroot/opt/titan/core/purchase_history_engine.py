"""
TITAN V7.0 SINGULARITY - Purchase History Engine
Generates realistic aged purchase history with CC holder data, billing address,
order confirmations, and commerce session artifacts for browser profiles.

Integrates with AdvancedProfileGenerator to produce 400MB+ profiles with
believable e-commerce history that passes antifraud session analysis.

Key Capabilities:
1. Purchase record injection (order history, confirmation emails, receipts)
2. Commerce cookie aging (cart tokens, session IDs, payment fingerprints)
3. Autofill data pre-population (CC holder, billing, shipping)
4. Cached checkout page artifacts (images, CSS, JS from real merchants)
5. Payment processor trust tokens (Stripe mID, PayPal TLTSID, Adyen device FP)
"""

import json
import sqlite3
import hashlib
import secrets
import random
import os
import struct
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger("TITAN-V7-PURCHASE-ENGINE")


def _fx_sqlite(db_path, page_size=32768):
    """SQLite connection with Firefox-matching PRAGMA settings.
    Real Firefox uses page_size=32768, journal_mode=WAL, auto_vacuum=INCREMENTAL.
    Default SQLite settings are an instant forensic detection vector."""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(f"PRAGMA page_size = {page_size}")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA auto_vacuum = INCREMENTAL")
    c.execute("PRAGMA wal_autocheckpoint = 512")
    c.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    return conn


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

class OrderStatus(Enum):
    DELIVERED = "delivered"
    SHIPPED = "shipped"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"


class PaymentMethod(Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    CRYPTO = "crypto"
    GIFT_CARD = "gift_card"


@dataclass
class CardHolderData:
    """Cardholder data for purchase history and autofill injection"""
    full_name: str
    first_name: str
    last_name: str
    card_last_four: str
    card_network: str          # visa, mastercard, amex
    card_exp_display: str      # "12/27"
    billing_address: str
    billing_city: str
    billing_state: str
    billing_zip: str
    billing_country: str = "US"
    email: str = ""
    phone: str = ""
    
    @property
    def billing_line(self) -> str:
        return f"{self.billing_address}, {self.billing_city}, {self.billing_state} {self.billing_zip}"


@dataclass
class PurchaseRecord:
    """Single purchase record for history injection"""
    merchant: str
    merchant_domain: str
    order_id: str
    amount: float
    currency: str
    items: List[Dict[str, Any]]
    status: OrderStatus
    payment_method: PaymentMethod
    card_last_four: str
    order_date: datetime
    delivery_date: Optional[datetime]
    shipping_address: str
    confirmation_email_id: str


@dataclass
class PurchaseHistoryConfig:
    """Configuration for purchase history generation"""
    cardholder: CardHolderData
    profile_age_days: int = 95
    num_purchases: int = 8      # Total purchase count over profile lifetime
    min_amount: float = 12.99
    max_amount: float = 149.99
    target_merchants: Optional[List[str]] = None   # Focus on these merchants
    include_failed_attempt: bool = True             # One failed/cancelled for realism


# ═══════════════════════════════════════════════════════════════════════════
# MERCHANT TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════

MERCHANT_TEMPLATES = {
    # ── Major Retailers (diverse PSPs) ────────────────────────────────
    "amazon.com": {
        "name": "Amazon.com",
        "order_prefix": "114",
        "order_format": "{prefix}-{seg1}-{seg2}",
        "items_pool": [
            {"name": "Anker USB-C Hub", "price": 35.99, "category": "Electronics"},
            {"name": "Bose QuietComfort Earbuds", "price": 179.00, "category": "Electronics"},
            {"name": "Kindle Paperwhite", "price": 139.99, "category": "Electronics"},
            {"name": "AmazonBasics Backpack", "price": 29.99, "category": "Bags"},
            {"name": "Logitech MX Master 3S", "price": 99.99, "category": "Electronics"},
            {"name": "Sony WH-1000XM5", "price": 278.00, "category": "Electronics"},
            {"name": "Hydro Flask 32oz", "price": 44.95, "category": "Kitchen"},
            {"name": "Anker PowerCore 10000", "price": 25.99, "category": "Electronics"},
        ],
        "processor": "amazon_pay",
        "cookie_names": ["session-id", "ubid-main", "session-token", "csm-hit", "i18n-prefs"],
        "localStorage_keys": ["csm-hit", "session-id-time"],
    },
    "walmart.com": {
        "name": "Walmart",
        "order_prefix": "WM",
        "order_format": "{prefix}{seg1}{seg2}",
        "items_pool": [
            {"name": "Great Value Paper Towels 12pk", "price": 15.97, "category": "Household"},
            {"name": "onn. 32\" Class HD TV", "price": 98.00, "category": "Electronics"},
            {"name": "Mainstays 5-Shelf Bookcase", "price": 54.00, "category": "Furniture"},
            {"name": "Ozark Trail Tumbler 20oz", "price": 7.97, "category": "Kitchen"},
            {"name": "Equate Vitamin D3 5000IU", "price": 6.48, "category": "Health"},
        ],
        "processor": "worldpay",
        "cookie_names": ["auth", "cart-item-count", "CRT", "type", "vtc"],
        "localStorage_keys": ["cart-active", "search-history", "user-pref"],
    },
    "bestbuy.com": {
        "name": "Best Buy",
        "order_prefix": "BBY01",
        "order_format": "{prefix}-{seg1}{seg2}",
        "items_pool": [
            {"name": "Insignia 50\" 4K Fire TV", "price": 249.99, "category": "TVs"},
            {"name": "Rocketfish HDMI Cable 8ft", "price": 29.99, "category": "Cables"},
            {"name": "SanDisk 256GB microSD", "price": 24.99, "category": "Storage"},
            {"name": "Insignia USB-C Wall Charger", "price": 19.99, "category": "Chargers"},
            {"name": "JBL Flip 6 Speaker", "price": 99.99, "category": "Audio"},
        ],
        "processor": "cybersource",
        "cookie_names": ["UID", "SID", "CTX", "ltc", "vt"],
        "localStorage_keys": ["bby-locale", "bby-acct-cache", "bby-cart-count"],
    },
    "target.com": {
        "name": "Target",
        "order_prefix": "TGT",
        "order_format": "{prefix}-{seg1}-{seg2}",
        "items_pool": [
            {"name": "Threshold Throw Blanket", "price": 25.00, "category": "Home"},
            {"name": "Good & Gather Trail Mix", "price": 5.99, "category": "Grocery"},
            {"name": "Cat & Jack Kids T-Shirt", "price": 8.00, "category": "Clothing"},
            {"name": "Room Essentials Desk Lamp", "price": 12.00, "category": "Home"},
            {"name": "up&up Ibuprofen 200mg", "price": 4.99, "category": "Health"},
        ],
        "processor": "stripe",
        "cookie_names": ["visitorId", "TealeafAkaSid", "sapphire", "fiatsCookie"],
        "localStorage_keys": ["tgt-visitor", "tgt-cart", "tgt-search-history"],
    },
    # ── Tech & Electronics ────────────────────────────────────────────
    "newegg.com": {
        "name": "Newegg",
        "order_prefix": "NE",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Corsair Vengeance 32GB DDR5", "price": 89.99, "category": "Memory"},
            {"name": "ASUS TUF Gaming B650", "price": 179.99, "category": "Motherboards"},
            {"name": "Samsung 990 Pro 2TB NVMe", "price": 149.99, "category": "Storage"},
            {"name": "be quiet! Pure Power 12 750W", "price": 99.90, "category": "PSU"},
        ],
        "processor": "adyen",
        "cookie_names": ["NV%5FNEWEGG", "NV%5FCONFIGURATION", "NV%5FCUSTOMER"],
        "localStorage_keys": ["ne-cart", "ne-session", "ne-recommendations"],
    },
    "ebay.com": {
        "name": "eBay",
        "order_prefix": "EB",
        "order_format": "{prefix}-{seg1}-{seg2}",
        "items_pool": [
            {"name": "Refurbished iPhone 14 Pro", "price": 649.00, "category": "Phones"},
            {"name": "Vintage Levi's 501 Jeans", "price": 45.00, "category": "Clothing"},
            {"name": "Arduino Starter Kit", "price": 34.99, "category": "Electronics"},
            {"name": "Pokemon TCG Booster Box", "price": 89.99, "category": "Collectibles"},
        ],
        "processor": "paypal",
        "cookie_names": ["ebay", "dp1", "nonsession", "s", "ak_bmsc"],
        "localStorage_keys": ["ebay-cart", "ebay-recently-viewed"],
    },
    # ── Shopify Stores (Shopify Payments) ─────────────────────────────
    "fashionnova.com": {
        "name": "Fashion Nova",
        "order_prefix": "FN",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Classic High Waist Skinny Jeans", "price": 24.99, "category": "Clothing"},
            {"name": "Oversized Graphic Tee", "price": 16.99, "category": "Clothing"},
            {"name": "Chunky Platform Sneakers", "price": 39.99, "category": "Shoes"},
        ],
        "processor": "shopify_payments",
        "cookie_names": ["_shopify_sa_t", "_shopify_y", "cart_ts", "cart_sig"],
        "localStorage_keys": ["shopify-cart", "shopify-checkout-token"],
    },
    "gymshark.com": {
        "name": "Gymshark",
        "order_prefix": "GS",
        "order_format": "{prefix}-{seg1}",
        "items_pool": [
            {"name": "Vital Seamless Leggings", "price": 54.00, "category": "Activewear"},
            {"name": "Crest Hoodie", "price": 48.00, "category": "Activewear"},
            {"name": "Speed Shorts", "price": 30.00, "category": "Activewear"},
        ],
        "processor": "shopify_payments",
        "cookie_names": ["_shopify_sa_t", "_shopify_y", "cart_ts"],
        "localStorage_keys": ["shopify-cart", "shopify-checkout-token"],
    },
    # ── Subscription / Digital Services ───────────────────────────────
    "spotify.com": {
        "name": "Spotify",
        "order_prefix": "SP",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Spotify Premium Individual (Monthly)", "price": 11.99, "category": "Subscription"},
            {"name": "Spotify Premium Family (Monthly)", "price": 17.99, "category": "Subscription"},
        ],
        "processor": "braintree",
        "cookie_names": ["sp_t", "sp_dc", "sp_key"],
        "localStorage_keys": ["spotify-prefs", "spotify-playback"],
    },
    "netflix.com": {
        "name": "Netflix",
        "order_prefix": "NF",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Netflix Standard (Monthly)", "price": 15.49, "category": "Subscription"},
            {"name": "Netflix Premium (Monthly)", "price": 22.99, "category": "Subscription"},
        ],
        "processor": "braintree",
        "cookie_names": ["NetflixId", "SecureNetflixId", "memclid"],
        "localStorage_keys": ["netflix-prefs", "netflix-profiles"],
    },
    # ── Food & Delivery (Square, Stripe, Braintree) ───────────────────
    "doordash.com": {
        "name": "DoorDash",
        "order_prefix": "DD",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Chipotle Burrito Bowl Delivery", "price": 18.50, "category": "Food"},
            {"name": "McDonald's Family Meal Delivery", "price": 32.00, "category": "Food"},
            {"name": "Thai Basil Fried Rice Delivery", "price": 16.99, "category": "Food"},
        ],
        "processor": "stripe",
        "cookie_names": ["dd_session", "dd_user", "dd_cart"],
        "localStorage_keys": ["dd-address", "dd-recent-orders"],
    },
    "ubereats.com": {
        "name": "Uber Eats",
        "order_prefix": "UE",
        "order_format": "{prefix}-{seg1}",
        "items_pool": [
            {"name": "Sushi Platter Delivery", "price": 28.00, "category": "Food"},
            {"name": "Pizza Large + Sides Delivery", "price": 24.50, "category": "Food"},
        ],
        "processor": "braintree",
        "cookie_names": ["ue_session", "ue_sid", "ue_lat"],
        "localStorage_keys": ["uber-eats-address", "uber-eats-cart"],
    },
    # ── Gaming & Digital (Adyen, PayPal, Internal) ────────────────────
    "steampowered.com": {
        "name": "Steam",
        "order_prefix": "ST",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Elden Ring", "price": 59.99, "category": "Games"},
            {"name": "Baldur's Gate 3", "price": 59.99, "category": "Games"},
            {"name": "Cyberpunk 2077", "price": 29.99, "category": "Games"},
            {"name": "Hades II (Early Access)", "price": 29.99, "category": "Games"},
        ],
        "processor": "paypal",
        "cookie_names": ["steamLoginSecure", "sessionid", "steamMachineAuth"],
        "localStorage_keys": ["steam-cart", "steam-library-cache"],
    },
    "eneba.com": {
        "name": "Eneba",
        "order_prefix": "EN",
        "order_format": "{prefix}-{seg1}-{seg2}",
        "items_pool": [
            {"name": "Xbox Game Pass Ultimate 1mo", "price": 12.99, "category": "Subscriptions"},
            {"name": "Nintendo eShop $50", "price": 42.99, "category": "Gift Cards"},
            {"name": "Spotify Premium 6mo", "price": 49.99, "category": "Subscriptions"},
        ],
        "processor": "checkout_com",
        "cookie_names": ["_eneba_session", "_eneba_cart", "_eneba_auth"],
        "localStorage_keys": ["eneba-user", "eneba-cart-items", "eneba-locale"],
    },
    "g2a.com": {
        "name": "G2A",
        "order_prefix": "G2A",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Windows 11 Pro Key", "price": 24.99, "category": "Software"},
            {"name": "Microsoft Office 2021 Key", "price": 34.99, "category": "Software"},
            {"name": "Valorant Points 1000", "price": 9.99, "category": "In-Game"},
        ],
        "processor": "adyen",
        "cookie_names": ["g2a_session", "g2a_cart", "g2a_user"],
        "localStorage_keys": ["g2a-user-pref", "g2a-cart-cache", "g2a-search"],
    },
    # ── Fashion & Lifestyle (Klarna, Afterpay, Stripe) ────────────────
    "nike.com": {
        "name": "Nike",
        "order_prefix": "NK",
        "order_format": "{prefix}{seg1}{seg2}",
        "items_pool": [
            {"name": "Air Max 90", "price": 130.00, "category": "Shoes"},
            {"name": "Dri-FIT Running Shirt", "price": 35.00, "category": "Clothing"},
            {"name": "Nike Sportswear Club Fleece Hoodie", "price": 60.00, "category": "Clothing"},
        ],
        "processor": "adyen",
        "cookie_names": ["NIKE_COMMERCE_COUNTRY", "anonymousId", "guidS", "visitData"],
        "localStorage_keys": ["nike-cart", "nike-locale", "nike-member"],
    },
    "zara.com": {
        "name": "Zara",
        "order_prefix": "ZR",
        "order_format": "{prefix}-{seg1}-{seg2}",
        "items_pool": [
            {"name": "Oversized Linen Blazer", "price": 89.90, "category": "Clothing"},
            {"name": "Leather Effect Bag", "price": 45.90, "category": "Accessories"},
            {"name": "Wide Leg Trousers", "price": 49.90, "category": "Clothing"},
        ],
        "processor": "adyen",
        "cookie_names": ["zara_session", "zara_cart", "zara_locale"],
        "localStorage_keys": ["zara-cart", "zara-wishlist"],
    },
    "shein.com": {
        "name": "SHEIN",
        "order_prefix": "SH",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Floral Print Midi Dress", "price": 18.49, "category": "Clothing"},
            {"name": "Casual Crossbody Bag", "price": 8.99, "category": "Accessories"},
            {"name": "Chunky Sneakers", "price": 32.00, "category": "Shoes"},
        ],
        "processor": "paypal",
        "cookie_names": ["shein_session", "shein_cart", "shein_user"],
        "localStorage_keys": ["shein-cart", "shein-wishlist", "shein-locale"],
    },
    # ── Home & Lifestyle (various PSPs) ───────────────────────────────
    "etsy.com": {
        "name": "Etsy",
        "order_prefix": "ET",
        "order_format": "{prefix}-{seg1}",
        "items_pool": [
            {"name": "Custom Name Necklace", "price": 28.00, "category": "Jewelry"},
            {"name": "Handmade Ceramic Mug", "price": 22.00, "category": "Home"},
            {"name": "Personalized Leather Wallet", "price": 45.00, "category": "Accessories"},
        ],
        "processor": "paypal",
        "cookie_names": ["uaid", "user_prefs", "fve"],
        "localStorage_keys": ["etsy-cart", "etsy-favorites"],
    },
    "wayfair.com": {
        "name": "Wayfair",
        "order_prefix": "WF",
        "order_format": "{prefix}{seg1}",
        "items_pool": [
            {"name": "Tufted Accent Chair", "price": 189.99, "category": "Furniture"},
            {"name": "Area Rug 5x7", "price": 79.99, "category": "Home"},
            {"name": "Floating Wall Shelves Set", "price": 34.99, "category": "Home"},
        ],
        "processor": "stripe",
        "cookie_names": ["wf_session", "wf_cart", "wf_user"],
        "localStorage_keys": ["wayfair-cart", "wayfair-recent"],
    },
    # ── Buy Now Pay Later (Klarna, Afterpay) ──────────────────────────
    "asos.com": {
        "name": "ASOS",
        "order_prefix": "AS",
        "order_format": "{prefix}{seg1}{seg2}",
        "items_pool": [
            {"name": "ASOS DESIGN Oversized T-Shirt", "price": 16.00, "category": "Clothing"},
            {"name": "Nike Air Force 1 '07", "price": 110.00, "category": "Shoes"},
            {"name": "ASOS DESIGN Skinny Chinos", "price": 32.00, "category": "Clothing"},
        ],
        "processor": "klarna",
        "cookie_names": ["asos_session", "asos_cart", "asos_country"],
        "localStorage_keys": ["asos-bag", "asos-savedItems", "asos-locale"],
    },
    # ── Grocery & Convenience ─────────────────────────────────────────
    "instacart.com": {
        "name": "Instacart",
        "order_prefix": "IC",
        "order_format": "{prefix}-{seg1}",
        "items_pool": [
            {"name": "Organic Bananas (bunch)", "price": 2.49, "category": "Grocery"},
            {"name": "Whole Milk 1 Gallon", "price": 4.99, "category": "Grocery"},
            {"name": "Rotisserie Chicken", "price": 8.99, "category": "Grocery"},
            {"name": "Mixed Greens Salad Kit", "price": 4.49, "category": "Grocery"},
        ],
        "processor": "square",
        "cookie_names": ["ic_session", "ic_cart", "ic_zip"],
        "localStorage_keys": ["ic-address", "ic-recent-stores"],
    },
}

# Confirmation email subject templates
EMAIL_SUBJECTS = {
    "amazon.com": "Your Amazon.com order #{order_id} has been {status}",
    "walmart.com": "Your Walmart order #{order_id} - {status}",
    "bestbuy.com": "Best Buy Order Confirmation #{order_id}",
    "target.com": "Your Target order #{order_id} is {status}",
    "newegg.com": "Newegg Order #{order_id} Confirmation",
    "ebay.com": "eBay: Order #{order_id} confirmed",
    "steampowered.com": "Thank you for your Steam purchase!",
    "eneba.com": "Your Eneba order #{order_id} - Digital delivery",
    "g2a.com": "G2A Order #{order_id} - Product delivered",
    "fashionnova.com": "Fashion Nova Order #{order_id} Confirmed!",
    "gymshark.com": "Gymshark: Your order #{order_id} is confirmed",
    "spotify.com": "Spotify receipt - Payment confirmed",
    "netflix.com": "Netflix - Payment receipt",
    "doordash.com": "DoorDash: Order #{order_id} confirmed",
    "ubereats.com": "Uber Eats: Your order #{order_id} is on its way",
    "nike.com": "Nike Order #{order_id} Confirmation",
    "zara.com": "ZARA - Order Confirmation #{order_id}",
    "shein.com": "SHEIN Order #{order_id} - Confirmed",
    "etsy.com": "Receipt from Etsy: Order #{order_id}",
    "wayfair.com": "Wayfair Order #{order_id} Confirmed",
    "asos.com": "ASOS: Order #{order_id} confirmed",
    "instacart.com": "Instacart: Your delivery order #{order_id}",
}


# ═══════════════════════════════════════════════════════════════════════════
# PURCHASE HISTORY ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class PurchaseHistoryEngine:
    """
    Generates realistic purchase history with CC holder data and
    injects it into browser profiles for antifraud trust building.
    
    The engine creates:
    1. Order records in IndexedDB / localStorage
    2. Commerce cookies with aged timestamps
    3. Confirmation "email" artifacts in browser storage
    4. Payment processor trust tokens (pre-aged)
    5. Autofill entries matching CC holder data
    6. Cached merchant page assets for profile size
    """
    
    def __init__(self, profile_path: Path):
        self.profile_path = profile_path
        self.profile_path.mkdir(parents=True, exist_ok=True)
    
    def generate(self, config: PurchaseHistoryConfig) -> Dict[str, Any]:
        """
        Generate complete purchase history and inject into profile.
        
        Returns:
            Summary dict with counts and total amounts
        """
        logger.info(f"[*] Generating purchase history for {config.cardholder.full_name}")
        
        # 1. Generate purchase records
        records = self._generate_purchase_records(config)
        
        # 2. Write purchase database
        self._write_purchase_database(records, config)
        
        # 3. Inject commerce cookies
        cookie_count = self._inject_commerce_cookies(records, config)
        
        # 4. Inject localStorage commerce data
        ls_count = self._inject_commerce_localstorage(records, config)
        
        # 5. Generate confirmation email artifacts
        email_count = self._generate_email_artifacts(records, config)
        
        # 6. Inject payment processor trust tokens
        token_count = self._inject_payment_tokens(config)
        
        # 7. Inject autofill data with CC holder info
        self._inject_autofill_data(config)
        
        # 8. Generate cached merchant assets for profile size
        cache_size = self._generate_merchant_cache(records, config)
        
        # 9. Write purchase history metadata
        self._write_metadata(records, config)
        
        total_spent = sum(r.amount for r in records if r.status != OrderStatus.PROCESSING)
        
        summary = {
            "total_purchases": len(records),
            "total_spent": round(total_spent, 2),
            "merchants": list(set(r.merchant for r in records)),
            "cookies_injected": cookie_count,
            "localstorage_entries": ls_count,
            "email_artifacts": email_count,
            "trust_tokens": token_count,
            "cache_size_mb": round(cache_size / (1024 * 1024), 1),
            "cardholder": config.cardholder.full_name,
        }
        
        logger.info(f"[+] Purchase history complete: {len(records)} orders, ${total_spent:.2f} total")
        return summary
    
    # ─── PURCHASE RECORD GENERATION ───────────────────────────────────
    
    def _generate_purchase_records(self, config: PurchaseHistoryConfig) -> List[PurchaseRecord]:
        """Generate realistic purchase records spread over profile lifetime"""
        records = []
        base_time = datetime.now()
        
        # Determine merchants to use
        if config.target_merchants:
            merchants = [m for m in config.target_merchants if m in MERCHANT_TEMPLATES]
        else:
            merchants = list(MERCHANT_TEMPLATES.keys())
        
        # Spread purchases over profile age with realistic timing
        # First purchase 70-90% through the profile age (recent-ish)
        # Build up frequency toward present
        purchase_days = self._generate_purchase_schedule(
            config.profile_age_days, config.num_purchases
        )
        
        for i, days_ago in enumerate(purchase_days):
            merchant_key = merchants[i % len(merchants)]
            template = MERCHANT_TEMPLATES[merchant_key]
            
            # Pick items
            num_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            items = random.sample(template["items_pool"], min(num_items, len(template["items_pool"])))
            amount = sum(item["price"] for item in items)
            
            # Clamp amount
            if amount < config.min_amount:
                amount = config.min_amount + random.uniform(0, 10)
            if amount > config.max_amount:
                amount = config.max_amount - random.uniform(0, 20)
            
            order_date = base_time - timedelta(days=days_ago, hours=random.randint(9, 22),
                                                minutes=random.randint(0, 59))
            
            # Delivery 2-7 days after order for physical, instant for digital
            is_digital = merchant_key in ("steampowered.com", "eneba.com", "g2a.com")
            if is_digital:
                delivery_date = order_date + timedelta(minutes=random.randint(1, 15))
            else:
                delivery_date = order_date + timedelta(days=random.randint(2, 7))
            
            # Status based on age
            if days_ago > 5:
                status = OrderStatus.DELIVERED
            elif days_ago > 2:
                status = OrderStatus.SHIPPED
            else:
                status = OrderStatus.CONFIRMED
            
            # One failed attempt for realism
            if config.include_failed_attempt and i == config.num_purchases - 2:
                status = OrderStatus.PROCESSING
                delivery_date = None
            
            record = PurchaseRecord(
                merchant=template["name"],
                merchant_domain=merchant_key,
                order_id=self._generate_order_id(template),
                amount=round(amount, 2),
                currency="USD",
                items=[{"name": it["name"], "price": it["price"], "qty": 1} for it in items],
                status=status,
                payment_method=PaymentMethod.CREDIT_CARD,
                card_last_four=config.cardholder.card_last_four,
                order_date=order_date,
                delivery_date=delivery_date,
                shipping_address=config.cardholder.billing_line,
                confirmation_email_id=secrets.token_hex(16),
            )
            records.append(record)
        
        return records
    
    def _generate_purchase_schedule(self, age_days: int, num_purchases: int) -> List[int]:
        """Generate realistic purchase day offsets (more recent = more frequent)"""
        days = []
        # First purchase at 70-85% of profile age
        first_purchase_day = int(age_days * random.uniform(0.70, 0.85))
        
        if num_purchases <= 1:
            return [first_purchase_day]
        
        # Distribute remaining purchases with increasing frequency
        remaining_days = first_purchase_day
        gap_reduction = remaining_days / (num_purchases * 1.5)
        
        current_day = first_purchase_day
        for i in range(num_purchases):
            days.append(max(1, int(current_day)))
            gap = max(3, int(gap_reduction * (num_purchases - i)))
            current_day -= gap + random.randint(-2, 2)
        
        days.sort(reverse=True)
        return days[:num_purchases]
    
    def _generate_order_id(self, template: Dict) -> str:
        """Generate merchant-specific order ID"""
        fmt = template["order_format"]
        return fmt.format(
            prefix=template["order_prefix"],
            seg1=str(random.randint(1000000, 9999999)),
            seg2=str(random.randint(1000000, 9999999)),
        )
    
    # ─── DATABASE INJECTION ───────────────────────────────────────────
    
    def _write_purchase_database(self, records: List[PurchaseRecord], 
                                  config: PurchaseHistoryConfig):
        """Write purchase records to profile's IndexedDB storage"""
        idb_dir = self.profile_path / "storage" / "default"
        
        for record in records:
            domain_dir = idb_dir / f"https+++www.{record.merchant_domain}" / "idb"
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            db_file = domain_dir / "order_history.sqlite"
            conn = _fx_sqlite(db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    order_id TEXT UNIQUE,
                    merchant TEXT,
                    amount REAL,
                    currency TEXT,
                    items TEXT,
                    status TEXT,
                    payment_method TEXT,
                    card_last_four TEXT,
                    order_date TEXT,
                    delivery_date TEXT,
                    shipping_address TEXT,
                    created_at INTEGER
                )
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO orders 
                (order_id, merchant, amount, currency, items, status, payment_method,
                 card_last_four, order_date, delivery_date, shipping_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.order_id,
                record.merchant,
                record.amount,
                record.currency,
                json.dumps(record.items),
                record.status.value,
                record.payment_method.value,
                record.card_last_four,
                record.order_date.isoformat(),
                record.delivery_date.isoformat() if record.delivery_date else None,
                record.shipping_address,
                int(record.order_date.timestamp()),
            ))
            
            conn.commit()
            conn.close()
        
        logger.info(f"[+] Purchase DB: {len(records)} order records written")
    
    # ─── COMMERCE COOKIES ─────────────────────────────────────────────
    
    def _inject_commerce_cookies(self, records: List[PurchaseRecord],
                                  config: PurchaseHistoryConfig) -> int:
        """Inject aged commerce cookies for each merchant visited"""
        cookies_db = self.profile_path / "cookies.sqlite"
        conn = _fx_sqlite(cookies_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_cookies (
                id INTEGER PRIMARY KEY,
                originAttributes TEXT DEFAULT '',
                name TEXT,
                value TEXT,
                host TEXT,
                path TEXT DEFAULT '/',
                expiry INTEGER,
                lastAccessed INTEGER,
                creationTime INTEGER,
                isSecure INTEGER DEFAULT 1,
                isHttpOnly INTEGER DEFAULT 1,
                inBrowserElement INTEGER DEFAULT 0,
                sameSite INTEGER DEFAULT 0,
                rawSameSite INTEGER DEFAULT 0,
                schemeMap INTEGER DEFAULT 0
            )
        """)
        
        cookie_count = 0
        base_time = datetime.now()
        
        # Get existing max ID
        cursor.execute("SELECT MAX(id) FROM moz_cookies")
        row = cursor.fetchone()
        next_id = (row[0] or 0) + 1
        
        seen_merchants = set()
        for record in records:
            domain = record.merchant_domain
            if domain in seen_merchants:
                continue
            seen_merchants.add(domain)
            
            template = MERCHANT_TEMPLATES.get(domain, {})
            creation = record.order_date - timedelta(days=random.randint(5, 30))
            
            # Merchant session cookies
            for cookie_name in template.get("cookie_names", []):
                cursor.execute("""
                    INSERT INTO moz_cookies 
                    (id, name, value, host, expiry, lastAccessed, creationTime, isSecure, isHttpOnly)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    next_id,
                    cookie_name,
                    secrets.token_hex(random.randint(16, 48)),
                    f".{domain}",
                    int((base_time + timedelta(days=365)).timestamp()),
                    int(base_time.timestamp() * 1000000),
                    int(creation.timestamp() * 1000000),
                    1, 1
                ))
                next_id += 1
                cookie_count += 1
            
            # Payment processor cookies based on merchant — multi-PSP realistic injection
            processor = template.get("processor", "stripe")
            psp_cookies = self._get_psp_cookies(processor, config, creation)
            for cname, cval, chost in psp_cookies:
                cursor.execute("""
                    INSERT INTO moz_cookies 
                    (id, name, value, host, expiry, lastAccessed, creationTime, isSecure, isHttpOnly)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (next_id, cname, cval, chost,
                      int((base_time + timedelta(days=365)).timestamp()),
                      int(base_time.timestamp() * 1000000),
                      int(creation.timestamp() * 1000000), 1, 0))
                next_id += 1
                cookie_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"[+] Commerce cookies: {cookie_count} injected")
        return cookie_count
    
    # ─── LOCALSTORAGE COMMERCE DATA ───────────────────────────────────
    
    def _inject_commerce_localstorage(self, records: List[PurchaseRecord],
                                       config: PurchaseHistoryConfig) -> int:
        """Inject localStorage entries for commerce sites"""
        storage_dir = self.profile_path / "storage" / "default"
        entry_count = 0
        
        seen = set()
        for record in records:
            domain = record.merchant_domain
            if domain in seen:
                continue
            seen.add(domain)
            
            template = MERCHANT_TEMPLATES.get(domain, {})
            domain_dir = storage_dir / f"https+++www.{domain}"
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            ls_db = domain_dir / "ls" / "data.sqlite"
            ls_db.parent.mkdir(parents=True, exist_ok=True)
            
            conn = _fx_sqlite(ls_db)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data (
                    key TEXT PRIMARY KEY,
                    utf16Length INTEGER NOT NULL DEFAULT 0,
                    compressed INTEGER NOT NULL DEFAULT 0,
                    lastAccessTime INTEGER NOT NULL DEFAULT 0,
                    value BLOB NOT NULL
                )
            """)
            
            # Inject merchant-specific localStorage keys
            for key in template.get("localStorage_keys", []):
                value = json.dumps({
                    "ts": int(record.order_date.timestamp() * 1000),
                    "data": secrets.token_hex(32),
                    "version": random.randint(1, 5),
                })
                la_time = int(datetime.now().timestamp() * 1e6)
                cursor.execute("""
                    INSERT OR REPLACE INTO data (key, value, utf16Length, lastAccessTime)
                    VALUES (?, ?, ?, ?)
                """, (key, value, len(value), la_time))
                entry_count += 1
            
            # Inject purchase-specific data (use realistic key name, not synthetic)
            order_data = json.dumps({
                "lastOrder": record.order_id,
                "lastAmount": record.amount,
                "lastDate": record.order_date.isoformat(),
                "cardLast4": record.card_last_four,
                "status": record.status.value,
            })
            la_time = int(record.order_date.timestamp() * 1e6)
            cursor.execute("""
                INSERT OR REPLACE INTO data (key, value, utf16Length, lastAccessTime)
                VALUES (?, ?, ?, ?)
            """, ("persist:orderHistory", order_data, len(order_data), la_time))
            entry_count += 1
            
            conn.commit()
            conn.close()
        
        logger.info(f"[+] Commerce localStorage: {entry_count} entries")
        return entry_count
    
    # ─── EMAIL ARTIFACTS ──────────────────────────────────────────────
    
    def _generate_email_artifacts(self, records: List[PurchaseRecord],
                                   config: PurchaseHistoryConfig) -> int:
        """Generate order confirmation email artifacts in profile storage"""
        email_dir = self.profile_path / "email_artifacts"
        email_dir.mkdir(parents=True, exist_ok=True)
        
        for record in records:
            subject_template = EMAIL_SUBJECTS.get(
                record.merchant_domain, "Order #{order_id} - {status}"
            )
            subject = subject_template.format(
                order_id=record.order_id,
                status=record.status.value,
            )
            
            email_data = {
                "id": record.confirmation_email_id,
                "from": f"no-reply@{record.merchant_domain}",
                "to": config.cardholder.email,
                "subject": subject,
                "date": record.order_date.isoformat(),
                "merchant": record.merchant,
                "order_id": record.order_id,
                "amount": f"${record.amount:.2f}",
                "items": record.items,
                "shipping_to": config.cardholder.full_name,
                "shipping_address": record.shipping_address,
                "payment": f"{config.cardholder.card_network.upper()} ending in {record.card_last_four}",
                "status": record.status.value,
            }
            
            email_file = email_dir / f"{record.confirmation_email_id}.json"
            with open(email_file, "w") as f:
                json.dump(email_data, f, indent=2)
        
        logger.info(f"[+] Email artifacts: {len(records)} confirmations")
        return len(records)
    
    # ─── PAYMENT TRUST TOKENS ─────────────────────────────────────────
    
    def _inject_payment_tokens(self, config: PurchaseHistoryConfig) -> int:
        """Inject pre-aged payment processor trust tokens"""
        tokens_file = self.profile_path / "commerce_tokens.json"
        
        base_time = datetime.now()
        first_purchase = base_time - timedelta(days=int(config.profile_age_days * 0.8))
        
        # Load existing tokens if present
        existing = {}
        if tokens_file.exists():
            with open(tokens_file, "r") as f:
                existing = json.load(f)
        
        # Collect which PSPs this profile actually used from merchant history
        used_psps = set()
        for domain in MERCHANT_TEMPLATES:
            used_psps.add(MERCHANT_TEMPLATES[domain].get("processor", "stripe"))
        
        # Generate trust tokens for every PSP the profile has interacted with
        tokens = {**existing}
        card_fp = hashlib.sha256(
            f"{config.cardholder.card_last_four}:{config.cardholder.full_name}".encode()
        ).hexdigest()[:24]
        
        if "stripe" in used_psps:
            tokens["stripe"] = {
                "__stripe_mid": self._generate_stripe_mid(config, first_purchase),
                "__stripe_sid": self._generate_stripe_sid(),
                "created_at": first_purchase.isoformat(),
                "age_days": config.profile_age_days,
                "card_fingerprint": card_fp,
            }
        if "paypal" in used_psps:
            tokens["paypal"] = {
                "TLTSID": secrets.token_hex(32),
                "ts": secrets.token_hex(16),
                "x-pp-s": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "adyen" in used_psps:
            tokens["adyen"] = {
                "_RP_UID": secrets.token_hex(24),
                "adyen-device-fingerprint": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "braintree" in used_psps:
            tokens["braintree"] = {
                "device_id": self._generate_uuid_v4(),
                "correlation_id": self._generate_uuid_v4(),
                "created_at": first_purchase.isoformat(),
            }
        if "shopify_payments" in used_psps:
            tokens["shopify"] = {
                "_shopify_y": secrets.token_hex(32),
                "_shopify_sa_t": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "klarna" in used_psps:
            tokens["klarna"] = {
                "client_id": self._generate_uuid_v4(),
                "session": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "square" in used_psps:
            tokens["square"] = {
                "device_id": self._generate_uuid_v4(),
                "created_at": first_purchase.isoformat(),
            }
        if "worldpay" in used_psps:
            tokens["worldpay"] = {
                "device_id": secrets.token_hex(32),
                "session_id": self._generate_uuid_v4(),
                "created_at": first_purchase.isoformat(),
            }
        if "cybersource" in used_psps:
            tokens["cybersource"] = {
                "dfp": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "checkout_com" in used_psps:
            tokens["checkout_com"] = {
                "cko-session-id": self._generate_uuid_v4(),
                "cko-device-id": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "amazon_pay" in used_psps:
            tokens["amazon_pay"] = {
                "at-main": secrets.token_hex(40),
                "created_at": first_purchase.isoformat(),
            }
        
        with open(tokens_file, "w") as f:
            json.dump(tokens, f, indent=2)
        
        logger.info(f"[+] Trust tokens: {len(tokens)} processors")
        return len(tokens)
    
    # ─── AUTOFILL DATA ────────────────────────────────────────────────
    
    def _inject_autofill_data(self, config: PurchaseHistoryConfig):
        """Inject CC holder autofill data into Firefox formhistory.sqlite"""
        ch = config.cardholder
        
        autofill_db = self.profile_path / "formhistory.sqlite"
        conn = _fx_sqlite(autofill_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_formhistory (
                id INTEGER PRIMARY KEY,
                fieldname TEXT,
                value TEXT,
                timesUsed INTEGER,
                firstUsed INTEGER,
                lastUsed INTEGER,
                guid TEXT
            )
        """)
        
        base_time = datetime.now()
        first_use = base_time - timedelta(days=int(config.profile_age_days * 0.75))
        
        autofill_entries = [
            ("name", ch.full_name, random.randint(5, 15)),
            ("first_name", ch.first_name, random.randint(5, 15)),
            ("last_name", ch.last_name, random.randint(5, 15)),
            ("given-name", ch.first_name, random.randint(3, 10)),
            ("family-name", ch.last_name, random.randint(3, 10)),
            ("email", ch.email, random.randint(8, 20)),
            ("tel", ch.phone, random.randint(3, 8)),
            ("address-line1", ch.billing_address, random.randint(4, 12)),
            ("address-level2", ch.billing_city, random.randint(4, 12)),
            ("address-level1", ch.billing_state, random.randint(4, 12)),
            ("postal-code", ch.billing_zip, random.randint(4, 12)),
            ("country", ch.billing_country, random.randint(4, 12)),
            ("cc-name", ch.full_name, random.randint(3, 8)),
            ("cc-number", f"****{ch.card_last_four}", 0),  # Never store full PAN
            ("cc-exp", ch.card_exp_display, random.randint(2, 5)),
            ("cc-type", ch.card_network, random.randint(2, 5)),
            ("organization", "", 0),
        ]
        
        for fieldname, value, times_used in autofill_entries:
            if not value:
                continue
            cursor.execute("""
                INSERT OR REPLACE INTO moz_formhistory 
                (fieldname, value, timesUsed, firstUsed, lastUsed, guid)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                fieldname, value, times_used,
                int(first_use.timestamp() * 1000000),
                int(base_time.timestamp() * 1000000),
                secrets.token_hex(8),
            ))
        
        # Also write address autofill
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_addresses (
                id INTEGER PRIMARY KEY,
                guid TEXT UNIQUE,
                given_name TEXT,
                family_name TEXT,
                street_address TEXT,
                address_level2 TEXT,
                address_level1 TEXT,
                postal_code TEXT,
                country TEXT,
                tel TEXT,
                email TEXT,
                timeCreated INTEGER,
                timeLastUsed INTEGER,
                timesUsed INTEGER
            )
        """)
        
        cursor.execute("""
            INSERT OR REPLACE INTO moz_addresses
            (guid, given_name, family_name, street_address, address_level2,
             address_level1, postal_code, country, tel, email,
             timeCreated, timeLastUsed, timesUsed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            secrets.token_hex(8),
            ch.first_name, ch.last_name,
            ch.billing_address, ch.billing_city,
            ch.billing_state, ch.billing_zip, ch.billing_country,
            ch.phone, ch.email,
            int(first_use.timestamp() * 1000),
            int(base_time.timestamp() * 1000),
            random.randint(5, 15),
        ))
        
        # Credit card autofill (Firefox stores encrypted, we store metadata)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_creditcards (
                id INTEGER PRIMARY KEY,
                guid TEXT UNIQUE,
                cc_name TEXT,
                cc_number_last4 TEXT,
                cc_exp_month INTEGER,
                cc_exp_year INTEGER,
                cc_type TEXT,
                timeCreated INTEGER,
                timeLastUsed INTEGER,
                timesUsed INTEGER
            )
        """)
        
        exp_parts = ch.card_exp_display.split("/")
        exp_month = int(exp_parts[0]) if len(exp_parts) >= 1 else 12
        exp_year = int(exp_parts[1]) + 2000 if len(exp_parts) >= 2 else 2027
        
        cursor.execute("""
            INSERT OR REPLACE INTO moz_creditcards
            (guid, cc_name, cc_number_last4, cc_exp_month, cc_exp_year, cc_type,
             timeCreated, timeLastUsed, timesUsed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            secrets.token_hex(8),
            ch.full_name, ch.card_last_four,
            exp_month, exp_year, ch.card_network,
            int(first_use.timestamp() * 1000),
            int(base_time.timestamp() * 1000),
            random.randint(3, 8),
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[+] Autofill data: name, address, card for {ch.full_name}")
    
    # ─── MERCHANT CACHE ───────────────────────────────────────────────
    
    def _generate_merchant_cache(self, records: List[PurchaseRecord],
                                  config: PurchaseHistoryConfig) -> int:
        """Generate cached merchant page assets to bulk up profile size"""
        cache_dir = self.profile_path / "cache2" / "entries"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        total_size = 0
        target_bytes = 50 * 1024 * 1024  # 50MB of merchant cache
        
        seen_merchants = set()
        for record in records:
            if record.merchant_domain in seen_merchants:
                continue
            seen_merchants.add(record.merchant_domain)
            
            # Generate per-merchant cached assets
            merchant_cache = cache_dir / record.merchant_domain
            merchant_cache.mkdir(parents=True, exist_ok=True)
            
            per_merchant = target_bytes // max(len(seen_merchants), 1)
            merchant_size = 0
            
            while merchant_size < per_merchant:
                # Simulate cached JS/CSS/image files
                file_hash = secrets.token_hex(20)
                file_size = random.randint(10 * 1024, 500 * 1024)
                
                cache_file = merchant_cache / file_hash
                with open(cache_file, "wb") as f:
                    f.write(os.urandom(file_size))
                
                merchant_size += file_size
                total_size += file_size
                
                if total_size >= target_bytes:
                    break
        
        logger.info(f"[+] Merchant cache: {total_size / (1024*1024):.1f} MB")
        return total_size
    
    # ─── METADATA ─────────────────────────────────────────────────────
    
    def _write_metadata(self, records: List[PurchaseRecord],
                        config: PurchaseHistoryConfig):
        """Write purchase history metadata for operator reference"""
        meta_file = self.profile_path / "purchase_history.json"
        
        metadata = {
            "cardholder": {
                "name": config.cardholder.full_name,
                "email": config.cardholder.email,
                "billing": config.cardholder.billing_line,
                "card_last_four": config.cardholder.card_last_four,
                "card_network": config.cardholder.card_network,
            },
            "orders": [
                {
                    "merchant": r.merchant,
                    "order_id": r.order_id,
                    "amount": r.amount,
                    "items": r.items,
                    "status": r.status.value,
                    "date": r.order_date.isoformat(),
                    "card_last_four": r.card_last_four,
                }
                for r in records
            ],
            "generated_at": datetime.now().isoformat(),
        }
        
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)
    
    # ─── MULTI-PSP COOKIE GENERATOR ──────────────────────────────────
    
    def _get_psp_cookies(self, processor: str, config: PurchaseHistoryConfig,
                          creation: datetime) -> List[tuple]:
        """Generate PSP-specific cookies as (name, value, host) tuples.
        
        Real users interact with 10+ different PSPs across their purchase
        history. Each PSP sets distinct tracking/device cookies.
        """
        cookies = []
        
        if processor == "stripe":
            cookies.append(("__stripe_mid", self._generate_stripe_mid(config, creation), ".stripe.com"))
            cookies.append(("__stripe_sid", self._generate_stripe_sid(), ".stripe.com"))
        
        elif processor == "paypal":
            cookies.append(("TLTSID", secrets.token_hex(32), ".paypal.com"))
            cookies.append(("ts", secrets.token_hex(16), ".paypal.com"))
            cookies.append(("tsrce", f"devmemoryauthsvc{secrets.token_hex(4)}", ".paypal.com"))
            cookies.append(("x-pp-s", secrets.token_hex(32), ".paypal.com"))
        
        elif processor == "adyen":
            cookies.append(("adyen-device-fingerprint", secrets.token_hex(32), ".adyen.com"))
            cookies.append(("_RP_UID", secrets.token_hex(24), ".adyen.com"))
        
        elif processor == "braintree":
            bt_id = self._generate_uuid_v4()
            cookies.append(("_braintree_device_id", bt_id, ".braintreegateway.com"))
            cookies.append(("_bt_devicedata", json.dumps({"correlation_id": bt_id}), ".braintreegateway.com"))
        
        elif processor == "shopify_payments":
            cookies.append(("_shopify_sa_t", secrets.token_hex(32), ".shopify.com"))
            cookies.append(("_shopify_y", secrets.token_hex(32), ".shopify.com"))
            cookies.append(("_shopify_s", secrets.token_hex(32), ".shopify.com"))
        
        elif processor == "klarna":
            cookies.append(("klarna_client_id", self._generate_uuid_v4(), ".klarna.com"))
            cookies.append(("klarna_session", secrets.token_hex(32), ".klarna.com"))
        
        elif processor == "square":
            cookies.append(("_sq_device_id", self._generate_uuid_v4(), ".squareup.com"))
            cookies.append(("_sq_session", secrets.token_hex(32), ".squareup.com"))
        
        elif processor == "worldpay":
            cookies.append(("_wp_device", secrets.token_hex(32), ".worldpay.com"))
            cookies.append(("_wp_session_id", self._generate_uuid_v4(), ".worldpay.com"))
        
        elif processor == "cybersource":
            cookies.append(("_cs_dfp", secrets.token_hex(32), ".cybersource.com"))
            cookies.append(("_cs_s", secrets.token_hex(24), ".cybersource.com"))
        
        elif processor == "amazon_pay":
            cookies.append(("at-main", secrets.token_hex(40), ".amazon.com"))
            cookies.append(("sess-at-main", f'"{secrets.token_hex(32)}"', ".amazon.com"))
            cookies.append(("sst-main", secrets.token_hex(40), ".amazon.com"))
        
        elif processor == "checkout_com":
            cookies.append(("cko-session-id", self._generate_uuid_v4(), ".checkout.com"))
            cookies.append(("cko-device-id", secrets.token_hex(32), ".checkout.com"))
        
        return cookies
    
    # ─── HELPERS ──────────────────────────────────────────────────────
    
    @staticmethod
    def _generate_uuid_v4() -> str:
        """Generate a standard UUID v4."""
        b = bytearray(secrets.token_bytes(16))
        b[6] = (b[6] & 0x0F) | 0x40
        b[8] = (b[8] & 0x3F) | 0x80
        h = bytes(b).hex()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    
    def _generate_stripe_mid(self, config: PurchaseHistoryConfig,
                              creation_time: datetime) -> str:
        """Generate __stripe_mid as UUID v4 (real Stripe format).
        
        V7.5 PATCH: Real __stripe_mid is a standard UUID v4:
        xxxxxxxx-xxxx-4xxx-Nxxx-xxxxxxxxxxxx
        Old format (hash.timestamp.random) was flagged by Stripe Radar.
        """
        seed = hashlib.sha256(
            f"{config.cardholder.full_name}:{config.cardholder.card_last_four}:{int(creation_time.timestamp())}".encode()
        ).digest()
        b = bytearray(seed[:16])
        b[6] = (b[6] & 0x0F) | 0x40  # version 4
        b[8] = (b[8] & 0x3F) | 0x80  # variant 1
        h = bytes(b).hex()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    
    @staticmethod
    def _generate_stripe_sid() -> str:
        """Generate __stripe_sid as UUID v4 (real Stripe format)."""
        b = bytearray(secrets.token_bytes(16))
        b[6] = (b[6] & 0x0F) | 0x40
        b[8] = (b[8] & 0x3F) | 0x80
        h = bytes(b).hex()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def inject_purchase_history(
    profile_path: str,
    full_name: str,
    email: str,
    card_last_four: str,
    card_network: str,
    card_exp: str,
    billing_address: str,
    billing_city: str,
    billing_state: str,
    billing_zip: str,
    phone: str = "",
    num_purchases: int = 8,
    profile_age_days: int = 95,
    target_merchants: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to inject purchase history into an existing profile.
    
    Returns summary dict with counts and totals.
    """
    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    
    cardholder = CardHolderData(
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        card_last_four=card_last_four,
        card_network=card_network,
        card_exp_display=card_exp,
        billing_address=billing_address,
        billing_city=billing_city,
        billing_state=billing_state,
        billing_zip=billing_zip,
        email=email,
        phone=phone,
    )
    
    config = PurchaseHistoryConfig(
        cardholder=cardholder,
        profile_age_days=profile_age_days,
        num_purchases=num_purchases,
        target_merchants=target_merchants,
    )
    
    engine = PurchaseHistoryEngine(Path(profile_path))
    return engine.generate(config)
