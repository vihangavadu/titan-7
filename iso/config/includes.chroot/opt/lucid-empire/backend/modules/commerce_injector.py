# LUCID EMPIRE :: COMMERCE INJECTOR
# Trust anchor injection for e-commerce signals

import asyncio
import json

async def inject_trust_anchors(page):
    """Inject trust anchors into localStorage and dispatch events."""
    anchors = {
        "_ga": "GA1.2.1234567890.1234567890",
        "_gid": "GA1.2.1234567891.1234567891",
        "_gat": "1",
    }
    
    # Double-tap injection: write + synthetic event
    for key, value in anchors.items():
        await page.evaluate(f"localStorage.setItem('{key}', '{value}')")
        # Dispatch storage event for realistic detection
        await page.evaluate(f"""
            window.dispatchEvent(new StorageEvent('storage', {{
                key: '{key}',
                newValue: '{value}',
                url: window.location.href
            }}))
        """)

async def inject_commerce_vector(page, platform="shopify"):
    """Inject commerce signals (cart, checkout flows)."""
    if platform == "shopify":
        commerce_signals = {
            "cart_items": json.dumps([{"id": "1", "quantity": 1, "price": 9999}]),
            "checkout_flow": "initiated",
            "payment_method": "credit_card"
        }
    elif platform == "stripe":
        commerce_signals = {
            "stripe_session": "test_session_123",
            "payment_status": "processing"
        }
    else:
        commerce_signals = {}
    
    for key, value in commerce_signals.items():
        if isinstance(value, str):
            await page.evaluate(f"localStorage.setItem('{key}', '{value}')")

async def inject_commerce_signals(page):
    """Comprehensive commerce signal injection."""
    signals = {
        "last_purchase_date": "2024-01-15",
        "purchase_frequency": "weekly",
        "avg_order_value": "125.50",
    }
    
    for key, value in signals.items():
        await page.evaluate(f"localStorage.setItem('{key}', '{value}')")
