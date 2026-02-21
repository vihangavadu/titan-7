#!/usr/bin/env python3
"""
TITAN V7.6 SINGULARITY — Complete Codebase Verification Script
═══════════════════════════════════════════════════════════════════════════════

This script provides comprehensive analysis of the TITAN codebase including:
- Module discovery and dependency mapping
- Import chain analysis
- Orphan module detection
- Integration coverage metrics (GUI/Backend/API)
- Module health checks
- Connection visualization

Usage:
    python titan_codebase_verify.py              # Full analysis
    python titan_codebase_verify.py --quick      # Quick scan only
    python titan_codebase_verify.py --json       # Output as JSON
    python titan_codebase_verify.py --fix        # Attempt to fix orphans
    python titan_codebase_verify.py --export     # Export report to file

Author: TITAN OS Team
Version: 7.6.0
"""

import os
import sys
import ast
import json
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict
import re

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TITAN_ROOT = Path(__file__).parent
CORE_DIR = TITAN_ROOT / "core"
APPS_DIR = TITAN_ROOT / "apps"
PROFGEN_DIR = TITAN_ROOT / "profgen"

# Key integration files
GUI_FILE = APPS_DIR / "app_unified.py"
BACKEND_FILE = CORE_DIR / "integration_bridge.py"
API_FILE = CORE_DIR / "titan_api.py"

# Files to exclude from orphan analysis (entry points, utilities, tests, self)
EXCLUDE_FROM_ORPHAN = {
    # Package init
    "__init__.py",
    # API & entry points
    "titan_api.py",
    "titan_codebase_verify.py",
    "module_connectivity_map.py",
    # Standalone GUI apps (launched directly, not imported)
    "app_unified.py",
    "app_cerberus.py",
    "app_genesis.py",
    "app_kyc.py",
    "app_bug_reporter.py",
    "titan_mission_control.py",
    "titan_dev_hub.py",
    # App utilities (used by apps at runtime, not cross-imported)
    "titan_icon.py",
    "titan_splash.py",
    "titan_enterprise_theme.py",
    "forensic_widget.py",
    "launch_forensic_monitor.py",
    # Test scripts
    "test_llm_bridge.py",
    "test_installation.py",
    "test_system_editor.py",
    "test_fingerprint_injector.py",
    "deep_verify.py",
    "real_e2e_test.py",
    # Profgen sub-modules (internal pipeline, imported by config.py)
    "gen_cookies.py",
    "gen_places.py",
    "gen_firefox_files.py",
    "gen_storage.py",
    "gen_formhistory.py",
    "config.py",
    # Legacy/symlink files on VPS (superseded by newer modules)
    "profile_realism_engine.py",  # Superseded by advanced_profile_generator
    "network_shield.py",          # Symlink to network_shield_loader.py
    "canvas_noise.py",            # Superseded by canvas_subpixel_shim
    "forensic_cleaner.py",        # Superseded by forensic_monitor
    "forensic_synthesis_engine.py",  # Superseded by advanced_profile_generator
    "location_spoofer.py",        # Superseded by location_spoofer_linux
}

# Non-Python files to track
NON_PYTHON_FILES = {".c", ".sh", ".bat"}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModuleInfo:
    """Information about a module"""
    name: str
    path: Path
    size_bytes: int = 0
    line_count: int = 0
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    is_loadable: bool = False
    load_error: Optional[str] = None
    docstring: Optional[str] = None
    
    # Integration status
    in_gui: bool = False
    in_backend: bool = False
    in_api: bool = False
    
    @property
    def is_orphan(self) -> bool:
        """Check if module is orphan (not imported anywhere)"""
        return len(self.imported_by) == 0 and self.name not in EXCLUDE_FROM_ORPHAN
    
    @property
    def integration_score(self) -> int:
        """Score 0-3 based on integration points"""
        return sum([self.in_gui, self.in_backend, self.in_api])
    
    @property
    def integration_status(self) -> str:
        """Human-readable integration status"""
        if self.integration_score == 3:
            return "FULL"
        elif self.integration_score == 2:
            return "PARTIAL"
        elif self.integration_score == 1:
            return "MINIMAL"
        else:
            return "NONE"


