#!/usr/bin/env python3
"""
Test suite for MultiPSPProcessor integration in purchase_history_engine.py

Tests:
1. MultiPSPProcessor initialization and processor selection
2. Transaction distribution across processors
3. Merchant-specific processor assignment
4. Processor statistics generation
"""

import sys
import unittest
from pathlib import Path

# Add the iso config path to sys.path
iso_path = Path(__file__).parent.parent / "iso" / "config" / "includes.chroot" / "opt" / "titan" / "core"
sys.path.insert(0, str(iso_path.parent.parent.parent.parent))

try:
    from purchase_history_engine import (
        PSPProcessor,
        MultiPSPProcessor,
        CardHolderData,
        PurchaseHistoryConfig,
    )
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Attempting to import from: {sys.path[0]}")
    # Fallback: try direct import for testing
    sys.exit(1)


class TestPSPProcessor(unittest.TestCase):
    """Test PSPProcessor dataclass"""

    def test_psp_processor_creation(self):
        """Test PSPProcessor can be created with correct attributes"""
        processor = PSPProcessor(name="Stripe", priority=10, success_rate=0.99)
        self.assertEqual(processor.name, "Stripe")
        self.assertEqual(processor.priority, 10)
        self.assertEqual(processor.success_rate, 0.99)
        self.assertEqual(len(processor.transactions), 0)

    def test_record_transaction(self):
        """Test recording transactions on PSPProcessor"""
        processor = PSPProcessor(name="PayPal", priority=9, success_rate=0.98)
        processor.record_transaction(amount=99.99, timestamp=1234567890.0, card_id="4532")
        self.assertEqual(processor.get_transaction_count(), 1)
        self.assertAlmostEqual(processor.get_total_volume(), 99.99, places=2)

    def test_multiple_transactions(self):
        """Test multiple transactions on PSPProcessor"""
        processor = PSPProcessor(name="Adyen", priority=9, success_rate=0.98)
        processor.record_transaction(amount=50.00, timestamp=1234567890.0, card_id="4532")
        processor.record_transaction(amount=75.50, timestamp=1234567900.0, card_id="4532")
        processor.record_transaction(amount=24.99, timestamp=1234567910.0, card_id="4532")
        self.assertEqual(processor.get_transaction_count(), 3)
        self.assertAlmostEqual(processor.get_total_volume(), 150.49, places=2)


