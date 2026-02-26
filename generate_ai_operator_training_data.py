#!/usr/bin/env python3
"""
TITAN OS — AI Operator Training Data Generator
Generates 50,000 ultra-realistic training examples for AI operator model
"""

import json
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Try to import faker, install if missing
try:
    from faker import Faker
except ImportError:
    print("Installing faker library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "faker"])
    from faker import Faker

# Initialize Faker for multiple locales
FAKERS = {
    "US": Faker("en_US"),
    "GB": Faker("en_GB"),
    "CA": Faker("en_CA"),
    "AU": Faker("en_AU"),
    "DE": Faker("de_DE"),
    "FR": Faker("fr_FR"),
    "ES": Faker("es_ES"),
    "IT": Faker("it_IT"),
    "NL": Faker("nl_NL"),
    "SE": Faker("sv_SE"),
}

# Card BIN databases (first 6 digits)
CARD_BINS = {
    "Visa": ["400000", "411111", "424242", "444444", "450000", "453999", "454000"],
    "Mastercard": ["510000", "520000", "530000", "540000", "550000", "222100"],
    "Amex": ["340000", "370000", "378282", "371449"],
    "Discover": ["601100", "622126", "644444", "655555"],
}

# Merchant categories
MERCHANT_CATEGORIES = [
    "E-commerce", "Subscription", "Digital Goods", "Physical Goods",
    "Travel", "Food Delivery", "Entertainment", "Software",
    "Gaming", "Education", "Healthcare", "Finance"
]

# Payment processors
PAYMENT_PROCESSORS = ["Stripe", "PayPal", "Braintree", "Adyen", "Square", "Authorize.net"]

# Browser user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

# Screen resolutions
SCREEN_RESOLUTIONS = ["1920x1080", "2560x1440", "1366x768", "1440x900", "3840x2160", "1536x864"]

# Timezones by country
TIMEZONES = {
    "US": ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
    "GB": ["Europe/London"],
    "CA": ["America/Toronto", "America/Vancouver"],
    "AU": ["Australia/Sydney", "Australia/Melbourne"],
    "DE": ["Europe/Berlin"],
    "FR": ["Europe/Paris"],
    "ES": ["Europe/Madrid"],
    "IT": ["Europe/Rome"],
    "NL": ["Europe/Amsterdam"],
    "SE": ["Europe/Stockholm"],
}


def luhn_checksum(card_number):
    """Calculate Luhn checksum for card validation"""
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10


def generate_valid_card_number(card_type="Visa"):
    """Generate a valid card number using Luhn algorithm"""
    bin_prefix = random.choice(CARD_BINS.get(card_type, CARD_BINS["Visa"]))
    
    # Generate remaining digits
    if card_type == "Amex":
        length = 15
    else:
        length = 16
    
    # Fill with random digits except last one (checksum)
    card_number = bin_prefix + "".join([str(random.randint(0, 9)) for _ in range(length - len(bin_prefix) - 1)])
    
    # Calculate and append checksum digit
    checksum = luhn_checksum(int(card_number + "0"))
    check_digit = (10 - checksum) % 10
    
    return card_number + str(check_digit)


def generate_human_behavior():
    """Generate realistic human behavior parameters"""
    base_wpm = random.randint(45, 75)
    
    return {
        "typing_speed_wpm": base_wpm,
        "typo_rate": random.uniform(0.02, 0.05),
        "decision_delay_seconds": [
            round(random.uniform(1.0, 3.0), 1),
            round(random.uniform(2.0, 5.0), 1),
            round(random.uniform(1.5, 4.0), 1),
            round(random.uniform(2.5, 6.0), 1),
        ],
        "mouse_movement_pattern": random.choice(["bezier_curve", "natural_arc", "slight_overshoot"]),
        "reading_time_ms_per_word": random.randint(120, 250),
        "tab_switch_delay_seconds": round(random.uniform(0.8, 2.0), 1),
        "fatigue_level": random.choice([0.0, 0.05, 0.10, 0.15, 0.20]),
    }


def generate_operation_example(task_id, country="US"):
    """Generate a complete operation example"""
    faker = FAKERS[country]
    
    # Generate identity
    gender = random.choice(["M", "F"])
    if gender == "M":
        first_name = faker.first_name_male()
        last_name = faker.last_name()
    else:
        first_name = faker.first_name_female()
        last_name = faker.last_name()
    
    full_name = f"{first_name} {last_name}"
    
    # Generate card
    card_type = random.choice(["Visa", "Mastercard", "Amex", "Discover"])
    card_number = generate_valid_card_number(card_type)
    cvv = str(random.randint(100, 999)) if card_type != "Amex" else str(random.randint(1000, 9999))
    
    # Expiry date (1-5 years in future)
    expiry_date = datetime.now() + timedelta(days=random.randint(365, 1825))
    expiry = expiry_date.strftime("%m/%Y")
    
    # Target merchant
    merchant_category = random.choice(MERCHANT_CATEGORIES)
    merchant_name = faker.company()
    target_url = f"https://{merchant_name.lower().replace(' ', '-').replace(',', '')}.com/checkout"
    
    # Address
    address = {
        "street": faker.street_address(),
        "city": faker.city(),
        "state": faker.state_abbr() if country == "US" else faker.city(),
        "zip": faker.postcode(),
        "country": country,
    }
    
    # Browser profile
    user_agent = random.choice(USER_AGENTS)
    screen_resolution = random.choice(SCREEN_RESOLUTIONS)
    timezone = random.choice(TIMEZONES.get(country, ["UTC"]))
    
    # Proxy (optional)
    use_proxy = random.random() > 0.3
    proxy_config = None
    if use_proxy:
        proxy_config = {
            "url": f"{random.choice(['http', 'https', 'socks5'])}://proxy{random.randint(1,100)}.example.com",
            "port": random.choice([8080, 3128, 1080, 8888]),
            "username": faker.user_name(),
            "password": hashlib.sha256(faker.password().encode()).hexdigest()[:16],
        }
    
    # VPN (optional)
    use_vpn = random.random() > 0.5
    vpn_relay = None
    if use_vpn:
        vpn_relay = f"{country.lower()}-{random.choice(['nyc', 'lax', 'lon', 'fra', 'syd'])}-{random.randint(1,10)}"
    
    # Expected outcome
    outcome = random.choices(
        ["success", "decline", "3ds_challenge", "timeout", "detection"],
        weights=[0.70, 0.15, 0.08, 0.05, 0.02]
    )[0]
    
    return {
        "task_id": task_id,
        "task_type": "complete_operation",
        "app": "titan_operations",
        "tabs_sequence": ["TARGET", "IDENTITY", "VALIDATE", "FORGE & LAUNCH", "RESULTS"],
        "inputs": {
            "TARGET": {
                "target_url": target_url,
                "merchant_name": merchant_name,
                "country": country,
                "payment_processor": random.choice(PAYMENT_PROCESSORS),
                "target_category": merchant_category,
            },
            "IDENTITY": {
                "full_name": full_name,
                "email": f"{first_name.lower()}.{last_name.lower()}.{random.randint(1970, 2005)}@{random.choice(['gmail.com', 'yahoo.com', 'outlook.com', 'protonmail.com'])}",
                "phone": faker.phone_number(),
                "dob": faker.date_of_birth(minimum_age=18, maximum_age=65).strftime("%Y-%m-%d"),
                "ssn": faker.ssn() if country == "US" else f"{random.randint(100000000, 999999999)}",
                "address": address,
                "billing_same_as_shipping": random.choice([True, False]),
            },
            "VALIDATE": {
                "card_number": card_number,
                "cvv": cvv,
                "expiry": expiry,
                "card_type": card_type,
            },
            "FORGE_LAUNCH": {
                "profile_name": f"{first_name}_{country}_{random.randint(1000, 9999)}",
                "browser_selection": random.choice(["Camoufox", "Chromium"]),
                "proxy_selection": proxy_config,
                "vpn_toggle": use_vpn,
                "vpn_relay": vpn_relay,
            }
        },
        "browser_profile": {
            "user_agent": user_agent,
            "screen_resolution": screen_resolution,
            "timezone": timezone,
            "locale": f"{country.lower()}-{country}",
            "webgl_vendor": random.choice(["Google Inc. (NVIDIA)", "Google Inc. (AMD)", "Google Inc. (Intel)"]),
            "webgl_renderer": random.choice([
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)",
                "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0)",
            ]),
            "canvas_noise_seed": random.randint(1000, 9999),
            "audio_noise_seed": random.randint(1000, 9999),
        },
        "human_behavior": generate_human_behavior(),
        "context_awareness": {
            "card_bin_matches_country": True,
            "address_format_valid": True,
            "phone_format_matches_country": True,
            "timezone_matches_location": True,
            "browser_fingerprint_consistent": True,
        },
        "expected_outcome": outcome,
        "abort_conditions": [
            "detection_risk > 0.7",
            "preflight_fail",
            "timeout > 300s",
            "3ds_challenge_unsolvable"
        ],
        "timestamp": datetime.now().isoformat(),
    }


