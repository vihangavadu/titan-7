"""
LUCID EMPIRE: Commerce Injector
Objective: Generate commerce history (LocalStorage vault) to establish trust tokens
"""

import json
import uuid
import base64
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommerceVault:
    """Generates convincing commerce/shopping history for profiles"""
    
    def __init__(self):
        """Initialize commerce vault generator"""
        self.steam_games = [
            "Counter-Strike 2",
            "Dota 2",
            "PUBG: Battlegrounds",
            "Rust",
            "Team Fortress 2",
            "Valheim",
            "Dead by Daylight"
        ]
        self.retailers = ["amazon", "ebay", "shopify", "stripe"]
    
    def generate_guid(self) -> str:
        """Generate a random GUID"""
        return str(uuid.uuid4())
    
    def generate_base64_token(self, length: int = 32) -> str:
        """Generate a random base64 string"""
        random_bytes = bytes(random.getrandbits(8) for _ in range(length))
        return base64.b64encode(random_bytes).decode('utf-8')
    
    def generate_steam_purchase_history(self, days_back: int = 45) -> list:
        """
        Generate Steam purchase history
        
        Args:
            days_back: How many days ago to backdate purchase
        
        Returns:
            List of purchase entries
        """
        purchase_date = datetime.now() - timedelta(days=days_back)
        
        return [
            {
                "game": random.choice(self.steam_games),
                "purchase_date": purchase_date.isoformat(),
                "price_usd": round(random.uniform(9.99, 59.99), 2),
                "transaction_id": self.generate_guid(),
                "payment_method": "credit_card",
                "status": "completed"
            }
        ]
    
    def generate_stripe_vault(self, cc_last4: str, holder_name: str) -> Dict[str, Any]:
        """
        Generate Stripe payment method vault entry
        
        Args:
            cc_last4: Last 4 digits of credit card
            holder_name: Name on credit card
        
        Returns:
            Stripe vault structure
        """
        return {
            "stripe_mid": self.generate_guid(),
            "stripe_fingerprint": self.generate_base64_token(16),
            "stripe_card_brand": "visa",
            "stripe_last4": cc_last4,
            "stripe_exp_month": random.randint(1, 12),
            "stripe_exp_year": datetime.now().year + random.randint(1, 4),
            "stripe_created": int(datetime.now().timestamp()),
            "stripe_holder": holder_name,
            "stripe_status": "verified"
        }
    
    def generate_shopify_vault(self) -> Dict[str, Any]:
        """
        Generate Shopify store vault data
        
        Returns:
            Shopify vault structure
        """
        return {
            "shopify_store_id": self.generate_guid(),
            "shopify_verify_token": self.generate_base64_token(24),
            "shopify_session_id": self.generate_guid(),
            "shopify_customer_id": f"gid://shopify/Customer/{random.randint(1000000, 9999999)}",
            "shopify_last_checkout": (datetime.now() - timedelta(days=random.randint(5, 30))).isoformat(),
            "shopify_cart_items": random.randint(1, 5),
            "shopify_loyalty_points": random.randint(100, 1000)
        }
    
    def generate_amazon_vault(self) -> Dict[str, Any]:
        """
        Generate Amazon account vault data
        
        Returns:
            Amazon vault structure
        """
        return {
            "amazon_account_id": f"amz_{self.generate_guid()[:12]}",
            "amazon_prime_status": random.choice(["active", "active"]),  # 80% chance active
            "amazon_profile_verified": True,
            "amazon_last_purchase": (datetime.now() - timedelta(days=random.randint(3, 20))).isoformat(),
            "amazon_purchase_count": random.randint(15, 150),
            "amazon_reviews_count": random.randint(2, 25),
            "amazon_review_rating": round(random.uniform(4.2, 5.0), 1)
        }
    
    def generate_ebay_vault(self) -> Dict[str, Any]:
        """
        Generate eBay account vault data
        
        Returns:
            eBay vault structure
        """
        return {
            "ebay_user_id": f"ebay_{self.generate_guid()[:10]}",
            "ebay_feedback_score": random.randint(50, 500),
            "ebay_positive_feedback": random.uniform(98.5, 100.0),
            "ebay_member_since": (datetime.now() - timedelta(days=random.randint(180, 1800))).isoformat(),
            "ebay_last_bid": (datetime.now() - timedelta(days=random.randint(2, 30))).isoformat(),
            "ebay_watchlist_count": random.randint(5, 50)
        }
    
    def generate_commerce_vault(self, cc_last4: str, holder_name: str) -> Dict[str, Any]:
        """
        Generate complete commerce vault
        
        This vault imitates a LocalStorage dump from a mature, trusted account
        with multiple payment methods and shopping history.
        
        Args:
            cc_last4: Last 4 digits of credit card
            holder_name: Name on credit card
        
        Returns:
            Complete commerce vault structure
        """
        vault = {
            "metadata": {
                "vault_version": "1.0",
                "generated": datetime.now().isoformat(),
                "holder_name": holder_name,
                "cc_last4": cc_last4
            },
            "stripe": self.generate_stripe_vault(cc_last4, holder_name),
            "shopify": self.generate_shopify_vault(),
            "amazon": self.generate_amazon_vault(),
            "ebay": self.generate_ebay_vault(),
            "steam": {
                "steam_id": f"{random.randint(76561000000000000, 76561999999999999)}",
                "steam_nickname": holder_name.replace(" ", "_"),
                "steam_profile_visibility": "public",
                "steam_account_created": (datetime.now() - timedelta(days=random.randint(365, 1825))).isoformat(),
                "steam_purchase_history": self.generate_steam_purchase_history(45)
            },
            "trust_tokens": {
                "account_age_days": random.randint(180, 1800),
                "total_purchases": random.randint(20, 200),
                "payment_methods": 2 + random.randint(0, 2),
                "verified_email": True,
                "verified_phone": random.choice([True, False]),
                "two_factor_enabled": random.choice([True, True, False]),  # 66% enabled
                "account_reputation_score": round(random.uniform(75, 99), 1)
            }
        }
        
        return vault
    
    def save_vault(self, vault: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        """
        Save vault to JSON file
        
        Args:
            vault: Vault dictionary to save
            output_path: Path to save vault (defaults to profile_data/commerce_vault.json)
        
        Returns:
            Path where vault was saved
        """
        if output_path is None:
            output_path = Path(__file__).parent.parent / "profile_data" / "commerce_vault.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(vault, f, indent=2)
        
        logger.info(f"Commerce vault saved to {output_path}")
        return output_path


def generate_and_save_vault(cc_last4: str, holder_name: str) -> Path:
    """
    Convenience function to generate and save a vault
    
    Args:
        cc_last4: Last 4 digits of credit card
        holder_name: Name on credit card
    
    Returns:
        Path to saved vault file
    """
    injector = CommerceVault()
    vault = injector.generate_commerce_vault(cc_last4, holder_name)
    return injector.save_vault(vault)


if __name__ == "__main__":
    # Example usage
    logger.info("Generating commerce vault...")
    
    vault_path = generate_and_save_vault(
        cc_last4="4532",
        holder_name="John Doe"
    )
    
    logger.info(f"Vault generated at {vault_path}")
    
    # Print summary
    with open(vault_path, 'r') as f:
        vault_data = json.load(f)
    
    print("\n📦 COMMERCE VAULT SUMMARY:")
    print(f"  Holder: {vault_data['metadata']['holder_name']}")
    print(f"  CC Last4: {vault_data['metadata']['cc_last4']}")
    print(f"  Trust Score: {vault_data['trust_tokens']['account_reputation_score']}")
    print(f"  Total Purchases: {vault_data['trust_tokens']['total_purchases']}")
    print(f"  Account Age: {vault_data['trust_tokens']['account_age_days']} days")
    print(f"\n✅ Vault ready for injection into browser profile")
