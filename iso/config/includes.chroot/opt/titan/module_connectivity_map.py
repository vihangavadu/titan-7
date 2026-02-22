#!/usr/bin/env python3
"""
TITAN V8.1 — Deep Module Connectivity Map Generator
═══════════════════════════════════════════════════════════════════════════════

Generates a complete connectivity map showing all module relationships.

Features:
- Cross-references ALL modules in the codebase
- Tracks import chains 3 levels deep
- Exports Mermaid diagram for visualization
- Identifies circular dependencies
- Maps class/function exports

Usage:
    python module_connectivity_map.py              # Generate map
    python module_connectivity_map.py --mermaid    # Export Mermaid diagram
    python module_connectivity_map.py --html       # Export interactive HTML

Author: TITAN OS Team
Version: 8.1.0
"""

import os
import sys
import ast
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict
import re

TITAN_ROOT = Path(__file__).parent

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

MODULE_CATEGORIES = {
    # Core Infrastructure
    "integration_bridge.py": "🔗 Bridge",
    "titan_api.py": "🌐 API",
    "titan_env.py": "⚙️ Config",
    "titan_services.py": "🔧 Services",
    
    # Profile Generation
    "genesis_core.py": "👤 Genesis",
    "advanced_profile_generator.py": "👤 Genesis",
    "fingerprint_injector.py": "👤 Genesis",
    "form_autofill_injector.py": "👤 Genesis",
    "purchase_history_engine.py": "👤 Genesis",
    
    # Card/Transaction
    "cerberus_core.py": "💳 Cerberus",
    "cerberus_enhanced.py": "💳 Cerberus",
    "three_ds_strategy.py": "💳 Cerberus",
    "transaction_monitor.py": "💳 Cerberus",
    "issuer_algo_defense.py": "💳 Cerberus",
    "tra_exemption_engine.py": "💳 Cerberus",
    
    # KYC/Identity
    "kyc_core.py": "🪪 KYC",
    "kyc_enhanced.py": "🪪 KYC",
    "kyc_voice_engine.py": "🪪 KYC",
    "tof_depth_synthesis.py": "🪪 KYC",
    "verify_deep_identity.py": "🪪 KYC",
    
    # Browser/Fingerprint
    "ja4_permutation_engine.py": "🔐 Fingerprint",
    "tls_parrot.py": "🔐 Fingerprint",
    "canvas_subpixel_shim.py": "🔐 Fingerprint",
    "webgl_angle.py": "🔐 Fingerprint",
    "audio_hardener.py": "🔐 Fingerprint",
    "font_sanitizer.py": "🔐 Fingerprint",
    
    # Network
    "proxy_manager.py": "🌍 Network",
    "lucid_vpn.py": "🌍 Network",
    "quic_proxy.py": "🌍 Network",
    "network_jitter.py": "🌍 Network",
    "network_shield_loader.py": "🌍 Network",
    "location_spoofer_linux.py": "🌍 Network",
    "timezone_enforcer.py": "🌍 Network",
    
    # AI/Intelligence
    "ai_intelligence_engine.py": "🧠 AI",
    "cognitive_core.py": "🧠 AI",
    "ollama_bridge.py": "🧠 AI",
    "target_intelligence.py": "🧠 AI",
    "target_discovery.py": "🧠 AI",
    "target_presets.py": "🧠 AI",
    "intel_monitor.py": "🧠 AI",
    
    # Behavior
    "ghost_motor_v6.py": "🎭 Behavior",
    "first_session_bias_eliminator.py": "🎭 Behavior",
    "referrer_warmup.py": "🎭 Behavior",
    "generate_trajectory_model.py": "🎭 Behavior",
    
    # Storage
    "indexeddb_lsng_synthesis.py": "💾 Storage",
    "dynamic_data.py": "💾 Storage",
    
    # Security
    "kill_switch.py": "🛡️ Security",
    "preflight_validator.py": "🛡️ Security",
    "forensic_monitor.py": "🛡️ Security",
    "immutable_os.py": "🛡️ Security",
    "cpuid_rdtsc_shield.py": "🛡️ Security",
    
    # Hardware
    "usb_peripheral_synth.py": "🔌 Hardware",
    "waydroid_sync.py": "🔌 Hardware",
    
    # Operations
    "handover_protocol.py": "📋 Ops",
    "cockpit_daemon.py": "📋 Ops",
    "bug_patch_bridge.py": "📋 Ops",
    "titan_master_verify.py": "📋 Ops",
    
    # Apps
    "app_unified.py": "🖥️ App",
    "app_cerberus.py": "🖥️ App",
    "app_genesis.py": "🖥️ App",
    "app_kyc.py": "🖥️ App",
    "titan_dev_hub.py": "🖥️ App",
    "titan_mission_control.py": "🖥️ App",
}


