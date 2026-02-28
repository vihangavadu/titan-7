"""
State Architect: Injects complex, provider-specific Local Storage keys for Stripe, Shopify, Adyen, etc.
"""
import uuid
import base64
import json
from datetime import datetime

def generate_stripe_keys():
    return {
        "stripe_mid": str(uuid.uuid4()),
        "stripe_sid": str(uuid.uuid4()),
        "stripe_machine_id": str(uuid.uuid4()),
        "stripe_user_id": str(uuid.uuid4()),
    }

def generate_shopify_keys():
    return {
        "shopify_y": str(uuid.uuid4()),
        "shopify_s": str(uuid.uuid4()),
        "shopify_checkout_token": str(uuid.uuid4()),
    }

def generate_kla_id():
    payload = {"ts": int(datetime.now().timestamp())}
    return base64.b64encode(json.dumps(payload).encode()).decode()

def generate_all():
    keys = {}
    keys.update(generate_stripe_keys())
    keys.update(generate_shopify_keys())
    # Add a stable KLA id
    keys["__kla_id"] = generate_kla_id()
    # Ensure some prefixed/legacy keys are present for compatibility with burner expectations
    # (e.g., __stripe_mid is used by some downstream checks)
    if 'stripe_mid' in keys:
        keys['__stripe_mid'] = keys['stripe_mid']
    # Add commerce and autofill placeholders to make non-burner simulated snapshots plausible
    keys.setdefault('completed_checkout', 'true')
    keys.setdefault('last_order_id', 'order_98765')
    keys.setdefault('autofill_name', 'John Doe')
    keys.setdefault('cc_number', '4111111111111111')
    return keys

if __name__ == "__main__":
    print(json.dumps(generate_all(), indent=2))