class TestMultiPSPProcessor(unittest.TestCase):
    """Test MultiPSPProcessor coordination layer"""

    def test_initialization_new_profile(self):
        """Test MultiPSPProcessor initialization for new profile"""
        multi_psp = MultiPSPProcessor(profile_age_days=3)
        # New profiles (< 7 days) should have 3 processors
        self.assertEqual(len(multi_psp.selected_processors), 3)
        self.assertGreater(multi_psp.processor_diversity_score, 0)
        self.assertLessEqual(multi_psp.processor_diversity_score, 1.0)

    def test_initialization_young_profile(self):
        """Test MultiPSPProcessor initialization for young profile"""
        multi_psp = MultiPSPProcessor(profile_age_days=15)
        # Young profiles (7-30 days) should have 5 processors
        self.assertEqual(len(multi_psp.selected_processors), 5)

    def test_initialization_mature_profile(self):
        """Test MultiPSPProcessor initialization for mature profile"""
        multi_psp = MultiPSPProcessor(profile_age_days=60)
        # Mature profiles (30-90 days) should have 6-7 processors
        self.assertIn(len(multi_psp.selected_processors), [6, 7])

    def test_initialization_established_profile(self):
        """Test MultiPSPProcessor initialization for established profile"""
        multi_psp = MultiPSPProcessor(profile_age_days=120)
        # Established profiles (90+ days) should have 8 processors
        self.assertEqual(len(multi_psp.selected_processors), 8)

    def test_processor_pool(self):
        """Test that processor pool contains expected processors"""
        self.assertEqual(len(MultiPSPProcessor.PROCESSOR_POOL), 15)
        expected_processors = ["stripe", "paypal", "adyen", "braintree"]
        for processor_key in expected_processors:
            self.assertIn(processor_key, MultiPSPProcessor.PROCESSOR_POOL)

    def test_transaction_distribution(self):
        """Test transaction distribution across processors"""
        multi_psp = MultiPSPProcessor(profile_age_days=90)
        distribution = multi_psp._distribute_transactions(100)
        
        # Total transactions should equal requested
        total_distributed = sum(distribution.values())
        self.assertEqual(total_distributed, 100)
        
        # All selected processors should be in distribution
        self.assertEqual(len(distribution), len(multi_psp.selected_processors))

    def test_merchant_processor_mapping(self):
        """Test merchant-specific processor mapping"""
        multi_psp = MultiPSPProcessor(profile_age_days=90)
        
        # Test known merchants
        amazon_processors = multi_psp.get_processors_for_merchant("Amazon")
        self.assertGreater(len(amazon_processors), 0)
        self.assertLessEqual(len(amazon_processors), 4)
        
        # Test default fallback
        default_processors = multi_psp.get_processors_for_merchant("UnknownStore")
        self.assertGreater(len(default_processors), 0)

    def test_processor_assignment(self):
        """Test processor assignment for transactions"""
        multi_psp = MultiPSPProcessor(profile_age_days=90)
        
        # Test multiple assignments
        assignments = []
        for _ in range(10):
            processor = multi_psp.assign_processor_to_transaction("Amazon")
            assignments.append(processor.name)
        
        # Should have some diversity in processor selection
        unique_assignments = len(set(assignments))
        self.assertGreater(unique_assignments, 1)

    def test_processor_statistics(self):
        """Test processor statistics generation"""
        multi_psp = MultiPSPProcessor(profile_age_days=90)
        multi_psp._distribute_transactions(50)
        stats = multi_psp.get_processor_statistics()
        
        # Verify stats structure
        self.assertIn("processor_count", stats)
        self.assertIn("diversity_score", stats)
        self.assertIn("selected_processors", stats)
        self.assertIn("transaction_distribution", stats)
        self.assertIn("coverage_percentage", stats)
        self.assertIn("average_priority", stats)
        
        # Verify stats values
        self.assertEqual(stats["processor_count"], len(multi_psp.selected_processors))
        self.assertGreater(stats["coverage_percentage"], 0)
        self.assertLessEqual(stats["coverage_percentage"], 100)

    def test_tier_selection(self):
        """Test that processor selection follows tier prioritization"""
        multi_psp = MultiPSPProcessor(profile_age_days=90)
        
        # Check that Tier 1 processors are preferred
        processor_names = [p.name for p in multi_psp.selected_processors]
        tier1_count = sum(
            1 for name in processor_names if name in [p.name for p in MultiPSPProcessor.TIER_1_PROCESSORS.values()]
        )
        
        # At least 50% should be Tier 1 for profile age 90
        self.assertGreaterEqual(tier1_count, len(multi_psp.selected_processors) * 0.50)


class TestMultiPSPIntegration(unittest.TestCase):
    """Test integration with PurchaseHistoryConfig"""

    def test_config_creation(self):
        """Test PurchaseHistoryConfig creation for testing"""
        cardholder = CardHolderData(
            full_name="John Doe",
            first_name="John",
            last_name="Doe",
            card_last_four="4532",
            card_network="VISA",
            card_exp_display="12/25",
            billing_address="123 Main St",
            billing_city="New York",
            billing_state="NY",
            billing_zip="10001",
            email="john.doe@example.com",
            phone="555-1234",
        )
        
        config = PurchaseHistoryConfig(
            cardholder=cardholder,
            profile_age_days=90,
            num_purchases=10,
        )
        
        self.assertEqual(config.cardholder.full_name, "John Doe")
        self.assertEqual(config.profile_age_days, 90)
        self.assertEqual(config.num_purchases, 10)

    def test_multi_psp_with_profile_age(self):
        """Test MultiPSPProcessor with various profile ages"""
        ages_and_expected_processor_counts = [
            (3, 3),      # New profile
            (15, 5),     # Young profile
            (60, 6),     # Mature profile
            (120, 8),    # Established profile
        ]
        
        for age, expected_count in ages_and_expected_processor_counts:
            multi_psp = MultiPSPProcessor(profile_age_days=age)
            self.assertEqual(
                len(multi_psp.selected_processors),
                expected_count,
                f"Expected {expected_count} processors for age {age}, got {len(multi_psp.selected_processors)}"
            )


if __name__ == "__main__":
    unittest.main()