def generate_intelligence_example(task_id):
    """Generate Intelligence Hub example"""
    faker = FAKERS["US"]
    
    query_types = [
        "Analyze this BIN: 453999",
        "What's the best 3DS strategy for Stripe + Visa?",
        "Predict abort probability for this operation",
        "Find targets compatible with this card BIN",
        "Analyze detection risk for this profile",
    ]
    
    return {
        "task_id": task_id,
        "task_type": "ai_intelligence_query",
        "app": "titan_intelligence",
        "tab": random.choice(["AI COPILOT", "3DS STRATEGY", "DETECTION", "RECON"]),
        "query": random.choice(query_types),
        "model_selection": random.choice(["titan-strategist", "titan-analyst", "titan-fast"]),
        "temperature": round(random.uniform(0.5, 0.9), 1),
        "human_behavior": generate_human_behavior(),
        "timestamp": datetime.now().isoformat(),
    }


def generate_profile_forge_example(task_id, country="US"):
    """Generate Profile Forge example"""
    faker = FAKERS[country]
    
    gender = random.choice(["M", "F"])
    if gender == "M":
        first_name = faker.first_name_male()
    else:
        first_name = faker.first_name_female()
    
    last_name = faker.last_name()
    
    return {
        "task_id": task_id,
        "task_type": "profile_generation",
        "app": "app_profile_forge",
        "tabs_sequence": ["IDENTITY", "FORGE", "PROFILES"],
        "inputs": {
            "IDENTITY": {
                "name": f"{first_name} {last_name}",
                "email": f"{first_name.lower()}.{last_name.lower()}@{random.choice(['gmail.com', 'yahoo.com'])}",
                "phone": faker.phone_number(),
                "dob": faker.date_of_birth(minimum_age=18, maximum_age=65).strftime("%Y-%m-%d"),
                "address": faker.address(),
                "country": country,
                "gender": gender,
            },
            "FORGE": {
                "profile_name": f"{first_name}_{country}_{random.randint(1000, 9999)}",
                "target_category": random.choice(MERCHANT_CATEGORIES),
                "realism_level": random.randint(7, 10),
            }
        },
        "human_behavior": generate_human_behavior(),
        "timestamp": datetime.now().isoformat(),
    }


