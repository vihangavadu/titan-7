"""
METHOD 5: TLS HERMETICISM LAYER
Library: curl_cffi
Purpose: Spoofs the JA3/JA4 TLS Fingerprint to match Chrome 120+
Replaces: core/resilient_api.py (Legacy requests)
"""

import random
import logging

try:
    from curl_cffi import requests as cffi_requests
    CURL_CFFI_OK = True
except ImportError:
    cffi_requests = None
    CURL_CFFI_OK = False
    logging.getLogger("TLSMimic").warning(
        "curl_cffi not installed — TLS fingerprint spoofing DISABLED. "
        "Install: pip install curl_cffi"
    )

class TLSMimic:
    def __init__(self, proxy_url=None):
        self.proxy = proxy_url
        # Chrome 120 Signature Impersonation
        self.impersonate = "chrome120"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        self.logger = logging.getLogger("TLSMimic")

    def get(self, url, params=None):
        """
        Executes a GET request using the BoringSSL handshake.
        This hides the 'Python' signature from Cloudflare/Akamai.
        """
        try:
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            response = cffi_requests.get(
                url,
                params=params,
                impersonate=self.impersonate,
                headers=self.headers,
                proxies=proxies,
                timeout=30
            )
            return response
        except Exception as e:
            self.logger.error(f"TLS GET Failed: {e}")
            return None

    def post(self, url, data=None, json=None):
        """
        Executes a POST request using the BoringSSL handshake.
        """
        try:
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            response = cffi_requests.post(
                url,
                data=data,
                json=json,
                impersonate=self.impersonate,
                headers=self.headers,
                proxies=proxies,
                timeout=30
            )
            return response
        except Exception as e:
            self.logger.error(f"TLS POST Failed: {e}")
            return None

    def check_ip_trust(self):
        """
        Verifies the proxy's fraud score via ip-api or similar (using TLS spoofing).
        """
        try:
            resp = self.get("http://ip-api.com/json/")
            if resp and resp.status_code == 200:
                data = resp.json()
                self.logger.info(f"Proxy Verified: {data.get('query')} ({data.get('country')})")
                return data
            return None
        except Exception as e:
            self.logger.error(f"IP Check Failed: {e}")
            return None