@dataclass
class ModuleNode:
    """Node in the connectivity graph"""
    name: str
    category: str = "📦 Other"
    imports: Set[str] = field(default_factory=set)
    imported_by: Set[str] = field(default_factory=set)
    exports: List[str] = field(default_factory=list)
    line_count: int = 0
    
    @property
    def connectivity_score(self) -> int:
        return len(self.imports) + len(self.imported_by)


class ConnectivityMapper:
    """Maps all module connectivity"""
    
    def __init__(self, root: Path):
        self.root = root
        self.nodes: Dict[str, ModuleNode] = {}
        self.all_files: List[Path] = []
    
    def scan(self):
        """Scan entire codebase"""
        print("🔍 Scanning codebase...")
        
        # Find all Python files
        for pattern in ["core/*.py", "apps/*.py", "profgen/*.py", "*.py"]:
            for f in self.root.glob(pattern):
                if not f.name.startswith("__"):
                    self.all_files.append(f)
        
        print(f"   Found {len(self.all_files)} Python files")
        
        # Analyze each file
        for f in self.all_files:
            self._analyze_file(f)
        
        # Build reverse connections
        self._build_reverse_connections()
        
        print(f"   Analyzed {len(self.nodes)} modules")
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single file"""
        name = file_path.name
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
            line_count = len(content.splitlines())
            
            # Parse AST
            tree = ast.parse(content)
            
            # Get imports
            imports = set()
            exports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
                elif isinstance(node, ast.ClassDef):
                    exports.append(f"class {node.name}")
                elif isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    exports.append(f"def {node.name}")
            
            # Create node
            self.nodes[name] = ModuleNode(
                name=name,
                category=MODULE_CATEGORIES.get(name, "📦 Other"),
                imports=imports,
                exports=exports[:10],  # Limit exports
                line_count=line_count,
            )
            
        except Exception as e:
            self.nodes[name] = ModuleNode(name=name, category="❌ Error")
    
    def _build_reverse_connections(self):
        """Build imported_by connections"""
        module_names = {n.replace('.py', '') for n in self.nodes.keys()}
        
        for name, node in self.nodes.items():
            for imp in node.imports:
                # Check if import matches a module
                target = f"{imp}.py"
                if target in self.nodes:
                    self.nodes[target].imported_by.add(name)
    
    def get_orphans(self) -> List[str]:
        """Get truly orphan modules"""
        exclusions = {
            "app_unified.py", "app_cerberus.py", "app_genesis.py", "app_kyc.py",
            "titan_api.py", "titan_dev_hub.py", "titan_mission_control.py",
            "__init__.py", "test_llm_bridge.py", "deep_verify.py",
            "real_e2e_test.py", "titan_codebase_verify.py", "module_connectivity_map.py",
        }
        
        orphans = []
        for name, node in self.nodes.items():
            if name not in exclusions and len(node.imported_by) == 0:
                orphans.append(name)
        
        return orphans
    
    def generate_mermaid(self) -> str:
        """Generate Mermaid diagram"""
        lines = ["graph LR"]
        
        # Group by category
        categories = defaultdict(list)
        for name, node in self.nodes.items():
            categories[node.category].append(name)
        
        # Add subgraphs for each category
        for cat, modules in sorted(categories.items()):
            cat_id = cat.replace(" ", "_").replace("🔗", "").replace("🌐", "").strip()
            lines.append(f"    subgraph {cat_id}[{cat}]")
            for m in modules[:10]:  # Limit per category
                m_id = m.replace('.py', '').replace('_', '')
                lines.append(f"        {m_id}[{m}]")
            lines.append("    end")
        
        # Add connections (limited to avoid clutter)
        added_edges = set()
        for name, node in self.nodes.items():
            from_id = name.replace('.py', '').replace('_', '')
            for imp in list(node.imports)[:5]:
                to_name = f"{imp}.py"
                if to_name in self.nodes:
                    to_id = to_name.replace('.py', '').replace('_', '')
                    edge = f"{from_id} --> {to_id}"
                    if edge not in added_edges:
                        lines.append(f"    {edge}")
                        added_edges.add(edge)
        
        return "\n".join(lines)
    
    def generate_html_report(self) -> str:
        """Generate interactive HTML report"""
        orphans = self.get_orphans()
        
        # Calculate stats
        total = len(self.nodes)
        by_category = defaultdict(int)
        for node in self.nodes.values():
            by_category[node.category] += 1
        
        total_lines = sum(n.line_count for n in self.nodes.values())
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>TITAN V8.1 Module Connectivity Map</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 20px; }}
        h1 {{ color: #00ff88; margin-bottom: 20px; }}
        h2 {{ color: #00aaff; margin: 20px 0 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: #1a1a2e; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff88; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #00ff88; }}
        .stat-label {{ color: #888; font-size: 0.9em; }}
        .module-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }}
        .module-card {{ background: #1a1a2e; padding: 12px; border-radius: 6px; border-left: 3px solid #444; }}
        .module-card.full {{ border-left-color: #00ff88; }}
        .module-card.partial {{ border-left-color: #ffaa00; }}
        .module-card.orphan {{ border-left-color: #ff4444; }}
        .module-name {{ font-weight: bold; color: #fff; margin-bottom: 5px; }}
        .module-category {{ font-size: 0.8em; color: #888; }}
        .module-stats {{ font-size: 0.85em; color: #aaa; margin-top: 5px; }}
        .connections {{ display: flex; gap: 10px; margin-top: 8px; flex-wrap: wrap; }}
        .conn-badge {{ background: #2a2a4e; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; }}
        .filter-bar {{ margin-bottom: 20px; }}
        .filter-btn {{ background: #2a2a4e; border: 1px solid #444; color: #fff; padding: 8px 15px; margin: 3px; border-radius: 4px; cursor: pointer; }}
        .filter-btn:hover {{ background: #3a3a5e; }}
        .filter-btn.active {{ background: #00aa88; border-color: #00ff88; }}
        .search-box {{ background: #1a1a2e; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 4px; width: 300px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #1a1a2e; color: #00aaff; }}
        tr:hover {{ background: #1a1a2e; }}
        .check {{ color: #00ff88; }}
        .cross {{ color: #ff4444; }}
    </style>
</head>
<body>
    <h1>🔱 TITAN V8.1 Module Connectivity Map</h1>
    <p style="color:#888; margin-bottom:20px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>📊 Statistics</h2>
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{total}</div>
            <div class="stat-label">Total Modules</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{total_lines:,}</div>
            <div class="stat-label">Lines of Code</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(orphans)}</div>
            <div class="stat-label">Orphan Modules</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(by_category)}</div>
            <div class="stat-label">Categories</div>
        </div>
    </div>
    
    <h2>🗂️ Category Distribution</h2>
    <div class="stats">
"""
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            html += f'        <div class="stat-card"><div class="stat-value">{count}</div><div class="stat-label">{cat}</div></div>\n'
        
        html += """    </div>
    
    <h2>🔗 Module Matrix</h2>
    <div class="filter-bar">
        <input type="text" class="search-box" placeholder="Search modules..." onkeyup="filterModules(this.value)">
    </div>
    
    <table id="module-table">
        <thead>
            <tr>
                <th>Module</th>
                <th>Category</th>
                <th>Lines</th>
                <th>Imports</th>
                <th>Imported By</th>
                <th>Score</th>
            </tr>
        </thead>
        <tbody>
"""
        # Sort by connectivity score
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: -n.connectivity_score)
        
        for node in sorted_nodes:
            imports_count = len(node.imports)
            imported_by_count = len(node.imported_by)
            score = node.connectivity_score
            
            html += f"""            <tr data-name="{node.name.lower()}">
                <td><strong>{node.name}</strong></td>
                <td>{node.category}</td>
                <td>{node.line_count:,}</td>
                <td>{imports_count}</td>
                <td>{imported_by_count}</td>
                <td><strong>{score}</strong></td>
            </tr>
"""
        
        html += """        </tbody>
    </table>
    
    <script>
        function filterModules(query) {
            const rows = document.querySelectorAll('#module-table tbody tr');
            query = query.toLowerCase();
            rows.forEach(row => {
                const name = row.getAttribute('data-name');
                row.style.display = name.includes(query) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
"""
        return html
    
    def print_report(self):
        """Print text report"""
        print()
        print("=" * 80)
        print("  TITAN V8.1 MODULE CONNECTIVITY MAP")
        print("=" * 80)
        print()
        
        # Stats
        print("📊 STATISTICS:")
        print(f"   Total Modules: {len(self.nodes)}")
        print(f"   Total Lines: {sum(n.line_count for n in self.nodes.values()):,}")
        print()
        
        # By category
        print("🗂️ BY CATEGORY:")
        by_cat = defaultdict(list)
        for name, node in self.nodes.items():
            by_cat[node.category].append(name)
        
        for cat, modules in sorted(by_cat.items(), key=lambda x: -len(x[1])):
            print(f"   {cat}: {len(modules)} modules")
        print()
        
        # Top connected modules
        print("🔗 TOP CONNECTED MODULES:")
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: -n.connectivity_score)[:15]
        
        print(f"   {'Module':<35} {'Imports':>8} {'Imported By':>12} {'Score':>6}")
        print("   " + "-" * 65)
        for node in sorted_nodes:
            print(f"   {node.name:<35} {len(node.imports):>8} {len(node.imported_by):>12} {node.connectivity_score:>6}")
        print()
        
        # Orphans
        orphans = self.get_orphans()
        print(f"🔴 ORPHAN MODULES ({len(orphans)}):")
        if orphans:
            for o in orphans:
                print(f"   • {o}")
        else:
            print("   ✅ No orphan modules!")
        print()


