"""
Safety Validator: Time synchronization validation and recovery mechanisms.
Ensures system clock accuracy before and after operations.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import time
import subprocess

try:
    import requests
except ImportError:
    requests = None

try:
    from dateutil.parser import parse as dateutil_parse
except ImportError:
    dateutil_parse = None
    logging.getLogger(__name__).warning(
        "python-dateutil not installed. Install: pip install python-dateutil"
    )


class SafetyValidator:
    """
    Validates system time synchronization and provides recovery mechanisms.
    Critical for ensuring temporal operations don't cause permanent desync.
    """
    
    DEFAULT_TIME_APIS = [
        "http://worldtimeapi.org/api/ip",
        "http://worldclockapi.com/api/json/utc/now",
        "https://timeapi.io/api/Time/current/zone?timeZone=UTC"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Safety Validator with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.time_api = self.config.get('time_api', self.DEFAULT_TIME_APIS[0])
        self.max_skew = self.config.get('max_skew_seconds', 5)
        self.rollback_on_error = self.config.get('rollback_on_error', True)
        
        # State tracking
        self.last_validation = None
        self.validation_history = []
        self.error_count = 0
    
    def validate_time_sync(self, strict: bool = True) -> bool:
        """
        Validate that system time is synchronized with world time.
        
        Args:
            strict: If True, enforce max_skew limit
            
        Returns:
            bool: True if time is synchronized within tolerance
        """
        try:
            # Get server time
            server_time = self._get_server_time()
            
            if not server_time:
                self.logger.warning("Could not retrieve server time")
                return not strict
            
            # Get local time
            local_time = datetime.utcnow()
            
            # Calculate skew
            skew_seconds = abs((server_time - local_time).total_seconds())
            
            # Log validation
            self.validation_history.append({
                'timestamp': datetime.utcnow(),
                'server_time': server_time,
                'local_time': local_time,
                'skew_seconds': skew_seconds,
                'passed': skew_seconds <= self.max_skew
            })
            
            self.last_validation = datetime.utcnow()
            
            if skew_seconds > self.max_skew:
                self.logger.warning(f"Time skew detected: {skew_seconds:.2f} seconds")
                
                if strict:
                    self.error_count += 1
                    return False
            else:
                self.logger.info(f"Time sync validated: skew {skew_seconds:.2f}s")
                self.error_count = 0
            
            return True
            
        except Exception as e:
            self.logger.error(f"Time validation failed: {e}")
            return not strict
    
    def _get_server_time(self) -> Optional[datetime]:
        """Retrieve current time from external API."""
        
        # Try primary API
        server_time = self._query_time_api(self.time_api)
        if server_time:
            return server_time
        
        # Fallback to other APIs
        for api_url in self.DEFAULT_TIME_APIS:
            if api_url != self.time_api:
                server_time = self._query_time_api(api_url)
                if server_time:
                    return server_time
        
        return None
    
    def _query_time_api(self, api_url: str) -> Optional[datetime]:
        """Query a specific time API."""
        try:
            response = requests.get(api_url, timeout=5)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Parse based on API format
            _parse = dateutil_parse or (lambda x: datetime.fromisoformat(x.replace("Z", "+00:00")))
            if 'worldtimeapi.org' in api_url:
                return _parse(data['datetime'])
            elif 'worldclockapi.com' in api_url:
                return _parse(data['currentDateTime'])
            elif 'timeapi.io' in api_url:
                return _parse(data['dateTime'])
            else:
                # Try common fields
                for field in ['datetime', 'time', 'utc', 'timestamp']:
                    if field in data:
                        return _parse(data[field])
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Time API query failed for {api_url}: {e}")
            return None
    
    def continuous_validation(self, interval: int = 300) -> bool:
        """
        Perform continuous time validation at specified interval.
        
        Args:
            interval: Seconds between validations
            
        Returns:
            bool: True if should continue, False if critical error
        """
        if not self.last_validation:
            return self.validate_time_sync()
        
        elapsed = (datetime.utcnow() - self.last_validation).total_seconds()
        
        if elapsed >= interval:
            return self.validate_time_sync()
        
        return True
    
    def auto_correct_time(self) -> bool:
        """Attempt to auto-correct system time if skew detected."""
        try:
            # Get accurate server time
            server_time = self._get_server_time()
            
            if not server_time:
                self.logger.error("Cannot auto-correct: no server time available")
                return False
            
            # Check current skew
            local_time = datetime.utcnow()
            skew_seconds = (server_time - local_time).total_seconds()
            
            if abs(skew_seconds) <= self.max_skew:
                self.logger.info("Time already within tolerance")
                return True
            
            self.logger.info(f"Auto-correcting time skew of {skew_seconds:.2f} seconds")
            
            # Use Windows time adjustment
            if abs(skew_seconds) < 3600:  # Less than 1 hour
                # Use w32tm for small adjustments
                return self._adjust_time_gradually(skew_seconds)
            else:
                # Use SetSystemTime for large adjustments
                return self._set_system_time(server_time)
            
        except Exception as e:
            self.logger.error(f"Auto-correction failed: {e}")
            return False
    
    def _adjust_time_gradually(self, skew_seconds: float) -> bool:
        """Gradually adjust time using w32tm."""
        try:
            # Configure w32tm for manual peer
            subprocess.run([
                'w32tm', '/config',
                '/manualpeerlist:time.windows.com',
                '/syncfromflags:manual',
                '/update'
            ], capture_output=True, timeout=30)
            
            # Force sync
            result = subprocess.run(['w32tm', '/resync', '/force'],
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info("Gradual time adjustment initiated")
                
                # Wait and verify
                time.sleep(2)
                return self.validate_time_sync(strict=False)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Gradual adjustment failed: {e}")
            return False
    
    def _set_system_time(self, target_time: datetime) -> bool:
        """Set system time directly using kernel32."""
        try:
            import ctypes
            from core.genesis import SYSTEMTIME
            
            kernel32 = ctypes.windll.kernel32
            
            # Create SYSTEMTIME structure
            st = SYSTEMTIME()
            st.wYear = target_time.year
            st.wMonth = target_time.month
            st.wDay = target_time.day
            st.wHour = target_time.hour
            st.wMinute = target_time.minute
            st.wSecond = target_time.second
            st.wMilliseconds = target_time.microsecond // 1000
            st.wDayOfWeek = (target_time.weekday() + 1) % 7
            
            # Set time
            result = kernel32.SetSystemTime(ctypes.byref(st))
            
            if result:
                self.logger.info("System time corrected successfully")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Direct time set failed: {e}")
            return False
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Generate validation report with statistics."""
        
        if not self.validation_history:
            return {
                'status': 'no_data',
                'validations': 0
            }
        
        successful = sum(1 for v in self.validation_history if v['passed'])
        failed = len(self.validation_history) - successful
        
        avg_skew = sum(v['skew_seconds'] for v in self.validation_history) / len(self.validation_history)
        max_skew = max(v['skew_seconds'] for v in self.validation_history)
        
        return {
            'status': 'healthy' if self.error_count == 0 else 'degraded',
            'validations': len(self.validation_history),
            'successful': successful,
            'failed': failed,
            'average_skew': avg_skew,
            'max_skew': max_skew,
            'last_validation': self.last_validation,
            'error_count': self.error_count
        }
    
    def emergency_recovery(self) -> bool:
        """Emergency recovery procedure for critical time desync."""
        self.logger.critical("Initiating emergency time recovery")
        
        try:
            # Step 1: Enable W32Time service
            subprocess.run(['sc', 'config', 'w32time', 'start=', 'auto'],
                         capture_output=True, timeout=30)
            subprocess.run(['net', 'start', 'w32time'],
                         capture_output=True, timeout=30)
            
            # Step 2: Configure multiple NTP servers
            ntp_servers = [
                'time.windows.com',
                'time.nist.gov',
                'pool.ntp.org'
            ]
            
            subprocess.run([
                'w32tm', '/config',
                f'/manualpeerlist:{" ".join(ntp_servers)}',
                '/syncfromflags:manual',
                '/reliable:yes',
                '/update'
            ], capture_output=True, timeout=30)
            
            # Step 3: Force immediate sync
            subprocess.run(['w32tm', '/resync', '/force'],
                         capture_output=True, timeout=30)
            
            # Step 4: Wait and validate
            time.sleep(5)
            
            if self.validate_time_sync(strict=False):
                self.logger.info("Emergency recovery successful")
                self.error_count = 0
                return True
            
            # Step 5: Manual correction as last resort
            return self.auto_correct_time()
            
        except Exception as e:
            self.logger.critical(f"Emergency recovery failed: {e}")
            return False