@dataclass
class VerificationReport:
    """Complete verification report"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    titan_version: str = "7.6.0"
    
    # Module counts
    total_modules: int = 0
    core_modules: int = 0
    app_modules: int = 0
    other_modules: int = 0
    
    # Health metrics
    loadable_modules: int = 0
    failed_modules: int = 0
    orphan_modules: int = 0
    
    # Integration coverage
    gui_coverage: int = 0
    backend_coverage: int = 0
    api_coverage: int = 0
    full_integration: int = 0
    
    # Total lines of code
    total_lines: int = 0
    total_size_kb: float = 0
    
    # Detailed data
    modules: Dict[str, ModuleInfo] = field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    orphans: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# AST ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

class ModuleAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze Python modules"""
    
    def __init__(self):
        self.imports: List[str] = []
        self.from_imports: Dict[str, List[str]] = defaultdict(list)
        self.classes: List[str] = []
        self.functions: List[str] = []
        self.docstring: Optional[str] = None
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.from_imports[node.module].extend(
                alias.name for alias in node.names
            )
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Only top-level functions
        self.functions.append(node.name)
        # Don't visit children to avoid nested functions
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.functions.append(node.name)
    
    def visit_Module(self, node: ast.Module):
        # Get module docstring
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant):
                self.docstring = node.body[0].value.value
        self.generic_visit(node)
    
    def get_all_imports(self) -> List[str]:
        """Get all imported module names"""
        imports = set(self.imports)
        imports.update(self.from_imports.keys())
        return list(imports)


def analyze_file(file_path: Path) -> Tuple[ModuleAnalyzer, Optional[str]]:
    """Analyze a Python file and return AST info"""
    try:
        source = file_path.read_text(encoding='utf-8', errors='replace')
        tree = ast.parse(source)
        analyzer = ModuleAnalyzer()
        analyzer.visit(tree)
        return analyzer, None
    except SyntaxError as e:
        return ModuleAnalyzer(), f"Syntax error: {e}"
    except Exception as e:
        return ModuleAnalyzer(), f"Parse error: {e}"


