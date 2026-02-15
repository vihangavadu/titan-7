"""
TITAN V7.0 Testing Environment
Virtualized PSP and Detection System Testing Framework

This module provides:
- PSP sandbox emulators (Stripe, Adyen, Braintree, etc.)
- Detection system emulators (fingerprint, behavioral, network)
- Automated test runner with failure analysis
- Comprehensive reporting with root cause analysis
"""

from .psp_sandbox import (
    PSPSandbox,
    StripeSandbox,
    AdyenSandbox,
    BraintreeSandbox,
    PayPalSandbox,
    SquareSandbox,
    PSPResponse,
    DeclineReason,
)

from .detection_emulator import (
    DetectionEmulator,
    FingerprintDetector,
    BehavioralDetector,
    NetworkDetector,
    DeviceDetector,
    VelocityDetector,
    DetectionResult,
    RiskSignal,
)

from .test_runner import (
    TestRunner,
    TestCase,
    TestResult,
    TestSuite,
    run_full_test,
)

from .report_generator import (
    ReportGenerator,
    FailureAnalysis,
    TestReport,
    generate_report,
)

from .environment import (
    TestEnvironment,
    create_test_environment,
    EnvironmentConfig,
)

__all__ = [
    # PSP Sandbox
    'PSPSandbox',
    'StripeSandbox',
    'AdyenSandbox',
    'BraintreeSandbox',
    'PayPalSandbox',
    'SquareSandbox',
    'PSPResponse',
    'DeclineReason',
    
    # Detection Emulator
    'DetectionEmulator',
    'FingerprintDetector',
    'BehavioralDetector',
    'NetworkDetector',
    'DeviceDetector',
    'VelocityDetector',
    'DetectionResult',
    'RiskSignal',
    
    # Test Runner
    'TestRunner',
    'TestCase',
    'TestResult',
    'TestSuite',
    'run_full_test',
    
    # Report Generator
    'ReportGenerator',
    'FailureAnalysis',
    'TestReport',
    'generate_report',
    
    # Environment
    'TestEnvironment',
    'create_test_environment',
    'EnvironmentConfig',
]
