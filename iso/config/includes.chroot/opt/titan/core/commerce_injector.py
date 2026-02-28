# LUCID EMPIRE :: COMMERCE INJECTOR
# Purpose: Injects localStorage artifacts AND dispatches StorageEvents.

import asyncio

async def inject_trust_anchors(page, key, value):
    """Inject a trust anchor (key-value pair) into localStorage and dispatch a storage event"""
    # Double-Tap Injection: First write the data, then dispatch a synthetic storage event

    # Tap 1: Write the data
    await page.evaluate(
        f"""
        localStorage.setItem('{key}', '{value}');
        """
    )

    # Tap 2: Fabricate and dispatch the StorageEvent
    await page.evaluate(
        f"""
        const event = new StorageEvent('storage', {{
            key: '{key}',
            newValue: '{value}',
            oldValue: null,
            url: window.location.href,
            storageArea: localStorage
        }});
        window.dispatchEvent(event);
        """
    )

async def inject_commerce_vector(page, platform="shopify"):
    print(f" [*] Injecting Commerce Vector: {platform.upper()}")
    
    if platform == "shopify":
        # Simulate a completed checkout token from 30 days ago
        token = "c1234567-89ab-cdef-0123-4567890abcdef"
        await inject_trust_anchors(page, "checkout_token", token)
        await inject_trust_anchors(page, "shopify_pay_redirect_cookie", "true")
        # 'completed' flag often checked by analytics
        await inject_trust_anchors(page, "completed", "true")
        
    elif platform == "stripe":
        # Inject Stripe device identifiers (Plan 6.3)
        # MUID is typically a GUID structure
        fake_muid = "c6b9d635-20de-4fc6-8995-5d5b2d165881"
        await inject_trust_anchors(page, "muid", fake_muid)
        await inject_trust_anchors(page, "stripe_device_id", fake_muid)
        await inject_trust_anchors(page, "__stripe_mid", "mid_" + fake_muid)
        
        # Cookie Injection for session persistence
        # Note: Cookies must be set via browser context for HttpOnly support, 
        # but client-side cookies can be set via JS for tracker detection.
        await page.evaluate(f"""
            document.cookie = "_stripe_sid={fake_muid}; path=/; domain=.stripe.com; max-age=31536000";
            document.cookie = "__stripe_mid=mid_{fake_muid}; path=/; domain=.stripe.com; max-age=31536000";
        """)

    elif platform == "adyen":
        # Plan 6.3: Adyen 3D Secure 2.0 frictionless artifacts
        fake_fingerprint = "adyen_fp_550e8400-e29b-41d4-a716-446655440000"
        await inject_trust_anchors(page, "fingerprint", fake_fingerprint)
        await inject_trust_anchors(page, "dfValue", "1_001" + fake_fingerprint)
        
    print(f" [V] {platform.upper()} Artifacts Injected via Double-Tap.")