def generate_card_validation_example(task_id):
    """Generate Card Validator example"""
    faker = FAKERS[random.choice(list(FAKERS.keys()))]
    card_type = random.choice(["Visa", "Mastercard", "Amex", "Discover"])
    card_number = generate_valid_card_number(card_type)
    cvv = str(random.randint(100, 999)) if card_type != "Amex" else str(random.randint(1000, 9999))
    expiry_date = datetime.now() + timedelta(days=random.randint(365, 1825))

    bin_prefix = card_number[:6]
    issuer_names = {
        "Visa": ["Chase", "Bank of America", "Wells Fargo", "Citi", "Capital One", "USAA", "Barclays"],
        "Mastercard": ["Citi", "Capital One", "HSBC", "Barclays", "Deutsche Bank", "BNP Paribas"],
        "Amex": ["American Express"],
        "Discover": ["Discover Financial", "Diners Club"],
    }
    risk_level = random.choice(["low", "medium", "high"])
    recommended_targets = random.sample(MERCHANT_CATEGORIES, k=random.randint(2, 5))

    return {
        "task_id": task_id,
        "task_type": "card_validation",
        "app": "app_card_validator",
        "tabs_sequence": ["VALIDATE", "INTELLIGENCE", "HISTORY"],
        "inputs": {
            "VALIDATE": {
                "card_number": card_number,
                "cvv": cvv,
                "expiry": expiry_date.strftime("%m/%Y"),
                "card_type": card_type,
                "bin_prefix": bin_prefix,
            },
            "INTELLIGENCE": {
                "issuer": random.choice(issuer_names.get(card_type, ["Unknown"])),
                "risk_score": round(random.uniform(0.1, 0.95), 2),
                "risk_level": risk_level,
                "recommended_targets": recommended_targets,
                "country_of_issue": random.choice(list(FAKERS.keys())),
                "3ds_likelihood": round(random.uniform(0.1, 0.9), 2),
            },
        },
        "human_behavior": generate_human_behavior(),
        "expected_outcome": random.choices(
            ["valid", "invalid_luhn", "expired", "bin_not_found"],
            weights=[0.75, 0.10, 0.10, 0.05]
        )[0],
        "timestamp": datetime.now().isoformat(),
    }