def check_import_in_file(file_path: Path, module_name: str) -> bool:
    """Check if a module is imported in a file"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
        # Check various import patterns
        patterns = [
            rf'^\s*import\s+{module_name}\b',
            rf'^\s*from\s+{module_name}\s+import',
            rf'^\s*from\s+{module_name.replace(".py", "")}\s+import',
        ]
        module_base = module_name.replace('.py', '')
        patterns.extend([
            rf'^\s*import\s+{module_base}\b',
            rf'^\s*from\s+{module_base}\s+import',
        ])
        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════

def discover_modules(directory: Path, prefix: str = "") -> List[Path]:
    """Discover all Python modules in a directory"""
    modules = []
    if not directory.exists():
        return modules
    
    for item in directory.iterdir():
        if item.is_file() and item.suffix == '.py':
            if not item.name.startswith('__pycache__'):
                modules.append(item)
        elif item.is_dir() and not item.name.startswith(('__pycache__', '.', 'test')):
            modules.extend(discover_modules(item, f"{prefix}{item.name}."))
    
    return modules


def get_module_info(file_path: Path) -> ModuleInfo:
    """Get detailed information about a module"""
    info = ModuleInfo(
        name=file_path.name,
        path=file_path,
    )
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
        info.size_bytes = len(content.encode('utf-8'))
        info.line_count = len(content.splitlines())
        
        # AST analysis
        analyzer, error = analyze_file(file_path)
        if error:
            info.load_error = error
        else:
            info.imports = analyzer.get_all_imports()
            info.classes = analyzer.classes
            info.functions = analyzer.functions
            info.docstring = analyzer.docstring
            info.is_loadable = True
            
    except Exception as e:
        info.load_error = str(e)
    
    return info


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_integration(modules: Dict[str, ModuleInfo]) -> None:
    """Analyze integration status for all modules"""
    
    # Check GUI integration
    if GUI_FILE.exists():
        for name, info in modules.items():
            module_base = name.replace('.py', '')
            info.in_gui = check_import_in_file(GUI_FILE, module_base)
    
    # Check Backend integration
    if BACKEND_FILE.exists():
        for name, info in modules.items():
            module_base = name.replace('.py', '')
            info.in_backend = check_import_in_file(BACKEND_FILE, module_base)
    
    # Check API integration
    if API_FILE.exists():
        for name, info in modules.items():
            module_base = name.replace('.py', '')
            info.in_api = check_import_in_file(API_FILE, module_base)


def build_dependency_graph(modules: Dict[str, ModuleInfo]) -> Dict[str, List[str]]:
    """Build reverse dependency graph (who imports whom)"""
    graph = defaultdict(list)
    module_names = {m.replace('.py', '') for m in modules.keys()}
    
    for name, info in modules.items():
        for imp in info.imports:
            # Check if this import is one of our modules
            imp_base = imp.split('.')[0]
            if imp_base in module_names:
                graph[f"{imp_base}.py"].append(name)
    
    # Update imported_by in module info
    for imported, importers in graph.items():
        if imported in modules:
            modules[imported].imported_by = importers
    
    return dict(graph)


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TitanCodebaseVerifier:
    """Main verification engine"""
    
    def __init__(self, root_path: Path = TITAN_ROOT):
        self.root = root_path
        self.report = VerificationReport()
        self.modules: Dict[str, ModuleInfo] = {}
    
    def run(self, quick: bool = False) -> VerificationReport:
        """Run full verification"""
        print("=" * 70)
        print("  TITAN V7.6 SINGULARITY — Codebase Verification")
        print("=" * 70)
        print()
        
        # Phase 1: Discover modules
        print("[1/5] Discovering modules...")
        self._discover_all_modules()
        
        # Phase 2: Analyze each module
        print("[2/5] Analyzing module contents...")
        self._analyze_modules()
        
        # Phase 3: Build dependency graph
        print("[3/5] Building dependency graph...")
        self.report.dependency_graph = build_dependency_graph(self.modules)
        
        # Phase 4: Check integration
        print("[4/5] Checking integration status...")
        analyze_integration(self.modules)
        
        # Phase 5: Generate report
        print("[5/5] Generating report...")
        self._generate_report()
        
        return self.report
    
    def _discover_all_modules(self):
        """Discover all Python modules"""
        # Core modules
        core_modules = discover_modules(CORE_DIR)
        for m in core_modules:
            info = get_module_info(m)
            self.modules[m.name] = info
        self.report.core_modules = len(core_modules)
        
        # App modules
        app_modules = discover_modules(APPS_DIR)
        for m in app_modules:
            info = get_module_info(m)
            self.modules[m.name] = info
        self.report.app_modules = len(app_modules)
        
        # Profgen modules
        profgen_modules = discover_modules(PROFGEN_DIR)
        for m in profgen_modules:
            info = get_module_info(m)
            self.modules[m.name] = info
        
        # Root level Python files
        for f in self.root.glob("*.py"):
            if f.name not in self.modules:
                info = get_module_info(f)
                self.modules[f.name] = info
        
        self.report.total_modules = len(self.modules)
        self.report.other_modules = len(self.modules) - self.report.core_modules - self.report.app_modules
        
        print(f"    Found {len(self.modules)} Python modules")
        print(f"    - Core: {self.report.core_modules}")
        print(f"    - Apps: {self.report.app_modules}")
        print(f"    - Other: {self.report.other_modules}")
    
    def _analyze_modules(self):
        """Analyze all discovered modules"""
        loadable = 0
        failed = 0
        total_lines = 0
        total_size = 0
        
        for name, info in self.modules.items():
            if info.is_loadable:
                loadable += 1
            else:
                failed += 1
                self.report.errors.append(f"{name}: {info.load_error}")
            
            total_lines += info.line_count
            total_size += info.size_bytes
        
        self.report.loadable_modules = loadable
        self.report.failed_modules = failed
        self.report.total_lines = total_lines
        self.report.total_size_kb = round(total_size / 1024, 2)
        
        print(f"    Loadable: {loadable}/{len(self.modules)}")
        print(f"    Total lines: {total_lines:,}")
        print(f"    Total size: {self.report.total_size_kb:,.1f} KB")
    
    def _generate_report(self):
        """Generate final report"""
        # Count orphans
        orphans = []
        for name, info in self.modules.items():
            if info.is_orphan:
                orphans.append(name)
        self.report.orphans = orphans
        self.report.orphan_modules = len(orphans)
        
        # Count integration coverage
        gui_count = sum(1 for m in self.modules.values() if m.in_gui)
        backend_count = sum(1 for m in self.modules.values() if m.in_backend)
        api_count = sum(1 for m in self.modules.values() if m.in_api)
        full_count = sum(1 for m in self.modules.values() if m.integration_score == 3)
        
        self.report.gui_coverage = gui_count
        self.report.backend_coverage = backend_count
        self.report.api_coverage = api_count
        self.report.full_integration = full_count
        
        # Store modules
        self.report.modules = self.modules
        
        print(f"    Orphan modules: {len(orphans)}")
        print(f"    GUI coverage: {gui_count}/{self.report.core_modules}")
        print(f"    Backend coverage: {backend_count}/{self.report.core_modules}")
        print(f"    API coverage: {api_count}/{self.report.core_modules}")


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT FORMATTERS
# ═══════════════════════════════════════════════════════════════════════════════

def print_module_matrix(report: VerificationReport):
    """Print module connection matrix"""
    print()
    print("=" * 90)
    print("  MODULE CONNECTION MATRIX")
    print("=" * 90)
    print()
    print(f"{'Module':<40} {'GUI':^5} {'Back':^5} {'API':^5} {'Score':^6} {'Status':^10}")
    print("-" * 90)
    
    # Sort by integration score (descending)
    sorted_modules = sorted(
        report.modules.items(),
        key=lambda x: (-x[1].integration_score, x[0])
    )
    
    for name, info in sorted_modules:
        gui = "✅" if info.in_gui else "❌"
        backend = "✅" if info.in_backend else "❌"
        api = "✅" if info.in_api else "❌"
        score = f"{info.integration_score}/3"
        status = info.integration_status
        
        # Color-code status
        if status == "FULL":
            status = f"✅ {status}"
        elif status == "PARTIAL":
            status = f"⚠️ {status}"
        elif status == "MINIMAL":
            status = f"🔸 {status}"
        else:
            status = f"❌ {status}"
        
        print(f"{name:<40} {gui:^5} {backend:^5} {api:^5} {score:^6} {status:^10}")


def print_dependency_graph(report: VerificationReport):
    """Print dependency graph"""
    print()
    print("=" * 70)
    print("  DEPENDENCY GRAPH (Who imports whom)")
    print("=" * 70)
    print()
    
    # Sort by number of importers
    sorted_deps = sorted(
        report.dependency_graph.items(),
        key=lambda x: -len(x[1])
    )[:20]  # Top 20
    
    for module, importers in sorted_deps:
        print(f"📦 {module} (imported by {len(importers)} modules):")
        for imp in importers[:5]:
            print(f"    ← {imp}")
        if len(importers) > 5:
            print(f"    ... and {len(importers) - 5} more")
        print()


def print_orphan_report(report: VerificationReport):
    """Print orphan module report"""
    print()
    print("=" * 70)
    print("  ORPHAN MODULE REPORT")
    print("=" * 70)
    print()
    
    if not report.orphans:
        print("  ✅ No orphan modules detected!")
        print("  All modules are imported somewhere in the codebase.")
    else:
        print(f"  ⚠️ Found {len(report.orphans)} orphan module(s):")
        print()
        for orphan in report.orphans:
            info = report.modules.get(orphan)
            if info:
                print(f"  • {orphan}")
                print(f"    Path: {info.path}")
                print(f"    Lines: {info.line_count}")
                print(f"    Classes: {', '.join(info.classes[:3]) or 'None'}")
                print()


def print_summary(report: VerificationReport):
    """Print verification summary"""
    print()
    print("=" * 70)
    print("  VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    print(f"  TITAN Version: {report.titan_version}")
    print(f"  Timestamp: {report.timestamp}")
    print()
    print("  📊 MODULE STATISTICS:")
    print(f"     Total Modules:      {report.total_modules}")
    print(f"     Core Modules:       {report.core_modules}")
    print(f"     App Modules:        {report.app_modules}")
    print(f"     Other Modules:      {report.other_modules}")
    print()
    print("  🔧 HEALTH STATUS:")
    print(f"     Loadable:           {report.loadable_modules}/{report.total_modules}")
    print(f"     Failed:             {report.failed_modules}")
    print(f"     Orphans:            {report.orphan_modules}")
    print()
    print("  🔗 INTEGRATION COVERAGE:")
    print(f"     GUI (app_unified):      {report.gui_coverage}/{report.core_modules} ({report.gui_coverage*100//max(report.core_modules,1)}%)")
    print(f"     Backend (bridge):       {report.backend_coverage}/{report.core_modules} ({report.backend_coverage*100//max(report.core_modules,1)}%)")
    print(f"     API (titan_api):        {report.api_coverage}/{report.core_modules} ({report.api_coverage*100//max(report.core_modules,1)}%)")
    print(f"     Full Integration:       {report.full_integration} modules")
    print()
    print("  📈 CODEBASE SIZE:")
    print(f"     Total Lines:        {report.total_lines:,}")
    print(f"     Total Size:         {report.total_size_kb:,.1f} KB")
    print()
    
    # Overall status
    if report.orphan_modules == 0 and report.failed_modules == 0:
        print("  ✅ VERIFICATION PASSED — All modules connected and healthy!")
    elif report.orphan_modules > 0:
        print(f"  ⚠️ VERIFICATION WARNING — {report.orphan_modules} orphan module(s) detected")
    if report.failed_modules > 0:
        print(f"  ❌ VERIFICATION FAILED — {report.failed_modules} module(s) have errors")


def export_json(report: VerificationReport, output_path: Path):
    """Export report as JSON"""
    def serialize(obj):
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, ModuleInfo):
            d = asdict(obj)
            d['path'] = str(obj.path)
            return d
        return obj
    
    data = {
        "timestamp": report.timestamp,
        "titan_version": report.titan_version,
        "summary": {
            "total_modules": report.total_modules,
            "core_modules": report.core_modules,
            "app_modules": report.app_modules,
            "loadable": report.loadable_modules,
            "failed": report.failed_modules,
            "orphans": report.orphan_modules,
            "total_lines": report.total_lines,
            "total_size_kb": report.total_size_kb,
        },
        "integration": {
            "gui_coverage": report.gui_coverage,
            "backend_coverage": report.backend_coverage,
            "api_coverage": report.api_coverage,
            "full_integration": report.full_integration,
        },
        "modules": {
            name: serialize(info) for name, info in report.modules.items()
        },
        "dependency_graph": report.dependency_graph,
        "orphans": report.orphans,
        "errors": report.errors,
        "warnings": report.warnings,
    }
    
    output_path.write_text(json.dumps(data, indent=2, default=str))
    print(f"\n  📄 Report exported to: {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="TITAN V7.6 Codebase Verification Script"
    )
    parser.add_argument("--quick", action="store_true", help="Quick scan only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--export", action="store_true", help="Export report to file")
    parser.add_argument("--matrix", action="store_true", help="Show module matrix")
    parser.add_argument("--deps", action="store_true", help="Show dependency graph")
    parser.add_argument("--orphans", action="store_true", help="Show orphan report")
    parser.add_argument("--all", action="store_true", help="Show all reports")
    args = parser.parse_args()
    
    # Run verification
    verifier = TitanCodebaseVerifier()
    report = verifier.run(quick=args.quick)
    
    # Output
    print()
    
    if args.json:
        # JSON output only
        import json
        output = {
            "total_modules": report.total_modules,
            "orphans": report.orphans,
            "integration": {
                "gui": report.gui_coverage,
                "backend": report.backend_coverage,
                "api": report.api_coverage,
            }
        }
        print(json.dumps(output, indent=2))
        return
    
    # Print summary always
    print_summary(report)
    
    # Optional detailed reports
    if args.all or args.matrix:
        print_module_matrix(report)
    
    if args.all or args.deps:
        print_dependency_graph(report)
    
    if args.all or args.orphans:
        print_orphan_report(report)
    
    if args.export:
        export_path = TITAN_ROOT / f"verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_json(report, export_path)
    
    print()
    print("=" * 70)
    print("  Verification complete!")
    print("=" * 70)
    
    # Exit code
    if report.orphan_modules > 0 or report.failed_modules > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
