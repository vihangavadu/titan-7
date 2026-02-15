"""
LUCID EMPIRE: Blacklist Validator
Objective: Check proxy IP against known fraud and abuse blacklists
Classification: LEVEL 6 AGENCY
"""

import requests
import socket
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlacklistValidator:
    """
    Checks proxy IP addresses against known fraud and abuse blacklists.
    
    Uses multiple sources:
    - AbuseIPDB (if API key available)
    - Local IP reputation check
    - DNS-based blacklists (DNSBL)
    """
    
    def __init__(self, abuseipdb_api_key: Optional[str] = None):
        """
        Initialize the validator
        
        Args:
            abuseipdb_api_key: Optional AbuseIPDB API key for enhanced checks
        """
        self.abuseipdb_api_key = abuseipdb_api_key
        
        # Common DNS-based blacklists
        self.dnsbl_servers = [
            "zen.spamhaus.org",
            "bl.spamcop.net",
            "dnsbl.sorbs.net",
            "b.barracudacentral.org",
            "cbl.abuseat.org",
        ]
        
        # Known datacenter/hosting provider IP ranges (simplified)
        self.datacenter_asns = [
            "AS14061",  # DigitalOcean
            "AS16276",  # OVH
            "AS24940",  # Hetzner
            "AS13335",  # Cloudflare
            "AS16509",  # Amazon AWS
            "AS15169",  # Google
            "AS8075",   # Microsoft
        ]
    
    def check_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """
        Comprehensive IP reputation check
        
        Args:
            ip_address: The IP address to check
            
        Returns:
            Dictionary with:
            - is_blacklisted: bool
            - risk_score: 0-100 (higher = more risky)
            - reports: number of abuse reports
            - checks_passed: list of passed checks
            - checks_failed: list of failed checks
            - recommendations: list of suggestions
        """
        result = {
            'ip': ip_address,
            'is_blacklisted': False,
            'risk_score': 0,
            'reports': 0,
            'last_report': None,
            'checks_passed': [],
            'checks_failed': [],
            'recommendations': [],
            'timestamp': datetime.now().isoformat(),
        }
        
        try:
            # 1. Basic IP validation
            if not self._is_valid_ip(ip_address):
                result['is_blacklisted'] = True
                result['risk_score'] = 100
                result['checks_failed'].append('Invalid IP format')
                return result
            
            result['checks_passed'].append('Valid IP format')
            
            # 2. Check if private/reserved IP
            if self._is_private_ip(ip_address):
                result['risk_score'] += 10
                result['checks_failed'].append('Private/Reserved IP')
                result['recommendations'].append('Use a public proxy IP')
            else:
                result['checks_passed'].append('Public IP')
            
            # 3. Check DNS blacklists
            dnsbl_hits = self._check_dnsbl(ip_address)
            if dnsbl_hits:
                result['risk_score'] += len(dnsbl_hits) * 15
                result['checks_failed'].extend([f"DNSBL: {bl}" for bl in dnsbl_hits])
                result['reports'] = len(dnsbl_hits)
                if result['risk_score'] >= 50:
                    result['is_blacklisted'] = True
            else:
                result['checks_passed'].append('Clean on DNS blacklists')
            
            # 4. Check AbuseIPDB if API key available
            if self.abuseipdb_api_key:
                abuse_result = self._check_abuseipdb(ip_address)
                if abuse_result:
                    result['risk_score'] = max(result['risk_score'], abuse_result.get('abuseConfidenceScore', 0))
                    result['reports'] += abuse_result.get('totalReports', 0)
                    result['last_report'] = abuse_result.get('lastReportedAt')
                    
                    if abuse_result.get('abuseConfidenceScore', 0) > 25:
                        result['checks_failed'].append(f"AbuseIPDB score: {abuse_result.get('abuseConfidenceScore')}%")
                        result['is_blacklisted'] = True
                    else:
                        result['checks_passed'].append('Low AbuseIPDB score')
            
            # 5. Check IP geolocation consistency
            geo_result = self._check_geolocation(ip_address)
            if geo_result:
                result['geo'] = geo_result
                if geo_result.get('is_hosting'):
                    result['risk_score'] += 20
                    result['checks_failed'].append('Datacenter/Hosting IP detected')
                    result['recommendations'].append('Use residential proxy instead')
                else:
                    result['checks_passed'].append('Residential IP')
            
            # 6. Final risk assessment
            if result['risk_score'] >= 75:
                result['is_blacklisted'] = True
                result['recommendations'].append('CRITICAL: Change proxy immediately')
            elif result['risk_score'] >= 50:
                result['recommendations'].append('WARNING: Consider using different proxy')
            elif result['risk_score'] >= 25:
                result['recommendations'].append('CAUTION: Monitor for issues')
            else:
                result['recommendations'].append('OK: Proxy appears clean')
            
            logger.info(f"IP {ip_address} check complete: risk_score={result['risk_score']}")
            
        except Exception as e:
            logger.error(f"Error checking IP {ip_address}: {str(e)}")
            result['checks_failed'].append(f"Check error: {str(e)}")
        
        return result
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            try:
                socket.inet_pton(socket.AF_INET6, ip)
                return True
            except socket.error:
                return False
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private/reserved range"""
        try:
            parts = [int(p) for p in ip.split('.')]
            
            # 10.0.0.0/8
            if parts[0] == 10:
                return True
            
            # 172.16.0.0/12
            if parts[0] == 172 and 16 <= parts[1] <= 31:
                return True
            
            # 192.168.0.0/16
            if parts[0] == 192 and parts[1] == 168:
                return True
            
            # 127.0.0.0/8 (loopback)
            if parts[0] == 127:
                return True
            
            # 0.0.0.0/8
            if parts[0] == 0:
                return True
            
            return False
        except:
            return False
    
    def _check_dnsbl(self, ip: str) -> List[str]:
        """
        Check IP against DNS-based blacklists
        
        Returns list of blacklists the IP appears on
        """
        hits = []
        
        try:
            # Reverse IP for DNSBL lookup
            reversed_ip = '.'.join(reversed(ip.split('.')))
            
            for dnsbl in self.dnsbl_servers:
                try:
                    query = f"{reversed_ip}.{dnsbl}"
                    socket.gethostbyname(query)
                    # If we get a response, IP is blacklisted
                    hits.append(dnsbl)
                    logger.debug(f"IP {ip} found on {dnsbl}")
                except socket.gaierror:
                    # No DNS record = not blacklisted
                    pass
                except Exception as e:
                    logger.debug(f"DNSBL check error for {dnsbl}: {e}")
        except Exception as e:
            logger.warning(f"DNSBL check failed: {e}")
        
        return hits
    
    def _check_abuseipdb(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Check IP against AbuseIPDB API
        
        Requires API key to be set
        """
        if not self.abuseipdb_api_key:
            return None
        
        try:
            response = requests.get(
                'https://api.abuseipdb.com/api/v2/check',
                headers={
                    'Key': self.abuseipdb_api_key,
                    'Accept': 'application/json',
                },
                params={
                    'ipAddress': ip,
                    'maxAgeInDays': 90,
                },
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {})
            else:
                logger.warning(f"AbuseIPDB returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"AbuseIPDB check failed: {e}")
            return None
    
    def _check_geolocation(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Check IP geolocation and detect if it's a datacenter IP
        """
        try:
            response = requests.get(
                f'https://ipinfo.io/{ip}/json',
                timeout=5,
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if hosting provider
                org = data.get('org', '').upper()
                is_hosting = any(
                    keyword in org 
                    for keyword in ['HOSTING', 'DATACENTER', 'CLOUD', 'VPS', 'DIGITALOCEAN', 'AWS', 'AZURE', 'LINODE', 'VULTR', 'OVH']
                )
                
                return {
                    'country': data.get('country'),
                    'region': data.get('region'),
                    'city': data.get('city'),
                    'timezone': data.get('timezone'),
                    'org': data.get('org'),
                    'is_hosting': is_hosting,
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Geolocation check failed: {e}")
            return None
    
    def quick_check(self, ip: str) -> Dict[str, Any]:
        """
        Quick check for pre-flight validation
        
        Returns simplified result for UI display
        """
        full_result = self.check_ip_reputation(ip)
        
        return {
            'ip': ip,
            'status': 'clean' if not full_result['is_blacklisted'] else 'blacklisted',
            'risk_score': full_result['risk_score'],
            'is_safe': full_result['risk_score'] < 50,
            'message': full_result['recommendations'][0] if full_result['recommendations'] else 'Check complete',
        }


# Convenience function
def check_proxy_blacklist(ip_address: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick function to check if an IP is blacklisted
    
    Args:
        ip_address: IP to check
        api_key: Optional AbuseIPDB API key
        
    Returns:
        Dictionary with blacklist status
    """
    validator = BlacklistValidator(api_key)
    return validator.check_ip_reputation(ip_address)


if __name__ == "__main__":
    # Test the validator
    print("LUCID EMPIRE: Blacklist Validator Test")
    print("=" * 50)
    
    validator = BlacklistValidator()
    
    # Test IPs
    test_ips = [
        "8.8.8.8",  # Google DNS (should be clean)
        "192.168.1.1",  # Private IP (should flag)
        "1.1.1.1",  # Cloudflare (clean but datacenter)
    ]
    
    for ip in test_ips:
        print(f"\nChecking: {ip}")
        result = validator.quick_check(ip)
        print(f"  Status: {result['status']}")
        print(f"  Risk Score: {result['risk_score']}")
        print(f"  Safe: {result['is_safe']}")
        print(f"  Message: {result['message']}")
