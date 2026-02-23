"""
Server-Side Triangulation: Google Analytics Measurement Protocol (GAMP) implementation.
Manages backdated event transmission with 72-hour rolling window strategy.
Level 9: Enhanced TLS fingerprinting with curl_cffi for Chrome 124+ mimicking.
"""
import json
import time
import hashlib
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import deque
import threading
import uuid

# Try to import curl_cffi for Chrome 124+ TLS mimicking
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

# Fallback to standard requests if curl_cffi is not available
import requests


class GAMPTriangulation:
    """
    Google Analytics Measurement Protocol v2 integration for server-side triangulation.
    Implements rolling window strategy to maintain temporal consistency.
    """
    
    GAMP_ENDPOINT = "https://www.google-analytics.com/mp/collect"
    GAMP_DEBUG_ENDPOINT = "https://www.google-analytics.com/debug/mp/collect"
    MAX_BACKDATE_HOURS = 72  # Google's limit for backdated events
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize GAMP Triangulation module.
        
        Args:
            config: Configuration dictionary with measurement_id, api_secret
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # GAMP credentials
        self.measurement_id = self.config.get('measurement_id', '')
        self.api_secret = self.config.get('api_secret', '')
        
        # Rolling window management
        self.event_queue = deque(maxlen=1000)
        self.client_sessions = {}
        self.rolling_window = []
        self.lock = threading.Lock()
        
        # Veritas V5: TLS Hardening - Strict curl_cffi enforcement
        self.use_curl_cffi = CURL_CFFI_AVAILABLE
        if self.use_curl_cffi:
            self.logger.info("✓ [VERITAS V5] curl_cffi enabled - Chrome 124+ TLS mimicking ACTIVE")
        else:
            self.logger.error("✗ [VERITAS V5] curl_cffi NOT AVAILABLE - TLS hardening DISABLED")
            self.logger.error("✗ [VERITAS V5] Install with: pip install curl_cffi")
            self.logger.error("✗ [VERITAS V5] Ghost Signal operations will be ABORTED (no fallback)")
        
        # Validate configuration
        if not self.measurement_id or not self.api_secret:
            self.logger.warning("GAMP credentials not configured")
    
    def send_event(self, client_id: str, 
                   timestamp: Optional[datetime] = None,
                   event_name: str = "page_view",
                   event_params: Optional[Dict] = None) -> bool:
        """
        Send a backdated event to Google Analytics.
        
        Args:
            client_id: Google Analytics client ID (from _ga cookie)
            timestamp: Backdated timestamp for the event
            event_name: Name of the event to track
            event_params: Additional event parameters
            
        Returns:
            bool: Success status
        """
        try:
            # Validate timestamp backdating limit
            if timestamp:
                hours_ago = (datetime.utcnow() - timestamp).total_seconds() / 3600
                
                if hours_ago > self.MAX_BACKDATE_HOURS:
                    # Implement rolling window strategy
                    return self._rolling_triangulation(client_id, timestamp, event_name, event_params)
            
            # Prepare event payload
            payload = self._prepare_payload(client_id, timestamp, event_name, event_params)
            
            # Send to GAMP endpoint
            response = self._send_to_gamp(payload)
            
            if response:
                self.logger.info(f"GAMP event sent: {event_name} for client {client_id[:8]}...")
                
                # Store in event queue
                with self.lock:
                    self.event_queue.append({
                        'client_id': client_id,
                        'timestamp': timestamp or datetime.utcnow(),
                        'event': event_name,
                        'sent_at': datetime.utcnow()
                    })
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"GAMP send failed: {e}")
            return False
    
    def _prepare_payload(self, client_id: str,
                         timestamp: Optional[datetime],
                         event_name: str,
                         event_params: Optional[Dict]) -> Dict:
        """Prepare GAMP payload with proper formatting."""
        
        # Base payload structure
        payload = {
            "client_id": client_id,
            "events": [
                {
                    "name": event_name,
                    "params": event_params or {}
                }
            ]
        }
        
        # Add timestamp if backdating
        if timestamp:
            # Convert to microseconds
            timestamp_micros = int(timestamp.timestamp() * 1000000)
            payload["timestamp_micros"] = timestamp_micros
        
        # Add session management
        session_id = self._get_or_create_session(client_id)
        payload["events"][0]["params"]["session_id"] = session_id
        payload["events"][0]["params"]["engagement_time_msec"] = "100"
        
        # Add user properties
        payload["user_properties"] = {
            "age_category": {
                "value": "established"
            }
        }
        
        return payload
    
    def _send_to_gamp(self, payload: Dict, debug: bool = False) -> bool:
        """
        Send payload to Google Analytics Measurement Protocol.
        
        Veritas V5 Protocol: TLS Hardening
        - Strictly enforce curl_cffi for Chrome 124+ TLS mimicking
        - Hardcode impersonate="chrome124" parameter
        - Abort if curl_cffi fails (no fallback to standard requests)
        - Better to send nothing than to send a Python-fingerprinted packet
        """
        try:
            # Veritas V5: Strict curl_cffi enforcement - no fallback allowed
            if not self.use_curl_cffi:
                self.logger.error("[TLS HARDENING] curl_cffi is not available - ABORTING")
                self.logger.error("[TLS HARDENING] Install curl_cffi to avoid Python fingerprinting")
                self.logger.error("[TLS HARDENING] Command: pip install curl_cffi")
                return False
            
            # Select endpoint
            endpoint = self.GAMP_DEBUG_ENDPOINT if debug else self.GAMP_ENDPOINT
            
            # Build URL with parameters
            url = f"{endpoint}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"
            
            # Send POST request with Chrome 124+ TLS mimicking
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            
            # Veritas V5: Use curl_cffi to mimic Chrome 124+ TLS fingerprint (HARDCODED)
            try:
                response = curl_requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10,
                    # Veritas V5: HARDCODED - Mimic Chrome 124 TLS/JA3 fingerprint
                    # Note: chrome124 is deliberately hardcoded per Veritas V5 protocol requirements
                    # to maintain consistent TLS fingerprinting. Update only when protocol requires.
                    impersonate="chrome124"
                )
                
                self.logger.debug(f"[TLS HARDENING] Request sent with Chrome 124 TLS fingerprint")
                
            except Exception as curl_error:
                # Veritas V5: No fallback - abort on curl_cffi failure
                self.logger.error(f"[TLS HARDENING] curl_cffi request failed: {curl_error}")
                self.logger.error("[TLS HARDENING] ABORTING - Will not fallback to standard requests")
                return False
            
            # Check response
            if debug:
                # Debug endpoint returns validation results
                result = response.json()
                if result.get('validationMessages'):
                    self.logger.warning(f"GAMP validation errors: {result['validationMessages']}")
                    return False
            
            return response.status_code in [200, 204]
            
        except Exception as e:
            self.logger.error(f"[TLS HARDENING] GAMP request failed: {e}")
            return False
    
    def _rolling_triangulation(self, client_id: str,
                               timestamp: datetime,
                               event_name: str,
                               event_params: Optional[Dict]) -> bool:
        """
        Implement rolling triangulation for events beyond 72-hour limit.
        Creates intermediate anchor points to maintain continuity.
        """
        try:
            self.logger.info("Initiating rolling triangulation strategy")
            
            # Calculate required intermediate points
            now = datetime.utcnow()
            total_hours = (now - timestamp).total_seconds() / 3600
            num_windows = int(total_hours / self.MAX_BACKDATE_HOURS) + 1
            
            # Generate intermediate timestamps
            intermediate_points = []
            current_ts = timestamp
            
            for i in range(num_windows):
                window_end = min(
                    current_ts + timedelta(hours=self.MAX_BACKDATE_HOURS - 1),
                    now
                )
                
                intermediate_points.append({
                    'start': current_ts,
                    'end': window_end,
                    'anchor': current_ts + timedelta(hours=self.MAX_BACKDATE_HOURS / 2)
                })
                
                current_ts = window_end
            
            # Send events for each window
            success_count = 0
            
            for window in intermediate_points:
                # Create bridging event
                bridge_params = event_params.copy() if event_params else {}
                bridge_params['window_index'] = intermediate_points.index(window)
                bridge_params['is_bridge'] = True
                
                # Send with anchor timestamp
                if self.send_event(client_id, window['anchor'], 
                                 f"bridge_{event_name}", bridge_params):
                    success_count += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
            
            # Send final target event
            if self.send_event(client_id, intermediate_points[-1]['end'],
                             event_name, event_params):
                success_count += 1
            
            self.logger.info(f"Rolling triangulation complete: {success_count}/{len(intermediate_points)+1} events sent")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Rolling triangulation failed: {e}")
            return False
    
    def _get_or_create_session(self, client_id: str) -> str:
        """Get or create a session ID for the client."""
        with self.lock:
            if client_id not in self.client_sessions:
                # Generate session ID based on client ID and timestamp
                session_data = f"{client_id}{int(time.time())}"
                session_id = hashlib.md5(session_data.encode()).hexdigest()[:16]
                self.client_sessions[client_id] = {
                    'session_id': session_id,
                    'created': datetime.utcnow(),
                    'events': 0
                }
            
            self.client_sessions[client_id]['events'] += 1
            return self.client_sessions[client_id]['session_id']
    
    def batch_send(self, events: List[Dict]) -> int:
        """
        Send multiple events in batch mode.
        
        Args:
            events: List of event dictionaries with client_id, timestamp, event_name, params
            
        Returns:
            int: Number of successfully sent events
        """
        success_count = 0
        
        for event in events:
            if self.send_event(
                client_id=event['client_id'],
                timestamp=event.get('timestamp'),
                event_name=event.get('event_name', 'page_view'),
                event_params=event.get('params')
            ):
                success_count += 1
            
            # Rate limiting
            time.sleep(0.05)
        
        return success_count
    
    def generate_organic_events(self, client_id: str,
                               start_date: datetime,
                               end_date: datetime,
                               daily_events: int = 7) -> List[Dict]:
        """
        Generate organic-looking event patterns for a date range.
        
        Level 9: Generates 5-10 events per day (default 7) with organic distribution
        to avoid flooding and maintain natural user behavior patterns.
        
        Args:
            client_id: Google Analytics client ID
            start_date: Start of date range
            end_date: End of date range  
            daily_events: Average events per day (Level 9 default: 7, range: 5-10)
            
        Returns:
            List of event dictionaries
        """
        events = []
        current_date = start_date
        
        # Event type distribution
        event_types = [
            ('page_view', 0.4),
            ('scroll', 0.2),
            ('click', 0.15),
            ('video_start', 0.05),
            ('form_submit', 0.05),
            ('file_download', 0.05),
            ('user_engagement', 0.1)
        ]
        
        while current_date < end_date:
            # Level 9: Vary daily events organically between 5-10 events
            # Use Gaussian distribution centered on daily_events with controlled variance
            num_events = max(5, min(10, int(random.gauss(daily_events, 1.5))))
            
            for _ in range(num_events):
                # Random time within the day
                hour = random.gauss(14, 4)  # Peak around 2 PM
                hour = max(0, min(23, int(hour)))
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                
                event_time = current_date.replace(hour=hour, minute=minute, second=second)
                
                # Select event type based on distribution
                rand_val = random.random()
                cumulative = 0
                selected_event = 'page_view'
                
                for event_type, probability in event_types:
                    cumulative += probability
                    if rand_val < cumulative:
                        selected_event = event_type
                        break
                
                # Generate event parameters
                params = self._generate_event_params(selected_event)
                
                events.append({
                    'client_id': client_id,
                    'timestamp': event_time,
                    'event_name': selected_event,
                    'params': params
                })
            
            current_date += timedelta(days=1)
        
        # Sort by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        return events
    
    def _generate_event_params(self, event_type: str) -> Dict:
        """Generate realistic parameters for different event types."""
        import random
        
        params = {
            'page_location': f'https://example.com/page{random.randint(1, 50)}',
            'page_referrer': random.choice(['https://google.com', 'https://facebook.com', 'direct']),
        }
        
        if event_type == 'scroll':
            params['percent_scrolled'] = random.choice([25, 50, 75, 90, 100])
        
        elif event_type == 'click':
            params['link_text'] = random.choice(['Learn More', 'Buy Now', 'Contact Us'])
            params['link_url'] = f'https://example.com/action{random.randint(1, 20)}'
        
        elif event_type == 'video_start':
            params['video_title'] = f'Video {random.randint(1, 100)}'
            params['video_duration'] = random.randint(30, 600)
        
        elif event_type == 'form_submit':
            params['form_name'] = random.choice(['contact', 'newsletter', 'registration'])
        
        elif event_type == 'file_download':
            params['file_name'] = f'document{random.randint(1, 50)}.pdf'
            params['file_extension'] = 'pdf'
        
        return params
    
    def validate_configuration(self) -> bool:
        """Validate GAMP configuration by sending a debug event."""
        try:
            test_payload = {
                "client_id": str(uuid.uuid4()),
                "events": [
                    {
                        "name": "test_event",
                        "params": {
                            "test": True
                        }
                    }
                ]
            }
            
            return self._send_to_gamp(test_payload, debug=True)
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False


# Level 9: GhostSignalInjector alias for backward compatibility
class GhostSignalInjector(GAMPTriangulation):
    """
    Ghost Signal Injector for Level 9 operations.
    Uses curl_cffi to mimic Chrome 124+ TLS fingerprints for undetectable server-side triangulation.
    
    This is an alias/wrapper for GAMPTriangulation to maintain backward compatibility
    while providing Level 9 enhancements.
    """
    pass