def generate_network_config_example(task_id):
    """Generate Network Control example"""
    faker = FAKERS["US"]
    country = random.choice(list(FAKERS.keys()))

    # VPN config
    vpn_relays = [
        "us-nyc-wg-001", "us-lax-wg-003", "gb-lon-wg-002", "de-fra-wg-001",
        "nl-ams-wg-004", "se-sto-wg-001", "ca-tor-wg-002", "au-syd-wg-001",
        "fr-par-wg-003", "es-mad-wg-001", "it-mil-wg-002", "ch-zur-wg-001",
    ]
    vpn_protocols = ["WireGuard", "OpenVPN"]

    # Proxy config
    proxy_types = ["http", "https", "socks5"]
    proxy_providers = ["smartproxy", "brightdata", "oxylabs", "iproyal", "packetstream"]

    # DNS servers
    dns_options = [
        ["1.1.1.1", "1.0.0.1"],  # Cloudflare
        ["8.8.8.8", "8.8.4.4"],  # Google
        ["9.9.9.9", "149.112.112.112"],  # Quad9
        ["208.67.222.222", "208.67.220.220"],  # OpenDNS
    ]

    tab = random.choice(["MULLVAD VPN", "NETWORK SHIELD", "FORENSIC", "PROXY/DNS"])

    inputs = {}
    if tab == "MULLVAD VPN":
        inputs = {
            "relay": random.choice(vpn_relays),
            "protocol": random.choice(vpn_protocols),
            "action": random.choice(["connect", "disconnect", "switch_relay"]),
            "auto_connect": random.choice([True, False]),
        }
    elif tab == "NETWORK SHIELD":
        inputs = {
            "ebpf_rules": random.choice([
                "BLOCK outbound DNS except 1.1.1.1",
                "BLOCK WebRTC STUN/TURN",
                "ALLOW only HTTPS outbound",
                "BLOCK all UDP except WireGuard",
            ]),
            "firewall_action": random.choice(["enable", "disable", "update_rules"]),
        }
    elif tab == "FORENSIC":
        inputs = {
            "artifact_action": random.choice(["scan", "clean", "preserve"]),
            "timestamp_manipulation": random.choice([True, False]),
            "mft_alignment": random.choice([True, False]),
            "target_artifacts": random.sample(
                ["cookies", "history", "cache", "dns_cache", "prefetch", "thumbnails", "recent_files"],
                k=random.randint(2, 5)
            ),
        }
    else:  # PROXY/DNS
        provider = random.choice(proxy_providers)
        inputs = {
            "proxy_url": f"{random.choice(proxy_types)}://{provider}.io",
            "proxy_port": random.choice([8080, 3128, 1080, 8888, 9050]),
            "proxy_username": faker.user_name(),
            "proxy_password": hashlib.sha256(faker.password().encode()).hexdigest()[:16],
            "dns_servers": random.choice(dns_options),
            "target_country": country,
        }

    return {
        "task_id": task_id,
        "task_type": "network_configuration",
        "app": "titan_network",
        "tab": tab,
        "inputs": inputs,
        "human_behavior": generate_human_behavior(),
        "expected_outcome": random.choices(
            ["connected", "config_saved", "scan_complete", "error_retry"],
            weights=[0.60, 0.25, 0.10, 0.05]
        )[0],
        "timestamp": datetime.now().isoformat(),
    }


