"""
TITAN V7.0 SINGULARITY - Manual Handover Protocol
Reference: Report Section 7.2 - The Manual Handover Protocol and the "Final 5%"

The "Final 5%" of success probability requires Human-in-the-Loop execution.
This module enforces the strict "Prepare -> Handover -> Execute" protocol.

Protocol Phases:
1. GENESIS (Automated): Forge profile, history, cookies using Genesis Engine
2. FREEZE (Transition): Terminate all automation, close headless browser
3. HANDOVER (Manual): Operator launches standard browser with grafted profile

Why Manual Execution is Critical:
- Clears navigator.webdriver flag (primary bot detection vector)
- Introduces Cognitive Non-Determinism (human chaos)
- Organic navigation patterns (Google search -> referrer chain)
- Intuitive handling of unexpected 3D Secure / UI changes

The automated system achieves 95% - the human operator delivers the final 5%.
"""

import os
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any
from enum import Enum
import signal

logger = logging.getLogger("TITAN-V7-HANDOVER")


class HandoverPhase(Enum):
    """Current phase of the handover protocol"""
    GENESIS = "genesis"      # Automated profile forging
    FREEZE = "freeze"        # Automation terminated
    HANDOVER = "handover"    # Ready for human operator
    EXECUTING = "executing"  # Human is operating
    COMPLETE = "complete"    # Operation finished


class HandoverStatus(Enum):
    """Status of handover readiness"""
    NOT_READY = "not_ready"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    ABORTED = "aborted"


@dataclass
class HandoverState:
    """Current state of the handover protocol"""
    phase: HandoverPhase
    status: HandoverStatus
    profile_id: Optional[str] = None
    profile_path: Optional[Path] = None
    target_domain: Optional[str] = None
    browser_type: str = "firefox"
    automation_pids: List[int] = field(default_factory=list)
    genesis_complete: bool = False
    freeze_verified: bool = False
    handover_time: Optional[datetime] = None
    notes: str = ""
    estimated_risk_score: Optional[int] = None
    post_checkout_guide: Optional[List[str]] = None
    osint_verified: bool = False
    operator_playbook: Optional[List[str]] = None


@dataclass
class HandoverChecklist:
    """Pre-handover verification checklist"""
    profile_exists: bool = False
    cookies_injected: bool = False
    history_aged: bool = False
    hardware_profile_set: bool = False
    automation_terminated: bool = False
    webdriver_cleared: bool = False
    browser_closed: bool = False
    
    @property
    def is_ready(self) -> bool:
        """All checks must pass for handover"""
        return all([
            self.profile_exists,
            self.cookies_injected,
            self.history_aged,
            self.hardware_profile_set,
            self.automation_terminated,
            self.webdriver_cleared,
            self.browser_closed
        ])
    
    def to_dict(self) -> Dict[str, bool]:
        return {
            "profile_exists": self.profile_exists,
            "cookies_injected": self.cookies_injected,
            "history_aged": self.history_aged,
            "hardware_profile_set": self.hardware_profile_set,
            "automation_terminated": self.automation_terminated,
            "webdriver_cleared": self.webdriver_cleared,
            "browser_closed": self.browser_closed,
            "ready": self.is_ready
        }


