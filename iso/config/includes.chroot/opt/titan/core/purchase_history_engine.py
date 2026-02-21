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
        
        # Initialize Multi-PSP Processor for diverse payment processor integration
        multi_psp = MultiPSPProcessor(profile_age_days=config.profile_age_days)
        logger.info(f"[+] Multi-PSP Processor initialized with {len(multi_psp.selected_processors)} processors")
        
        # 1. Generate purchase records
        records = self._generate_purchase_records(config)
        
        # 2. Distribute transactions across processors
        transaction_distribution = multi_psp._distribute_transactions(len(records))
        
        # 3. Write purchase database
        self._write_purchase_database(records, config)
        
        # 4. Inject commerce cookies
        cookie_count = self._inject_commerce_cookies(records, config)
        
        # 5. Inject localStorage commerce data
        ls_count = self._inject_commerce_localstorage(records, config)
        
        # 6. Generate confirmation email artifacts
        email_count = self._generate_email_artifacts(records, config)
        
        # 7. Inject payment processor trust tokens (using diversified processors)
        token_count = self._inject_payment_tokens(config, multi_psp)
        
        # 8. Inject autofill data with CC holder info
        self._inject_autofill_data(config)
        
        # 9. Generate cached merchant assets for profile size
        cache_size = self._generate_merchant_cache(records, config)
        
        # V7.6: P0 Critical Components for Maximum Operational Success
        try:
            # 10. Refund/return history (authenticity marker)
            refund_count = self._generate_refund_history(records, config)
            
            # 11. Subscription history (trust builder)
            subscription_count = self._generate_subscription_history(records, config)
            
            # 12. Review history (engagement marker)
            review_count = self._generate_review_history(records, config)
            
            # 13. Loyalty rewards (long-term relationship marker)
            loyalty_count = self._generate_loyalty_rewards(records, config)
            
            logger.info(f"[V7.6] P0 components: {refund_count} refunds, {subscription_count} subs, {review_count} reviews, {loyalty_count} loyalty programs")
        except Exception as exc:
            logger.warning(f"[V7.6] P0 component generation partial: {exc}")
            refund_count = subscription_count = review_count = loyalty_count = 0
        
        # 14. Write purchase history metadata
        self._write_metadata(records, config)
        
        total_spent = sum(r.amount for r in records if r.status != OrderStatus.PROCESSING)
        
        # Get Multi-PSP processor statistics
        psp_stats = multi_psp.get_processor_statistics()
        
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
            "payment_processors": psp_stats["processor_count"],
            "processor_diversity_score": psp_stats["diversity_score"],
            "processor_coverage": psp_stats["coverage_percentage"],
            "selected_processors": psp_stats["selected_processors"],
            "transaction_distribution": transaction_distribution,
            "refunds": refund_count,
            "subscriptions": subscription_count,
            "reviews": review_count,
            "loyalty_programs": loyalty_count,
        }
        
        logger.info(f"[+] Purchase history complete: {len(records)} orders, ${total_spent:.2f} total, {psp_stats['processor_count']} processors")
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
            # V7.5 FIX: Real Firefox LSNG stores values as UTF-16LE BLOBs
            for key in template.get("localStorage_keys", []):
                value_str = json.dumps({
                    "ts": int(record.order_date.timestamp() * 1000),
                    "data": secrets.token_hex(32),
                    "version": random.randint(1, 5),
                })
                utf16_chars = len(value_str)
                value_blob = struct.pack("<I", utf16_chars) + value_str.encode("utf-16-le")
                la_time = int(datetime.now().timestamp() * 1e6)
                cursor.execute("""
                    INSERT OR REPLACE INTO data (key, value, utf16Length, lastAccessTime)
                    VALUES (?, ?, ?, ?)
                """, (key, value_blob, utf16_chars, la_time))
                entry_count += 1
            
            # Inject purchase-specific data (use realistic key name, not synthetic)
            order_str = json.dumps({
                "lastOrder": record.order_id,
                "lastAmount": record.amount,
                "lastDate": record.order_date.isoformat(),
                "cardLast4": record.card_last_four,
                "status": record.status.value,
            })
            utf16_chars = len(order_str)
            order_blob = struct.pack("<I", utf16_chars) + order_str.encode("utf-16-le")
            la_time = int(record.order_date.timestamp() * 1e6)
            cursor.execute("""
                INSERT OR REPLACE INTO data (key, value, utf16Length, lastAccessTime)
                VALUES (?, ?, ?, ?)
            """, ("persist:orderHistory", order_blob, utf16_chars, la_time))
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
    
    def _inject_payment_tokens(self, config: PurchaseHistoryConfig, multi_psp: Optional[MultiPSPProcessor] = None) -> int:
        """Inject pre-aged payment processor trust tokens with diverse processor support"""
        tokens_file = self.profile_path / "commerce_tokens.json"
        
        base_time = datetime.now()
        first_purchase = base_time - timedelta(days=int(config.profile_age_days * 0.8))
        
        # Load existing tokens if present
        existing = {}
        if tokens_file.exists():
            with open(tokens_file, "r") as f:
                existing = json.load(f)
        
        # Use MultiPSPProcessor if available; otherwise fall back to merchant-based list
        if multi_psp:
            # Use selected processors from MultiPSPProcessor
            selected_processor_names = {p.name.lower().replace(" ", "_") for p in multi_psp.selected_processors}
        else:
            # Collect which PSPs this profile actually used from merchant history
            selected_processor_names = set()
            for domain in MERCHANT_TEMPLATES:
                selected_processor_names.add(MERCHANT_TEMPLATES[domain].get("processor", "stripe"))
        
        # Generate trust tokens for every PSP the profile has interacted with
        tokens = {**existing}
        card_fp = hashlib.sha256(
            f"{config.cardholder.card_last_four}:{config.cardholder.full_name}".encode()
        ).hexdigest()[:24]
        
        if "stripe" in selected_processor_names:
            tokens["stripe"] = {
                "__stripe_mid": self._generate_stripe_mid(config, first_purchase),
                "__stripe_sid": self._generate_stripe_sid(),
                "created_at": first_purchase.isoformat(),
                "age_days": config.profile_age_days,
                "card_fingerprint": card_fp,
            }
        if "paypal" in selected_processor_names:
            tokens["paypal"] = {
                "TLTSID": secrets.token_hex(32),
                "ts": secrets.token_hex(16),
                "x-pp-s": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "adyen" in selected_processor_names:
            tokens["adyen"] = {
                "_RP_UID": secrets.token_hex(24),
                "adyen-device-fingerprint": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "braintree" in selected_processor_names:
            tokens["braintree"] = {
                "device_id": self._generate_uuid_v4(),
                "correlation_id": self._generate_uuid_v4(),
                "created_at": first_purchase.isoformat(),
            }
        if "shopify" in selected_processor_names:
            tokens["shopify"] = {
                "_shopify_y": secrets.token_hex(32),
                "_shopify_sa_t": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "klarna" in selected_processor_names:
            tokens["klarna"] = {
                "client_id": self._generate_uuid_v4(),
                "session": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "square" in selected_processor_names:
            tokens["square"] = {
                "device_id": self._generate_uuid_v4(),
                "created_at": first_purchase.isoformat(),
            }
        if "worldpay" in selected_processor_names:
            tokens["worldpay"] = {
                "device_id": secrets.token_hex(32),
                "session_id": self._generate_uuid_v4(),
                "created_at": first_purchase.isoformat(),
            }
        if "cybersource" in selected_processor_names:
            tokens["cybersource"] = {
                "dfp": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "checkout_com" in selected_processor_names or "checkout.com" in selected_processor_names:
            tokens["checkout.com"] = {
                "cko-session-id": self._generate_uuid_v4(),
                "cko-device-id": secrets.token_hex(32),
                "created_at": first_purchase.isoformat(),
            }
        if "amazon_pay" in selected_processor_names:
            tokens["amazon_pay"] = {
                "at-main": secrets.token_hex(40),
                "created_at": first_purchase.isoformat(),
            }
        
        # Add additional PSP tokens if using MultiPSPProcessor with Tier 3 processors
        if multi_psp:
            if "2checkout" in selected_processor_names:
                tokens["2checkout"] = {
                    "2co-session": secrets.token_hex(32),
                    "2co-device": secrets.token_hex(24),
                    "created_at": first_purchase.isoformat(),
                }
            if "gocardless" in selected_processor_names:
                tokens["gocardless"] = {
                    "gc-token": secrets.token_hex(32),
                    "gc-device": secrets.token_hex(24),
                    "created_at": first_purchase.isoformat(),
                }
            if "wise" in selected_processor_names:
                tokens["wise"] = {
                    "wise-token": secrets.token_hex(32),
                    "wise-device": secrets.token_hex(24),
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
                secrets.token_urlsafe(9)[:12],
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
            secrets.token_urlsafe(9)[:12],
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
            secrets.token_urlsafe(9)[:12],
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
                # V7.5 FIX: Add nsDiskCacheEntry 32-byte headers
                url = f"https://www.{record.merchant_domain}/assets/{secrets.token_hex(8)}"
                key_bytes = url.encode("ascii")
                body_size = random.randint(10 * 1024, 500 * 1024)
                base_ts = int(datetime.now().timestamp())
                age_s = random.randint(0, 86400 * 90)
                header = struct.pack("<IIIIIIII",
                    3, random.randint(1, 20), base_ts - age_s,
                    base_ts - age_s - random.randint(0, 3600),
                    random.randint(10, 5000), base_ts + 86400 * 365,
                    len(key_bytes), 0)
                meta = b"request-method: GET\r\nresponse-head: HTTP/1.1 200 OK\r\n"
                
                file_hash = hashlib.sha1(key_bytes).hexdigest()[:40]
                cache_file = merchant_cache / file_hash
                with open(cache_file, "wb") as f:
                    f.write(header)
                    f.write(key_bytes)
                    f.write(os.urandom(body_size))
                    f.write(struct.pack("<I", len(meta)))
                    f.write(meta)
                
                file_size = 32 + len(key_bytes) + body_size + 4 + len(meta)
                merchant_size += file_size
                total_size += file_size
                
                if total_size >= target_bytes:
                    break
        
        logger.info(f"[+] Merchant cache: {total_size / (1024*1024):.1f} MB")
        return total_size

    # ═══════════════════════════════════════════════════════════════════════════
    # V7.6 UPGRADE: P0 CRITICAL COMPONENTS FOR MAXIMUM OPERATIONAL SUCCESS
    # Refund History, Subscription Tracking, Review History, Loyalty Rewards
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_refund_history(self, records: List[PurchaseRecord],
                                  config: PurchaseHistoryConfig) -> int:
        """
        Generate realistic refund/return history.
        
        Real users return ~8-15% of online purchases. A profile with 100%
        successful orders is suspicious. Including canceled/returned orders
        shows authentic purchasing behavior.
        """
        if len(records) < 4:
            return 0  # Not enough orders to have returns
        
        refund_dir = self.profile_path / "refund_history"
        refund_dir.mkdir(parents=True, exist_ok=True)
        
        # Pick 1-2 orders to have been returned/refunded (10-15% rate)
        num_refunds = max(1, int(len(records) * random.uniform(0.08, 0.15)))
        refund_candidates = [r for r in records if r.status == OrderStatus.DELIVERED]
        
        if not refund_candidates:
            return 0
        
        refunded_orders = random.sample(refund_candidates, min(num_refunds, len(refund_candidates)))
        
        refunds = []
        for order in refunded_orders:
            # Refund 3-14 days after delivery
            refund_date = order.delivery_date + timedelta(days=random.randint(3, 14)) if order.delivery_date else order.order_date + timedelta(days=random.randint(10, 20))
            
            # Full or partial refund
            is_partial = random.random() < 0.3
            refund_amount = order.amount * random.uniform(0.3, 0.7) if is_partial else order.amount
            
            refund_record = {
                "refund_id": f"RF-{secrets.token_hex(8).upper()}",
                "original_order_id": order.order_id,
                "merchant": order.merchant,
                "merchant_domain": order.merchant_domain,
                "refund_amount": round(refund_amount, 2),
                "refund_type": "partial" if is_partial else "full",
                "reason": random.choice([
                    "Item not as described",
                    "Changed my mind",
                    "Found better price",
                    "Ordered wrong size",
                    "Duplicate order",
                ]),
                "refund_date": refund_date.isoformat(),
                "card_last_four": order.card_last_four,
                "status": "completed",
            }
            refunds.append(refund_record)
        
        # Write refund database
        with open(refund_dir / "refund_records.json", "w") as f:
            json.dump(refunds, f, indent=2)
        
        logger.info(f"[V7.6] Refund history: {len(refunds)} returns/refunds generated")
        return len(refunds)

    def _generate_subscription_history(self, records: List[PurchaseRecord],
                                        config: PurchaseHistoryConfig) -> int:
        """
        Generate subscription/recurring payment history.
        
        Recurring payments show stable, trustworthy behavior. Antifraud
        systems treat profiles with subscription history as lower risk.
        """
        subscription_dir = self.profile_path / "subscription_history"
        subscription_dir.mkdir(parents=True, exist_ok=True)
        
        # Find subscription-based merchants
        subscription_merchants = ["spotify.com", "netflix.com", "doordash.com", "ubereats.com"]
        active_subs = [r for r in records if r.merchant_domain in subscription_merchants]
        
        subscriptions = []
        base_time = datetime.now()
        
        # Generate 1-3 subscription records
        num_subs = random.randint(1, min(3, len(active_subs) + 1))
        
        for i in range(num_subs):
            # Pick a subscription service
            service = random.choice(["Spotify Premium", "Netflix Standard", "Amazon Prime", 
                                     "YouTube Premium", "DoorDash DashPass", "Instacart+"])
            
            # Started 2-6 months ago
            start_date = base_time - timedelta(days=random.randint(60, 180))
            
            # Generate payment history
            payments = []
            current_date = start_date
            while current_date < base_time:
                payments.append({
                    "date": current_date.isoformat(),
                    "amount": round(random.uniform(9.99, 22.99), 2),
                    "status": "completed",
                    "card_last_four": config.cardholder.card_last_four,
                })
                current_date += timedelta(days=30)  # Monthly
            
            subscription = {
                "subscription_id": f"SUB-{secrets.token_hex(8).upper()}",
                "service": service,
                "plan": random.choice(["Individual", "Family", "Premium"]),
                "status": "active",
                "start_date": start_date.isoformat(),
                "next_billing": (base_time + timedelta(days=random.randint(1, 28))).isoformat(),
                "payment_method": f"{config.cardholder.card_network} ending in {config.cardholder.card_last_four}",
                "payments": payments,
                "cardholder_name": config.cardholder.full_name,
            }
            subscriptions.append(subscription)
        
        with open(subscription_dir / "subscriptions.json", "w") as f:
            json.dump(subscriptions, f, indent=2)
        
        logger.info(f"[V7.6] Subscription history: {len(subscriptions)} active subscriptions")
        return len(subscriptions)

    def _generate_review_history(self, records: List[PurchaseRecord],
                                  config: PurchaseHistoryConfig) -> int:
        """
        Generate product review history.
        
        Real users write reviews for ~5-15% of purchases. Review history
        shows genuine engagement and builds trust with merchants.
        """
        review_dir = self.profile_path / "review_history"
        review_dir.mkdir(parents=True, exist_ok=True)
        
        # Pick 1-3 orders to have reviews (5-15% review rate)
        num_reviews = max(1, int(len(records) * random.uniform(0.10, 0.20)))
        review_candidates = [r for r in records if r.status == OrderStatus.DELIVERED]
        
        if not review_candidates:
            return 0
        
        reviewed_orders = random.sample(review_candidates, min(num_reviews, len(review_candidates)))
        
        reviews = []
        positive_phrases = [
            "Exactly what I needed", "Great quality", "Fast shipping", 
            "Would buy again", "Excellent product", "Good value",
            "Works as described", "Happy with purchase"
        ]
        
        for order in reviewed_orders:
            # Review 5-30 days after delivery
            review_date = order.delivery_date + timedelta(days=random.randint(5, 30)) if order.delivery_date else order.order_date + timedelta(days=random.randint(14, 40))
            
            # Most reviews are positive (4-5 stars)
            rating = random.choices([5, 4, 3, 2], weights=[0.50, 0.35, 0.10, 0.05])[0]
            
            item = order.items[0] if order.items else {"name": "Product"}
            
            review = {
                "review_id": f"REV-{secrets.token_hex(8).upper()}",
                "order_id": order.order_id,
                "merchant": order.merchant,
                "merchant_domain": order.merchant_domain,
                "product": item.get("name", "Product"),
                "rating": rating,
                "title": random.choice(positive_phrases) if rating >= 4 else "Okay product",
                "body": f"{'Good' if rating >= 4 else 'Average'} experience. " + 
                        random.choice(positive_phrases) + "." if rating >= 4 else "It works, nothing special.",
                "review_date": review_date.isoformat(),
                "verified_purchase": True,
                "helpful_votes": random.randint(0, 5) if random.random() > 0.7 else 0,
            }
            reviews.append(review)
        
        with open(review_dir / "reviews.json", "w") as f:
            json.dump(reviews, f, indent=2)
        
        logger.info(f"[V7.6] Review history: {len(reviews)} product reviews")
        return len(reviews)

    def _generate_loyalty_rewards(self, records: List[PurchaseRecord],
                                   config: PurchaseHistoryConfig) -> int:
        """
        Generate loyalty program / rewards data.
        
        Real users accumulate loyalty points. Profiles with rewards
        history show long-term customer relationships.
        """
        rewards_dir = self.profile_path / "loyalty_rewards"
        rewards_dir.mkdir(parents=True, exist_ok=True)
        
        # Group orders by merchant for loyalty programs
        merchant_orders = {}
        for record in records:
            if record.merchant not in merchant_orders:
                merchant_orders[record.merchant] = []
            merchant_orders[record.merchant].append(record)
        
        loyalty_programs = []
        
        # Generate loyalty for merchants with 2+ orders
        for merchant, orders in merchant_orders.items():
            if len(orders) < 2:
                continue
            
            # Calculate points (roughly 1-2% of spend)
            total_spent = sum(o.amount for o in orders)
            points_rate = random.uniform(1.0, 2.5)
            points_earned = int(total_spent * points_rate)
            
            # Some points redeemed
            points_redeemed = int(points_earned * random.uniform(0, 0.4)) if points_earned > 100 else 0
            
            first_order = min(orders, key=lambda x: x.order_date)
            
            loyalty = {
                "program_id": f"LYL-{secrets.token_hex(6).upper()}",
                "merchant": merchant,
                "member_since": first_order.order_date.isoformat(),
                "tier": "Gold" if total_spent > 500 else "Silver" if total_spent > 200 else "Bronze",
                "points_earned": points_earned,
                "points_redeemed": points_redeemed,
                "points_balance": points_earned - points_redeemed,
                "lifetime_spend": round(total_spent, 2),
                "orders_count": len(orders),
                "email": config.cardholder.email,
            }
            loyalty_programs.append(loyalty)
        
        with open(rewards_dir / "loyalty_programs.json", "w") as f:
            json.dump(loyalty_programs, f, indent=2)
        
        logger.info(f"[V7.6] Loyalty rewards: {len(loyalty_programs)} programs")
        return len(loyalty_programs)
    
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
# MULTI-PSP PROCESSOR COORDINATION LAYER
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class PSPProcessor:
    """Represents a single payment service provider with characteristics."""
    name: str
    priority: int  # 1-10, higher = better for profile age recommendations
    success_rate: float  # 0.88-0.99, realistic for each processor
    transactions: List[Dict] = field(default_factory=list)
    tokens: Dict[str, str] = field(default_factory=dict)
    
    def record_transaction(self, amount: float, timestamp: float, card_id: str) -> None:
        """Record a transaction on this processor."""
        self.transactions.append({
            "amount": amount,
            "timestamp": timestamp,
            "card_id": card_id,
            "status": "completed"
        })
    
    def get_transaction_count(self) -> int:
        """Get total transactions recorded on this processor."""
        return len(self.transactions)
    
    def get_total_volume(self) -> float:
        """Get total transaction volume on this processor."""
        return sum(t["amount"] for t in self.transactions)


class MultiPSPProcessor:
    """Coordinates diverse payment processor selection and transaction distribution."""
    
    # Tier 1 processors: Primary, most trusted, highest priority
    TIER_1_PROCESSORS = {
        "stripe": PSPProcessor("Stripe", 10, 0.99),
        "paypal": PSPProcessor("PayPal", 9, 0.98),
        "adyen": PSPProcessor("Adyen", 9, 0.98),
        "braintree": PSPProcessor("Braintree (PayPal)", 8, 0.97),
        "cybersource": PSPProcessor("CyberSource", 8, 0.97),
        "worldpay": PSPProcessor("WorldPay", 8, 0.96),
    }
    
    # Tier 2 processors: Secondary, still trustworthy, medium-high priority
    TIER_2_PROCESSORS = {
        "amazon_pay": PSPProcessor("Amazon Pay", 7, 0.95),
        "shopify": PSPProcessor("Shopify Payments", 7, 0.95),
        "checkout": PSPProcessor("Checkout.com", 7, 0.94),
        "square": PSPProcessor("Square", 6, 0.93),
        "klarna": PSPProcessor("Klarna", 6, 0.92),
    }
    
    # Tier 3 processors: Regional/niche, reliable, medium priority
    TIER_3_PROCESSORS = {
        "2checkout": PSPProcessor("2Checkout (Verifone)", 5, 0.91),
        "gocardless": PSPProcessor("GoCardless", 5, 0.90),
        "wise": PSPProcessor("Wise", 4, 0.89),
    }
    
    PROCESSOR_POOL = {**TIER_1_PROCESSORS, **TIER_2_PROCESSORS, **TIER_3_PROCESSORS}
    
    # Merchant-specific processor assignments (realistic patterns)
    MERCHANT_PROCESSOR_MAPPING = {
        "Amazon": ["amazon_pay", "stripe", "paypal"],
        "Walmart": ["paypal", "stripe", "braintree"],
        "Best Buy": ["stripe", "paypal", "cybersource"],
        "Target": ["paypal", "stripe", "square"],
        "Adidas": ["stripe", "square", "paypal"],
        "Nike": ["stripe", "paypal", "adyen"],
        "Apple": ["stripe", "paypal", "square"],
        "default": ["stripe", "paypal", "adyen", "braintree", "cybersource"],
    }
    
    def __init__(self, profile_age_days: int = 30):
        """Initialize MultiPSPProcessor with profile characteristics."""
        self.profile_age_days = profile_age_days
        self.selected_processors: List[PSPProcessor] = []
        self.transaction_distribution: Dict[str, int] = {}
        self.processor_diversity_score = 0.0
        
        # Diversify processor selection based on age
        self._diversify_processors()
    
    def _diversify_processors(self) -> None:
        """Select 5-8 processors based on profile age for realistic diversity."""
        # Newer profiles use fewer processors; older ones use more
        if self.profile_age_days < 7:
            processor_count = 3  # New profile: 2-3 processors
        elif self.profile_age_days < 30:
            processor_count = 5  # Young profile: 4-5 processors
        elif self.profile_age_days < 90:
            processor_count = 6  # Mature profile: 6-7 processors
        else:
            processor_count = 8  # Established profile: 7-8 processors
        
        # Favor Tier 1, then Tier 2, then Tier 3 based on age
        tier1_count = max(2, int(processor_count * 0.50))
        tier2_count = max(1, int(processor_count * 0.35))
        tier3_count = processor_count - tier1_count - tier2_count
        
        self.selected_processors = []
        self.selected_processors.extend(
            list(self.TIER_1_PROCESSORS.values())[:tier1_count]
        )
        self.selected_processors.extend(
            list(self.TIER_2_PROCESSORS.values())[:tier2_count]
        )
        self.selected_processors.extend(
            list(self.TIER_3_PROCESSORS.values())[:tier3_count]
        )
        
        # Calculate diversity score (0-1, max = all 15 processors used)
        self.processor_diversity_score = len(self.selected_processors) / len(
            self.PROCESSOR_POOL
        )
    
    def _distribute_transactions(self, total_transactions: int) -> Dict[str, int]:
        """Distribute transactions realistically across selected processors."""
        if not self.selected_processors:
            return {}
        
        # Weight distribution by priority: higher priority gets more transactions
        total_priority = sum(p.priority for p in self.selected_processors)
        distribution = {}
        
        remaining = total_transactions
        for i, processor in enumerate(self.selected_processors):
            if i == len(self.selected_processors) - 1:
                # Last processor gets remainder to exactly match total
                distribution[processor.name] = remaining
            else:
                # Proportional allocation based on priority
                allocation = int(total_transactions * (processor.priority / total_priority))
                distribution[processor.name] = allocation
                remaining -= allocation
        
        self.transaction_distribution = distribution
        return distribution
    
    def get_processors_for_merchant(self, merchant: str) -> List[str]:
        """Get recommended processors for a specific merchant (2-4 processors)."""
        # Use merchant-specific assignment if available
        if merchant in self.MERCHANT_PROCESSOR_MAPPING:
            base_processors = self.MERCHANT_PROCESSOR_MAPPING[merchant]
        else:
            base_processors = self.MERCHANT_PROCESSOR_MAPPING["default"]
        
        # Filter to only selected processors, pad if needed
        recommended = [
            p for p in base_processors if p in [proc.name.lower().replace(" ", "_") for proc in self.selected_processors]
        ]
        
        if not recommended:
            # Fallback: use top selected processors
            recommended = [
                self.PROCESSOR_POOL[list(self.PROCESSOR_POOL.keys())[i]].name
                for i in range(min(3, len(self.selected_processors)))
            ]
        
        return recommended[:4]  # Cap at 4 processors per merchant
    
    def assign_processor_to_transaction(
        self, merchant: str = "default"
    ) -> PSPProcessor:
        """Select a processor for a transaction using weighted random selection."""
        processors = self.get_processors_for_merchant(merchant)
        if not processors:
            processors = [p.name for p in self.selected_processors[:3]]
        
        # Weight selection by priority
        selected = random.choices(
            [p for p in self.selected_processors if p.name in processors],
            weights=[p.priority for p in self.selected_processors if p.name in processors],
            k=1
        )[0]
        return selected
    
    def get_processor_statistics(self) -> Dict:
        """Get comprehensive statistics about processor diversity and coverage."""
        return {
            "processor_count": len(self.selected_processors),
            "diversity_score": round(self.processor_diversity_score, 3),
            "selected_processors": [p.name for p in self.selected_processors],
            "transaction_distribution": self.transaction_distribution,
            "coverage_percentage": round(self.processor_diversity_score * 100, 1),
            "average_priority": round(
                sum(p.priority for p in self.selected_processors)
                / len(self.selected_processors),
                2,
            ),
        }


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