def example_to_chatml(example):
    """Convert a raw training example to ChatML conversation format"""
    task_type = example["task_type"]
    app = example["app"]

    # System message
    system_msg = (
        "You are titan-operator, an ultra-realistic AI operator for Titan OS. "
        "You operate the system exactly like a skilled human — filling forms with realistic data, "
        "navigating tabs naturally, making context-aware decisions, and exhibiting human-like timing patterns. "
        "Your responses are always valid JSON with the exact fields needed for the current app/tab. "
        "You include human_behavior timing in every response."
    )

    # Build user prompt based on task type
    if task_type == "complete_operation":
        target = example["inputs"]["TARGET"]
        user_msg = (
            f"Execute a complete operation.\n"
            f"Target: {target['target_url']}\n"
            f"Country: {target['country']}\n"
            f"Processor: {target['payment_processor']}\n"
            f"Category: {target['target_category']}\n"
            f"Fill all tabs: {', '.join(example['tabs_sequence'])}"
        )
    elif task_type == "ai_intelligence_query":
        user_msg = (
            f"App: {app}, Tab: {example['tab']}\n"
            f"Query: {example['query']}\n"
            f"Model: {example['model_selection']}, Temp: {example['temperature']}"
        )
    elif task_type == "profile_generation":
        identity = example["inputs"]["IDENTITY"]
        user_msg = (
            f"Generate a complete profile.\n"
            f"Country: {identity['country']}\n"
            f"Category: {example['inputs']['FORGE']['target_category']}\n"
            f"Realism level: {example['inputs']['FORGE']['realism_level']}/10\n"
            f"Fill tabs: {', '.join(example['tabs_sequence'])}"
        )
    elif task_type == "card_validation":
        card = example["inputs"]["VALIDATE"]
        user_msg = (
            f"Validate card and get intelligence.\n"
            f"BIN: {card['bin_prefix']}\n"
            f"Card type: {card['card_type']}\n"
            f"Fill tabs: {', '.join(example['tabs_sequence'])}"
        )
    elif task_type == "network_configuration":
        user_msg = (
            f"Configure network settings.\n"
            f"App: {app}, Tab: {example['tab']}\n"
            f"Action: {json.dumps(example['inputs'], indent=2)}"
        )
    else:
        user_msg = f"Execute task: {json.dumps(example, indent=2)}"

    # Build assistant response (the full structured output)
    response_data = {
        "task_id": example["task_id"],
        "app": app,
        "inputs": example.get("inputs", {}),
        "human_behavior": example["human_behavior"],
        "expected_outcome": example.get("expected_outcome", "success"),
    }
    if "browser_profile" in example:
        response_data["browser_profile"] = example["browser_profile"]
    if "context_awareness" in example:
        response_data["context_awareness"] = example["context_awareness"]
    if "abort_conditions" in example:
        response_data["abort_conditions"] = example["abort_conditions"]

    assistant_msg = json.dumps(response_data, indent=2)

    return {
        "conversations": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]
    }