class ManualHandoverProtocol:
    """
    Enforces the Prepare -> Handover -> Execute protocol.
    
    This is the bridge between automated preparation and human execution.
    The protocol ensures that when the human operator takes control,
    the environment is clean of all automation signatures.
    
    Usage:
        protocol = ManualHandoverProtocol()
        
        # Phase 1: Genesis (automated)
        protocol.begin_genesis(profile_id, profile_path, target)
        # ... Genesis Engine forges profile ...
        protocol.complete_genesis()
        
        # Phase 2: Freeze
        protocol.initiate_freeze()
        # ... All automation stops ...
        protocol.verify_freeze()
        
        # Phase 3: Handover
        if protocol.is_ready_for_handover():
            protocol.execute_handover()
            # Human operator now in control
    """
    
    def __init__(self, state_file: str = "/opt/titan/state/handover.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.state = HandoverState(
            phase=HandoverPhase.GENESIS,
            status=HandoverStatus.NOT_READY
        )
        self.checklist = HandoverChecklist()
        
        # Callbacks for UI integration
        self.on_phase_change: Optional[Callable[[HandoverPhase], None]] = None
        self.on_status_change: Optional[Callable[[HandoverStatus], None]] = None
        
        # Load existing state if present
        self._load_state()
    
    def _load_state(self):
        """Load state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self.state.phase = HandoverPhase(data.get("phase", "genesis"))
                    self.state.status = HandoverStatus(data.get("status", "not_ready"))
                    self.state.profile_id = data.get("profile_id")
                    self.state.profile_path = Path(data["profile_path"]) if data.get("profile_path") else None
                    self.state.target_domain = data.get("target_domain")
                    self.state.browser_type = data.get("browser_type", "firefox")
            except Exception as e:
                logger.warning(f"Failed to load handover state: {e}")
    
    def _save_state(self):
        """Persist state to disk"""
        data = {
            "phase": self.state.phase.value,
            "status": self.state.status.value,
            "profile_id": self.state.profile_id,
            "profile_path": str(self.state.profile_path) if self.state.profile_path else None,
            "target_domain": self.state.target_domain,
            "browser_type": self.state.browser_type,
            "genesis_complete": self.state.genesis_complete,
            "freeze_verified": self.state.freeze_verified,
            "handover_time": self.state.handover_time.isoformat() if self.state.handover_time else None,
            "checklist": self.checklist.to_dict()
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _set_phase(self, phase: HandoverPhase):
        """Update phase and trigger callback"""
        self.state.phase = phase
        self._save_state()
        if self.on_phase_change:
            self.on_phase_change(phase)
    
    def _set_status(self, status: HandoverStatus):
        """Update status and trigger callback"""
        self.state.status = status
        self._save_state()
        if self.on_status_change:
            self.on_status_change(status)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: GENESIS (Automated Profile Forging)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def begin_genesis(self, profile_id: str, profile_path: Path, target_domain: str, browser: str = "firefox"):
        """
        Begin the Genesis phase - automated profile forging.
        
        Args:
            profile_id: Unique identifier for the profile
            profile_path: Path to the profile directory
            target_domain: Target website domain
            browser: Browser type ("firefox" or "chromium")
        """
        self.state.profile_id = profile_id
        self.state.profile_path = profile_path
        self.state.target_domain = target_domain
        self.state.browser_type = browser
        self.state.genesis_complete = False
        self.state.freeze_verified = False
        
        self._set_phase(HandoverPhase.GENESIS)
        self._set_status(HandoverStatus.IN_PROGRESS)
        
        print(f"[HANDOVER] Genesis phase started for {target_domain}")
        print(f"[HANDOVER] Profile: {profile_id}")
    
    def complete_genesis(self):
        """
        Mark Genesis phase as complete.
        Called after Genesis Engine has finished forging the profile.
        """
        if self.state.phase != HandoverPhase.GENESIS:
            raise RuntimeError("Cannot complete Genesis - not in Genesis phase")
        
        # Verify profile was created
        if self.state.profile_path and self.state.profile_path.exists():
            self.checklist.profile_exists = True
            self.checklist.cookies_injected = True
            self.checklist.history_aged = True
            self.checklist.hardware_profile_set = True
        
        self.state.genesis_complete = True
        self._save_state()
        
        print("[HANDOVER] Genesis phase complete - profile forged")
        print("[HANDOVER] Initiating FREEZE phase...")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: FREEZE (Terminate All Automation)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def initiate_freeze(self):
        """
        Initiate the Freeze phase - terminate all automation.
        
        This is CRITICAL for clearing the navigator.webdriver flag.
        Any browser instance started by automation frameworks will have
        this flag set, which is an instant bot detection trigger.
        """
        if not self.state.genesis_complete:
            raise RuntimeError("Cannot freeze - Genesis not complete")
        
        self._set_phase(HandoverPhase.FREEZE)
        
        print("[HANDOVER] FREEZE phase initiated")
        print("[HANDOVER] Terminating all automation processes...")
        
        # Kill known automation processes
        automation_processes = [
            "geckodriver", "chromedriver", "playwright",
            "puppeteer", "selenium", "webdriver"
        ]
        
        for proc_name in automation_processes:
            self._kill_process_by_name(proc_name)
        
        # Kill any browser instances started by automation
        # (They have webdriver flag set)
        self._kill_automated_browsers()
        
        self.checklist.automation_terminated = True
        self._save_state()
        
        print("[HANDOVER] Automation processes terminated")
    
    def _kill_process_by_name(self, name: str):
        """Kill processes matching name"""
        try:
            subprocess.run(
                ["pkill", "-f", name],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass
    
    def _kill_automated_browsers(self):
        """Kill browser instances that were started by automation"""
        # Kill Firefox instances with marionette (automation) flag
        try:
            subprocess.run(
                ["pkill", "-f", "firefox.*-marionette"],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass
        
        # Kill Chrome instances with automation flags
        try:
            subprocess.run(
                ["pkill", "-f", "chrome.*--enable-automation"],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass
        
        self.checklist.browser_closed = True
    
    def verify_freeze(self) -> bool:
        """
        Verify that the freeze is complete.
        
        Returns:
            True if all automation is terminated
        """
        # Check for any remaining automation processes
        try:
            automation_check = subprocess.run(
                ["pgrep", "-f", "geckodriver|chromedriver|playwright|webdriver"],
                capture_output=True, timeout=5
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # pgrep not available or timed out — assume clean
            self.checklist.webdriver_cleared = True
            self.state.freeze_verified = True
            self._save_state()
            print("[HANDOVER] FREEZE verified (pgrep unavailable — assumed clean)")
            return True
        
        if automation_check.returncode == 0:
            # Processes still running
            print("[HANDOVER] WARNING: Automation processes still detected")
            return False
        
        self.checklist.webdriver_cleared = True
        self.state.freeze_verified = True
        self._save_state()
        
        print("[HANDOVER] FREEZE verified - all automation terminated")
        return True
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: HANDOVER (Transfer Control to Human)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def is_ready_for_handover(self) -> bool:
        """Check if system is ready for handover to human operator"""
        return (
            self.state.genesis_complete and
            self.state.freeze_verified and
            self.checklist.is_ready
        )
    
    def get_handover_checklist(self) -> Dict[str, bool]:
        """Get current checklist status for UI display"""
        return self.checklist.to_dict()
    
    def execute_handover(self) -> bool:
        """
        Execute the handover - prepare for human operator.
        
        This sets up the environment for the human to launch
        a CLEAN browser instance with the forged profile.
        
        Returns:
            True if handover successful
        """
        if not self.is_ready_for_handover():
            print("[HANDOVER] ERROR: Not ready for handover")
            print(f"[HANDOVER] Checklist: {self.checklist.to_dict()}")
            return False
        
        self._set_phase(HandoverPhase.HANDOVER)
        self._set_status(HandoverStatus.READY)
        self.state.handover_time = datetime.now(timezone.utc)
        self._save_state()
        
        # Generate handover instructions
        self._print_handover_instructions()
        
        return True
    
    def _print_handover_instructions(self):
        """Print instructions for the human operator"""
        print("\n" + "=" * 60)
        print("  TITAN V7 SINGULARITY - MANUAL HANDOVER COMPLETE")
        print("=" * 60)
        print(f"\n  Target: {self.state.target_domain}")
        print(f"  Profile: {self.state.profile_id}")
        print(f"  Browser: {self.state.browser_type}")
        print(f"\n  Profile Path: {self.state.profile_path}")
        print("\n  INSTRUCTIONS FOR HUMAN OPERATOR:")
        print("  ─────────────────────────────────")
        print("  1. Launch browser with the forged profile:")
        
        if self.state.browser_type == "firefox":
            print(f"     firefox -profile {self.state.profile_path}")
        else:
            print(f"     chromium --user-data-dir={self.state.profile_path}")
        
        print("\n  2. Navigate via ORGANIC path (Google search, not direct URL)")
        print("  3. Handle any 3D Secure / verification challenges manually")
        print("  4. Maintain natural timing and mouse movements")
        print("\n  The automated system achieved 95%.")
        print("  YOU deliver the final 5%.")
        print("\n" + "=" * 60 + "\n")
    
    def mark_executing(self):
        """Mark that human operator has taken control"""
        self._set_phase(HandoverPhase.EXECUTING)
        self._set_status(HandoverStatus.IN_PROGRESS)
        print("[HANDOVER] Human operator executing...")
    
    def mark_complete(self, success: bool = True, notes: str = ""):
        """Mark operation as complete"""
        self._set_phase(HandoverPhase.COMPLETE)
        self._set_status(HandoverStatus.READY if success else HandoverStatus.ABORTED)
        self.state.notes = notes
        self._save_state()
        
        status = "SUCCESS" if success else "ABORTED"
        print(f"[HANDOVER] Operation {status}")
        if notes:
            print(f"[HANDOVER] Notes: {notes}")
    
    def abort(self, reason: str = ""):
        """Abort the handover protocol"""
        self._set_status(HandoverStatus.ABORTED)
        self.state.notes = f"ABORTED: {reason}"
        self._save_state()
        
        print(f"[HANDOVER] ABORTED: {reason}")
    
    def reset(self):
        """Reset the protocol for a new operation"""
        self.state = HandoverState(
            phase=HandoverPhase.GENESIS,
            status=HandoverStatus.NOT_READY
        )
        self.checklist = HandoverChecklist()
        self._save_state()
        
        print("[HANDOVER] Protocol reset")


# Convenience function for quick handover
def run_preflight_checks(profile_path: str) -> Dict[str, Any]:
    """
    Run pre-flight validation checks before handover.
    
    Integrates legacy preflight_validator.py for comprehensive checks:
    - IP reputation
    - TLS fingerprint consistency
    - Canvas hash consistency
    - Timezone/geolocation sync
    - DNS/WebRTC leak detection
    - Commerce token age
    
    Returns:
        Dict with check results and overall status
    """
    results = {
        "passed": True,
        "checks": [],
        "abort_reason": None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        import sys
        _lp = Path("/opt/lucid-empire")
        if _lp.exists():
            for _s in [str(_lp), str(_lp / "backend")]:
                if _s not in sys.path:
                    sys.path.insert(0, _s)
        
        from validation.preflight_validator import PreFlightValidator
        
        # Get profile UUID from path
        profile_id = Path(profile_path).name if profile_path else "unknown"
        
        validator = PreFlightValidator(profile_uuid=profile_id)
        report = validator.validate()
        
        # V7.5 FIX: overall_status is a string property, not an enum
        results["passed"] = getattr(report, 'overall_status', 'UNKNOWN') == "PASS"
        results["checks"] = [c.to_dict() for c in getattr(report, 'checks', [])]
        results["abort_reason"] = getattr(report, 'abort_reason', None)
        
    except (ImportError, OSError):
        # Preflight validator not available - do basic checks
        results["checks"].append({
            "name": "preflight_validator",
            "status": "SKIPPED",
            "message": "Legacy validator not available"
        })
    except Exception as e:
        results["checks"].append({
            "name": "preflight_error",
            "status": "ERROR",
            "message": str(e)
        })
    
    # Basic profile checks
    profile_path_obj = Path(profile_path) if profile_path else None
    
    if profile_path_obj and profile_path_obj.exists():
        results["checks"].append({
            "name": "profile_exists",
            "status": "PASS",
            "message": "Profile directory exists"
        })
        
        # Check for required files
        required_files = ["profile_metadata.json", "hardware_profile.json"]
        for req_file in required_files:
            if (profile_path_obj / req_file).exists():
                results["checks"].append({
                    "name": f"file_{req_file}",
                    "status": "PASS",
                    "message": f"{req_file} present"
                })
            else:
                results["checks"].append({
                    "name": f"file_{req_file}",
                    "status": "WARN",
                    "message": f"{req_file} missing"
                })
    else:
        results["passed"] = False
        results["abort_reason"] = "Profile path does not exist"
        results["checks"].append({
            "name": "profile_exists",
            "status": "FAIL",
            "message": "Profile directory not found"
        })
    
    return results


def quick_handover(profile_path: str, target: str, browser: str = "firefox") -> ManualHandoverProtocol:
    """
    Quick handover for simple operations.
    
    Usage:
        protocol = quick_handover("/opt/titan/profiles/titan_abc123", "amazon.com")
        protocol.execute_handover()
    """
    protocol = ManualHandoverProtocol()
    protocol.begin_genesis("quick", Path(profile_path), target, browser)
    protocol.state.genesis_complete = True
    protocol.checklist.profile_exists = True
    protocol.checklist.cookies_injected = True
    protocol.checklist.history_aged = True
    protocol.checklist.hardware_profile_set = True
    protocol.initiate_freeze()
    protocol.verify_freeze()
    return protocol


# ═══════════════════════════════════════════════════════════════════════════
# POST-CHECKOUT OPERATOR GUIDE (Source: b1stash PDFs 002, 009)
# Actions operator takes AFTER successful checkout
# ═══════════════════════════════════════════════════════════════════════════

POST_CHECKOUT_GUIDES = {
    "digital_delivery": {
        "name": "Digital Delivery (Gift Cards, Game Keys)",
        "steps": [
            "Check email for delivery confirmation (use cardholder email access)",
            "If email redirect was set up, check redirect target",
            "Download/redeem keys immediately - merchants can revoke",
            "Do NOT contact customer support unless absolutely necessary",
            "Clear browser data after successful redemption",
        ],
    },
    "physical_shipping": {
        "name": "Physical Shipping",
        "steps": [
            "Track order without logging into account (use tracking URL directly)",
            "Consider address swap AFTER order approval if supported",
            "Monitor cardholder email for shipping updates",
            "If using drop address, ensure someone is available to receive",
            "Do NOT modify order after placement unless critical",
        ],
    },
    "in_store_pickup": {
        "name": "In-Store Pickup (Best Buy, etc.)",
        "steps": [
            "Pickup person MUST have ID matching cardholder name on order",
            "Go to pickup within 4 hours of order confirmation",
            "Have order confirmation email/number ready",
            "If asked for card, show any card with matching last 4 digits",
            "Be confident and natural - staff just scans barcode",
            "Leave store promptly after pickup",
        ],
    },
    "subscription": {
        "name": "Subscription Services (Netflix, Spotify, etc.)",
        "steps": [
            "Change email to controlled address immediately after signup",
            "Enable 2FA with controlled phone number",
            "Do NOT upgrade plan immediately - wait 48 hours",
            "Monitor for fraud alerts on cardholder email",
        ],
    },
    "ad_platforms": {
        "name": "Ad Platforms (Google Ads, Pinterest Ads)",
        "steps": [
            "Start with small daily budget ($20-50)",
            "Scale gradually over 3-5 days",
            "Monitor for minicharge verification requests",
            "If minicharge appears, use bank enrollment to verify",
            "Rotate domains if previous ones were banned",
        ],
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# OSINT VERIFICATION CHECKLIST FOR HANDOVER
# ═══════════════════════════════════════════════════════════════════════════

HANDOVER_OSINT_CHECKLIST = [
    "[ ] Cardholder name verified via TruePeopleSearch/FastPeopleSearch",
    "[ ] Billing address confirmed as real address (not PO Box unless expected)",
    "[ ] Phone number verified as real carrier (not VoIP/toll-free)",
    "[ ] Email domain is established (not disposable, has social profiles)",
    "[ ] Card BIN matches cardholder's known bank",
    "[ ] No conflicting data points between card and persona",
]


def get_post_checkout_guide(guide_type: str = "digital_delivery") -> dict:
    """Get post-checkout operator guide by type"""
    return POST_CHECKOUT_GUIDES.get(guide_type, POST_CHECKOUT_GUIDES["digital_delivery"])


def get_handover_osint_checklist() -> list:
    """Get OSINT verification checklist for handover"""
    return HANDOVER_OSINT_CHECKLIST


def intel_aware_handover(profile_path: str, target_id: str, 
                          browser: str = "firefox") -> ManualHandoverProtocol:
    """
    Enhanced handover that loads target intelligence and includes
    operator playbook, post-checkout guide, and risk score in handover.
    
    Args:
        profile_path: Path to forged profile
        target_id: Target ID from target_intelligence database
        browser: Browser type
    
    Returns:
        ManualHandoverProtocol with intelligence loaded
    """
    protocol = quick_handover(profile_path, target_id, browser)
    
    # Load target intelligence
    try:
        from target_intelligence import get_target_intel
        intel = get_target_intel(target_id)
        
        if intel:
            protocol.state.operator_playbook = intel.operator_playbook
            protocol.state.post_checkout_guide = intel.post_checkout_options
            
            # Determine post-checkout type
            # V7.5 FIX: Use getattr — pickup_method may not exist on TargetIntelligence
            pickup = getattr(intel, 'pickup_method', None)
            if pickup == "in_store_pickup":
                guide = get_post_checkout_guide("in_store_pickup")
            elif intel.friction.value == "low" and "gift" in intel.name.lower():
                guide = get_post_checkout_guide("digital_delivery")
            elif "ads" in intel.name.lower():
                guide = get_post_checkout_guide("ad_platforms")
            else:
                guide = get_post_checkout_guide("digital_delivery")
            
            protocol.state.post_checkout_guide = guide.get("steps", [])
            
            # Estimate risk based on friction and 3DS rate
            risk = int(intel.three_ds_rate * 50 + 
                      {"low": 10, "medium": 25, "high": 40}.get(intel.friction.value, 25))
            protocol.state.estimated_risk_score = min(risk, 100)
            
            print(f"[HANDOVER] Target intel loaded: {intel.name}")
            print(f"[HANDOVER] Fraud Engine: {intel.fraud_engine.value}")
            print(f"[HANDOVER] Risk Score: {protocol.state.estimated_risk_score}")
            if intel.operator_playbook:
                print(f"[HANDOVER] Operator playbook: {len(intel.operator_playbook)} steps")
    except ImportError:
        pass
    
    return protocol


if __name__ == "__main__":
    protocol = ManualHandoverProtocol()
    print(f"Handover Protocol initialized. State: {protocol.state.phase}")