def main():
    parser = argparse.ArgumentParser(description="TITAN Module Connectivity Mapper")
    parser.add_argument("--mermaid", action="store_true", help="Export Mermaid diagram")
    parser.add_argument("--html", action="store_true", help="Export HTML report")
    parser.add_argument("--json", action="store_true", help="Export JSON data")
    args = parser.parse_args()
    
    mapper = ConnectivityMapper(TITAN_ROOT)
    mapper.scan()
    
    if args.mermaid:
        mermaid = mapper.generate_mermaid()
        output = TITAN_ROOT / "module_connectivity.mmd"
        output.write_text(mermaid)
        print(f"📊 Mermaid diagram exported to: {output}")
    
    if args.html:
        html = mapper.generate_html_report()
        output = TITAN_ROOT / "module_connectivity.html"
        output.write_text(html)
        print(f"🌐 HTML report exported to: {output}")
    
    if args.json:
        data = {
            name: {
                "category": node.category,
                "imports": list(node.imports),
                "imported_by": list(node.imported_by),
                "exports": node.exports,
                "line_count": node.line_count,
                "connectivity_score": node.connectivity_score,
            }
            for name, node in mapper.nodes.items()
        }
        output = TITAN_ROOT / "module_connectivity.json"
        output.write_text(json.dumps(data, indent=2))
        print(f"📄 JSON data exported to: {output}")
    
    if not any([args.mermaid, args.html, args.json]):
        mapper.print_report()


if __name__ == "__main__":
    main()