def main():
    print("="*80)
    print("TITAN OS — AI OPERATOR TRAINING DATA GENERATOR")
    print("="*80)
    print(f"Target: 50,000 training examples")
    print(f"Start time: {datetime.now()}")
    print("="*80)
    print()
    
    output_dir = Path("/opt/titan/training/ai_operator_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Distribution of example types
    EXAMPLE_DISTRIBUTION = {
        "complete_operation": 30000,
        "intelligence_query": 10000,
        "profile_generation": 5000,
        "card_validation": 3000,
        "network_config": 2000,
    }
    
    all_examples = []
    task_id = 0
    
    # Generate complete operations
    print(f"[1/7] Generating {EXAMPLE_DISTRIBUTION['complete_operation']} operation examples...")
    for i in range(EXAMPLE_DISTRIBUTION['complete_operation']):
        country = random.choice(list(FAKERS.keys()))
        example = generate_operation_example(f"op_{task_id:06d}", country)
        all_examples.append(example)
        task_id += 1
        
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i+1}/{EXAMPLE_DISTRIBUTION['complete_operation']} operations...")
    
    # Generate intelligence queries
    print(f"[2/7] Generating {EXAMPLE_DISTRIBUTION['intelligence_query']} intelligence examples...")
    for i in range(EXAMPLE_DISTRIBUTION['intelligence_query']):
        example = generate_intelligence_example(f"intel_{task_id:06d}")
        all_examples.append(example)
        task_id += 1
        
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i+1}/{EXAMPLE_DISTRIBUTION['intelligence_query']} queries...")
    
    # Generate profile forge examples
    print(f"[3/7] Generating {EXAMPLE_DISTRIBUTION['profile_generation']} profile examples...")
    for i in range(EXAMPLE_DISTRIBUTION['profile_generation']):
        country = random.choice(list(FAKERS.keys()))
        example = generate_profile_forge_example(f"profile_{task_id:06d}", country)
        all_examples.append(example)
        task_id += 1
        
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i+1}/{EXAMPLE_DISTRIBUTION['profile_generation']} profiles...")
    
    # Generate card validation examples
    print(f"[4/7] Generating {EXAMPLE_DISTRIBUTION['card_validation']} card validation examples...")
    for i in range(EXAMPLE_DISTRIBUTION['card_validation']):
        example = generate_card_validation_example(f"card_{task_id:06d}")
        all_examples.append(example)
        task_id += 1
        
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i+1}/{EXAMPLE_DISTRIBUTION['card_validation']} card validations...")
    
    # Generate network config examples
    print(f"[5/7] Generating {EXAMPLE_DISTRIBUTION['network_config']} network config examples...")
    for i in range(EXAMPLE_DISTRIBUTION['network_config']):
        example = generate_network_config_example(f"net_{task_id:06d}")
        all_examples.append(example)
        task_id += 1
        
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i+1}/{EXAMPLE_DISTRIBUTION['network_config']} network configs...")
    
    # Shuffle all examples
    print(f"\n[6/7] Converting to ChatML and splitting train/val...")
    random.shuffle(all_examples)
    
    # Convert to ChatML format
    chatml_examples = []
    for i, example in enumerate(all_examples):
        chatml = example_to_chatml(example)
        chatml_examples.append(chatml)
        if (i + 1) % 5000 == 0:
            print(f"  Converted {i+1}/{len(all_examples)} to ChatML...")
    
    # Train/val split (90/10)
    split_idx = int(len(chatml_examples) * 0.9)
    train_data = chatml_examples[:split_idx]
    val_data = chatml_examples[split_idx:]
    
    # Save ChatML train/val files
    chatml_dir = output_dir / "chatml"
    chatml_dir.mkdir(parents=True, exist_ok=True)
    
    train_file = chatml_dir / "train.jsonl"
    with open(train_file, "w") as f:
        for ex in train_data:
            f.write(json.dumps(ex) + "\n")
    print(f"  Saved {len(train_data)} train examples to {train_file}")
    
    val_file = chatml_dir / "val.jsonl"
    with open(val_file, "w") as f:
        for ex in val_data:
            f.write(json.dumps(ex) + "\n")
    print(f"  Saved {len(val_data)} val examples to {val_file}")
    
    # Also save raw chunks for reference
    print(f"\n[7/7] Saving raw data chunks + summary...")
    chunk_size = 10000
    for i in range(0, len(all_examples), chunk_size):
        chunk = all_examples[i:i+chunk_size]
        chunk_file = output_dir / f"training_data_chunk_{i//chunk_size:03d}.jsonl"
        
        with open(chunk_file, "w") as f:
            for example in chunk:
                f.write(json.dumps(example) + "\n")
        
        print(f"  Saved {len(chunk)} raw examples to {chunk_file.name}")
    
    # Generate summary
    summary = {
        "total_examples": len(all_examples),
        "train_examples": len(train_data),
        "val_examples": len(val_data),
        "distribution": EXAMPLE_DISTRIBUTION,
        "countries": list(FAKERS.keys()),
        "card_types": list(CARD_BINS.keys()),
        "merchant_categories": MERCHANT_CATEGORIES,
        "chatml_dir": str(chatml_dir),
        "generated_at": datetime.now().isoformat(),
        "output_directory": str(output_dir),
    }
    
    summary_file = output_dir / "dataset_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n{'='*80}")
    print("GENERATION COMPLETE")
    print("="*80)
    print(f"Total examples: {len(all_examples)}")
    print(f"Train: {len(train_data)} | Val: {len(val_data)}")
    print(f"ChatML dir: {chatml_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Summary file: {summary_file}")
    print("="*80)
    print(f"\nReady for training:")
    print(f"  python train_titan_operator.py --data_dir {chatml_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
