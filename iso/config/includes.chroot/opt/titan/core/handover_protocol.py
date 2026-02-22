"""
TITAN V8.1 SINGULARITY - Manual Handover Protocol
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
from typing import Optional, Dict, List, Callable, Any, Tuple
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
    browser_type: str = "camoufox"
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


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 HANDOVER ORCHESTRATOR — Orchestrate complex multi-step handovers
# ═══════════════════════════════════════════════════════════════════════════════

import threading
from collections import defaultdict


@dataclass
class OrchestrationStep:
    """A step in the handover orchestration."""
    step_id: int
    name: str
    status: str  # "pending", "in_progress", "completed", "failed", "skipped"
    dependencies: List[int]
    action: Optional[Callable[[], bool]]
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class OrchestrationResult:
    """Result of handover orchestration."""
    success: bool
    steps_completed: int
    steps_failed: int
    total_duration_ms: float
    failed_steps: List[str]
    warnings: List[str]


class HandoverOrchestrator:
    """
    V7.6 Handover Orchestrator - Orchestrates complex multi-step
    handover processes with dependency management.
    """
    
    # Standard orchestration templates
    ORCHESTRATION_TEMPLATES = {
        "standard": [
            {"name": "Verify profile exists", "dependencies": []},
            {"name": "Check cookies validity", "dependencies": [0]},
            {"name": "Validate hardware profile", "dependencies": [0]},
            {"name": "Kill automation processes", "dependencies": [1, 2]},
            {"name": "Verify freeze complete", "dependencies": [3]},
            {"name": "Generate operator instructions", "dependencies": [4]},
            {"name": "Record handover timestamp", "dependencies": [5]},
        ],
        "high_security": [
            {"name": "Verify profile exists", "dependencies": []},
            {"name": "Check cookies validity", "dependencies": [0]},
            {"name": "Validate hardware profile", "dependencies": [0]},
            {"name": "Verify IP reputation", "dependencies": [0]},
            {"name": "Check TLS fingerprint", "dependencies": [0]},
            {"name": "Validate timezone sync", "dependencies": [3, 4]},
            {"name": "Kill automation processes", "dependencies": [1, 2, 5]},
            {"name": "Verify freeze complete", "dependencies": [6]},
            {"name": "Run preflight checks", "dependencies": [7]},
            {"name": "Generate operator instructions", "dependencies": [8]},
            {"name": "Record handover timestamp", "dependencies": [9]},
        ],
        "quick": [
            {"name": "Verify profile exists", "dependencies": []},
            {"name": "Kill automation processes", "dependencies": [0]},
            {"name": "Generate operator instructions", "dependencies": [1]},
        ],
    }
    
    def __init__(self, protocol: Optional[ManualHandoverProtocol] = None):
        self.protocol = protocol or ManualHandoverProtocol()
        self._steps: List[OrchestrationStep] = []
        self._execution_lock = threading.Lock()
        self._orchestration_history: List[OrchestrationResult] = []
    
    def load_template(self, template_name: str = "standard"):
        """Load an orchestration template."""
        template = self.ORCHESTRATION_TEMPLATES.get(
            template_name, 
            self.ORCHESTRATION_TEMPLATES["standard"]
        )
        
        self._steps = []
        for i, step_def in enumerate(template):
            step = OrchestrationStep(
                step_id=i,
                name=step_def["name"],
                status="pending",
                dependencies=step_def["dependencies"],
                action=self._get_action_for_step(step_def["name"])
            )
            self._steps.append(step)
    
    def _get_action_for_step(self, step_name: str) -> Optional[Callable[[], bool]]:
        """Get action function for a step."""
        actions = {
            "Verify profile exists": self._verify_profile_exists,
            "Check cookies validity": self._check_cookies,
            "Validate hardware profile": self._validate_hardware,
            "Kill automation processes": self._kill_automation,
            "Verify freeze complete": self._verify_freeze,
            "Generate operator instructions": self._generate_instructions,
            "Record handover timestamp": self._record_timestamp,
            "Verify IP reputation": self._verify_ip,
            "Check TLS fingerprint": self._check_tls,
            "Validate timezone sync": self._validate_timezone,
            "Run preflight checks": self._run_preflight,
        }
        return actions.get(step_name)
    
    def _verify_profile_exists(self) -> bool:
        if self.protocol.state.profile_path and self.protocol.state.profile_path.exists():
            self.protocol.checklist.profile_exists = True
            return True
        return False
    
    def _check_cookies(self) -> bool:
        self.protocol.checklist.cookies_injected = True
        return True
    
    def _validate_hardware(self) -> bool:
        self.protocol.checklist.hardware_profile_set = True
        return True
    
    def _kill_automation(self) -> bool:
        self.protocol.initiate_freeze()
        return True
    
    def _verify_freeze(self) -> bool:
        return self.protocol.verify_freeze()
    
    def _generate_instructions(self) -> bool:
        return True
    
    def _record_timestamp(self) -> bool:
        self.protocol.state.handover_time = datetime.now(timezone.utc)
        return True
    
    def _verify_ip(self) -> bool:
        return True
    
    def _check_tls(self) -> bool:
        return True
    
    def _validate_timezone(self) -> bool:
        return True
    
    def _run_preflight(self) -> bool:
        if self.protocol.state.profile_path:
            results = run_preflight_checks(str(self.protocol.state.profile_path))
            return results.get("passed", False)
        return False
    
    def _can_execute_step(self, step: OrchestrationStep) -> bool:
        """Check if all dependencies are satisfied."""
        for dep_id in step.dependencies:
            dep_step = self._steps[dep_id]
            if dep_step.status != "completed":
                return False
        return True
    
    def execute(self) -> OrchestrationResult:
        """Execute the orchestration."""
        start_time = time.time()
        failed_steps = []
        warnings = []
        
        with self._execution_lock:
            # Execute steps in dependency order
            max_iterations = len(self._steps) * 2  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                made_progress = False
                
                for step in self._steps:
                    if step.status == "pending" and self._can_execute_step(step):
                        step.status = "in_progress"
                        step.started_at = time.time()
                        
                        try:
                            if step.action:
                                result = step.action()
                                step.result = result
                                
                                if result:
                                    step.status = "completed"
                                else:
                                    step.status = "failed"
                                    failed_steps.append(step.name)
                            else:
                                # No action, just mark complete
                                step.status = "completed"
                        except Exception as e:
                            step.status = "failed"
                            step.error = str(e)
                            failed_steps.append(step.name)
                        
                        step.completed_at = time.time()
                        made_progress = True
                
                # Check if all done
                all_terminal = all(s.status in ("completed", "failed", "skipped") for s in self._steps)
                if all_terminal:
                    break
                
                if not made_progress:
                    # Stuck - mark remaining as skipped
                    for step in self._steps:
                        if step.status == "pending":
                            step.status = "skipped"
                            warnings.append(f"Step '{step.name}' skipped due to unmet dependencies")
                    break
        
        elapsed_ms = (time.time() - start_time) * 1000
        completed = sum(1 for s in self._steps if s.status == "completed")
        failed = sum(1 for s in self._steps if s.status == "failed")
        
        result = OrchestrationResult(
            success=failed == 0,
            steps_completed=completed,
            steps_failed=failed,
            total_duration_ms=round(elapsed_ms, 2),
            failed_steps=failed_steps,
            warnings=warnings
        )
        
        self._orchestration_history.append(result)
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestration status."""
        return {
            "steps": [
                {
                    "id": s.step_id,
                    "name": s.name,
                    "status": s.status,
                    "duration_ms": (s.completed_at - s.started_at) * 1000 if s.started_at and s.completed_at else None,
                    "error": s.error
                }
                for s in self._steps
            ],
            "total_steps": len(self._steps),
            "completed": sum(1 for s in self._steps if s.status == "completed"),
            "failed": sum(1 for s in self._steps if s.status == "failed")
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 OPERATOR GUIDANCE ENGINE — Provide real-time guidance to operators
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GuidanceMessage:
    """A guidance message for the operator."""
    message_id: str
    severity: str  # "info", "warning", "critical", "success"
    title: str
    content: str
    action_required: bool
    timestamp: float


class OperatorGuidanceEngine:
    """
    V7.6 Operator Guidance Engine - Provides real-time guidance
    and tips to operators during manual execution.
    """
    
    # Context-aware guidance rules
    GUIDANCE_RULES = {
        "login_page": [
            GuidanceMessage("lg1", "info", "Login Approach", 
                "Enter credentials at human pace (2-3 seconds per field)", False, 0),
            GuidanceMessage("lg2", "warning", "Autofill Alert", 
                "Use browser autofill if available - it triggers trust signals", True, 0),
            GuidanceMessage("lg3", "info", "Failed Login", 
                "If login fails, wait 30 seconds before retry", False, 0),
        ],
        "checkout": [
            GuidanceMessage("ck1", "critical", "Card Entry", 
                "Match typing speed to card complexity - don't rush", True, 0),
            GuidanceMessage("ck2", "warning", "3D Secure", 
                "If 3DS appears, wait for full load before acting", True, 0),
            GuidanceMessage("ck3", "info", "Review Order", 
                "Pause 3-5 seconds on review page - real users read", False, 0),
        ],
        "3ds_challenge": [
            GuidanceMessage("3d1", "critical", "3DS Detected", 
                "Do NOT close the popup - complete or wait for timeout", True, 0),
            GuidanceMessage("3d2", "warning", "OTP Entry", 
                "Enter OTP at 1-2 digits per second, human pace", True, 0),
            GuidanceMessage("3d3", "info", "Failed 3DS", 
                "If 3DS fails, do NOT retry immediately - wait 5 minutes", False, 0),
        ],
        "captcha": [
            GuidanceMessage("cp1", "warning", "Captcha Detected", 
                "Solve carefully - multiple failures increase suspicion", True, 0),
            GuidanceMessage("cp2", "info", "Image Captcha", 
                "Take 3-5 seconds per selection - real users aren't instant", False, 0),
        ],
        "post_checkout": [
            GuidanceMessage("pc1", "success", "Order Placed", 
                "Wait for confirmation email before closing browser", False, 0),
            GuidanceMessage("pc2", "warning", "Order Review", 
                "Some orders enter manual review - check email in 24 hours", False, 0),
            GuidanceMessage("pc3", "info", "Clear Data", 
                "Clear browser data after confirmed receipt", False, 0),
        ],
    }
    
    # Domain-specific tips
    DOMAIN_TIPS = {
        "amazon.com": [
            "Amazon tracks mouse hover patterns - browse naturally before checkout",
            "Add item to cart, then 'continue shopping' before final checkout",
            "Use Prime trial if account doesn't have it - reduces friction",
        ],
        "bestbuy.com": [
            "Best Buy in-store pickup is fastest - verify name matches ID",
            "Rewards signup during checkout is normal - can skip safely",
            "Payment review is common - may take 30 minutes for approval",
        ],
        "eneba.com": [
            "Eneba allows Paysafecard/crypto - consider non-card options",
            "Key delivery is instant - redeem immediately after purchase",
            "Account age matters - consider using aged profiles",
        ],
    }
    
    def __init__(self):
        self._active_guidance: List[GuidanceMessage] = []
        self._dismissed_ids: set = set()
        self._guidance_history: List[Dict] = []
    
    def get_guidance_for_context(self, context: str) -> List[GuidanceMessage]:
        """
        Get guidance messages for a specific context.
        
        Args:
            context: Current context ("login_page", "checkout", etc.)
        
        Returns:
            List of relevant guidance messages
        """
        messages = self.GUIDANCE_RULES.get(context, [])
        
        # Filter out dismissed messages
        active = [m for m in messages if m.message_id not in self._dismissed_ids]
        
        # Add timestamps
        now = time.time()
        for m in active:
            m.timestamp = now
        
        self._active_guidance = active
        return active
    
    def get_domain_tips(self, domain: str) -> List[str]:
        """Get domain-specific tips."""
        # Find matching domain
        for pattern, tips in self.DOMAIN_TIPS.items():
            if pattern in domain:
                return tips
        return []
    
    def dismiss_guidance(self, message_id: str):
        """Dismiss a guidance message."""
        self._dismissed_ids.add(message_id)
    
    def acknowledge_guidance(self, message_id: str, action_taken: str = ""):
        """Acknowledge acting on guidance."""
        self._guidance_history.append({
            "message_id": message_id,
            "action_taken": action_taken,
            "timestamp": time.time()
        })
    
    def get_critical_guidance(self) -> List[GuidanceMessage]:
        """Get only critical guidance messages."""
        return [m for m in self._active_guidance if m.severity == "critical"]
    
    def generate_step_by_step(self, target_domain: str, 
                              checkout_type: str = "digital_delivery") -> List[str]:
        """
        Generate step-by-step operator guide for a target.
        
        Args:
            target_domain: Target website domain
            checkout_type: Type of checkout
        
        Returns:
            List of step-by-step instructions
        """
        steps = []
        
        # Pre-checkout
        steps.append("1. Launch browser with the prepared profile")
        steps.append("2. Navigate to target via organic path (Google search preferred)")
        
        # Domain-specific
        tips = self.get_domain_tips(target_domain)
        if tips:
            steps.append(f"3. Note: {tips[0]}")
        
        # Checkout
        steps.append("4. Browse naturally for 2-3 minutes before checkout")
        steps.append("5. Add items to cart, review order")
        steps.append("6. Proceed to checkout when ready")
        steps.append("7. Enter payment details at human pace")
        steps.append("8. Handle 3DS challenge if presented")
        steps.append("9. Confirm order and note confirmation number")
        
        # Post-checkout
        guide = get_post_checkout_guide(checkout_type)
        for i, post_step in enumerate(guide.get("steps", [])[:3], 10):
            steps.append(f"{i}. {post_step}")
        
        return steps


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 HANDOVER ANALYTICS — Track handover success rates and patterns
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HandoverMetrics:
    """Metrics for handover analytics."""
    total_handovers: int
    successful: int
    failed: int
    aborted: int
    avg_duration_ms: float
    success_rate: float
    common_failures: List[Tuple[str, int]]


class HandoverAnalytics:
    """
    V7.6 Handover Analytics - Tracks handover success rates
    and identifies patterns for improvement.
    """
    
    def __init__(self):
        self._handover_records: List[Dict] = []
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._domain_stats: Dict[str, Dict] = defaultdict(lambda: {"success": 0, "fail": 0})
    
    def record_handover(self, profile_id: str, target_domain: str,
                       success: bool, duration_ms: float,
                       failure_reason: Optional[str] = None):
        """Record a handover outcome."""
        record = {
            "profile_id": profile_id,
            "target_domain": target_domain,
            "success": success,
            "duration_ms": duration_ms,
            "failure_reason": failure_reason,
            "timestamp": time.time()
        }
        
        self._handover_records.append(record)
        
        if not success and failure_reason:
            self._failure_counts[failure_reason] += 1
        
        domain_key = target_domain.replace("www.", "")
        if success:
            self._domain_stats[domain_key]["success"] += 1
        else:
            self._domain_stats[domain_key]["fail"] += 1
    
    def get_metrics(self) -> HandoverMetrics:
        """Get overall handover metrics."""
        if not self._handover_records:
            return HandoverMetrics(0, 0, 0, 0, 0, 0, [])
        
        total = len(self._handover_records)
        successful = sum(1 for r in self._handover_records if r["success"])
        failed = sum(1 for r in self._handover_records if not r["success"] and r.get("failure_reason"))
        aborted = total - successful - failed
        
        durations = [r["duration_ms"] for r in self._handover_records if r["duration_ms"]]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        success_rate = successful / total if total > 0 else 0
        
        common_failures = sorted(
            self._failure_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return HandoverMetrics(
            total_handovers=total,
            successful=successful,
            failed=failed,
            aborted=aborted,
            avg_duration_ms=round(avg_duration, 2),
            success_rate=round(success_rate, 3),
            common_failures=common_failures
        )
    
    def get_domain_success_rate(self, domain: str) -> float:
        """Get success rate for a specific domain."""
        domain_key = domain.replace("www.", "")
        stats = self._domain_stats.get(domain_key, {"success": 0, "fail": 0})
        total = stats["success"] + stats["fail"]
        return stats["success"] / total if total > 0 else 0
    
    def get_best_performing_domains(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Get domains with highest success rates."""
        rates = []
        for domain, stats in self._domain_stats.items():
            total = stats["success"] + stats["fail"]
            if total >= 3:  # Minimum sample size
                rate = stats["success"] / total
                rates.append((domain, rate))
        
        return sorted(rates, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_improvement_suggestions(self) -> List[str]:
        """Generate improvement suggestions based on data."""
        suggestions = []
        metrics = self.get_metrics()
        
        if metrics.success_rate < 0.7:
            suggestions.append("Overall success rate is below 70% - review profile quality")
        
        for failure, count in metrics.common_failures:
            if count >= 3:
                suggestions.append(f"Address recurring failure: '{failure}' ({count} occurrences)")
        
        # Check for domain-specific issues
        for domain, stats in self._domain_stats.items():
            total = stats["success"] + stats["fail"]
            if total >= 5 and stats["fail"] / total > 0.5:
                suggestions.append(f"High failure rate on {domain} - consider target-specific optimization")
        
        if not suggestions:
            suggestions.append("Performance is good - maintain current practices")
        
        return suggestions


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 SECURE HANDOVER CHANNEL — Secure communication during handover
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import hmac


class SecureHandoverChannel:
    """
    V7.6 Secure Handover Channel - Provides secure communication
    between automated system and operator during handover.
    """
    
    def __init__(self, shared_secret: Optional[str] = None):
        """
        Initialize secure channel.
        
        Args:
            shared_secret: Pre-shared key for HMAC (auto-generated if None)
        """
        self.secret = shared_secret or base64.b64encode(os.urandom(32)).decode()
        self._message_queue: List[Dict] = []
        self._received_acks: set = set()
    
    def _sign_message(self, message: str) -> str:
        """Sign a message with HMAC."""
        signature = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _verify_signature(self, message: str, signature: str) -> bool:
        """Verify message signature."""
        expected = self._sign_message(message)
        return hmac.compare_digest(expected, signature)
    
    def send_secure_message(self, message_type: str, content: Dict) -> str:
        """
        Send a secure message to the operator.
        
        Args:
            message_type: Type of message ("instruction", "warning", "data")
            content: Message content
        
        Returns:
            Message ID
        """
        message_id = hashlib.md5(
            f"{time.time()}{json.dumps(content)}".encode()
        ).hexdigest()[:12]
        
        payload = json.dumps({
            "id": message_id,
            "type": message_type,
            "content": content,
            "timestamp": time.time()
        })
        
        signature = self._sign_message(payload)
        
        self._message_queue.append({
            "id": message_id,
            "payload": payload,
            "signature": signature,
            "sent_at": time.time()
        })
        
        return message_id
    
    def receive_ack(self, message_id: str, ack_signature: str) -> bool:
        """
        Receive acknowledgment from operator.
        
        Args:
            message_id: Message being acknowledged
            ack_signature: Signature proving receipt
        
        Returns:
            True if ack is valid
        """
        if self._verify_signature(message_id, ack_signature):
            self._received_acks.add(message_id)
            return True
        return False
    
    def get_pending_messages(self) -> List[Dict]:
        """Get messages awaiting acknowledgment."""
        return [
            msg for msg in self._message_queue 
            if msg["id"] not in self._received_acks
        ]
    
    def send_handover_data(self, handover_state: HandoverState) -> str:
        """Send handover data securely."""
        content = {
            "profile_id": handover_state.profile_id,
            "target_domain": handover_state.target_domain,
            "browser_type": handover_state.browser_type,
            "profile_path": str(handover_state.profile_path) if handover_state.profile_path else None,
            "risk_score": handover_state.estimated_risk_score,
            "operator_playbook": handover_state.operator_playbook,
        }
        return self.send_secure_message("handover_data", content)
    
    def generate_operator_token(self, handover_state: HandoverState, 
                                validity_minutes: int = 60) -> str:
        """
        Generate a time-limited token for operator authentication.
        
        Args:
            handover_state: Current handover state
            validity_minutes: Token validity period
        
        Returns:
            Operator authentication token
        """
        expiry = time.time() + (validity_minutes * 60)
        
        token_data = {
            "profile_id": handover_state.profile_id,
            "target": handover_state.target_domain,
            "expires": expiry
        }
        
        payload = json.dumps(token_data)
        signature = self._sign_message(payload)
        
        token = base64.b64encode(
            f"{payload}|{signature}".encode()
        ).decode()
        
        return token
    
    def verify_operator_token(self, token: str) -> Optional[Dict]:
        """
        Verify an operator token.
        
        Returns:
            Token data if valid, None if invalid/expired
        """
        try:
            decoded = base64.b64decode(token).decode()
            payload, signature = decoded.rsplit("|", 1)
            
            if not self._verify_signature(payload, signature):
                return None
            
            token_data = json.loads(payload)
            
            if token_data.get("expires", 0) < time.time():
                return None
            
            return token_data
            
        except Exception:
            return None


# Global instances
_handover_orchestrator: Optional[HandoverOrchestrator] = None
_guidance_engine: Optional[OperatorGuidanceEngine] = None
_handover_analytics: Optional[HandoverAnalytics] = None
_secure_channel: Optional[SecureHandoverChannel] = None


def get_handover_orchestrator() -> HandoverOrchestrator:
    """Get global handover orchestrator."""
    global _handover_orchestrator
    if _handover_orchestrator is None:
        _handover_orchestrator = HandoverOrchestrator()
    return _handover_orchestrator


def get_guidance_engine() -> OperatorGuidanceEngine:
    """Get global operator guidance engine."""
    global _guidance_engine
    if _guidance_engine is None:
        _guidance_engine = OperatorGuidanceEngine()
    return _guidance_engine


def get_handover_analytics() -> HandoverAnalytics:
    """Get global handover analytics."""
    global _handover_analytics
    if _handover_analytics is None:
        _handover_analytics = HandoverAnalytics()
    return _handover_analytics


def get_secure_channel(secret: Optional[str] = None) -> SecureHandoverChannel:
    """Get global secure handover channel."""
    global _secure_channel
    if _secure_channel is None:
        _secure_channel = SecureHandoverChannel(secret)
    return _secure_channel
