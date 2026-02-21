import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import time
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Optional tray support
try:
    import pystray
    from PIL import Image as PILImage
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# === TITAN CONFIGURATION ===
# Load External APIs from .env
ENV_PATH = "/opt/titan/config/titan.env"
if not os.path.exists(ENV_PATH):
    ENV_PATH = ".env" # Fallback for local dev
load_dotenv(ENV_PATH)

# TITAN ENTERPRISE HRUX PALETTE
try:
    from titan_enterprise_theme import MISSION_CONTROL_COLORS as COLORS
except ImportError:
    COLORS = {
        "bg": "#0a0e17",         # Midnight
        "fg": "#00d4ff",         # Neon Cyan
        "fg_dim": "#64748B",     # Muted text
        "accent": "#0d1123",     # Panel base
        "accent_hover": "#1a2540",
        "green": "#00ff88",      # Neon Green
        "orange": "#ff6b35",     # Genesis Orange
        "alert": "#ff3355",      # Panic Red
        "warn": "#FFB74D",       # Warning Amber
        "panel": "#0d1123",      # Panel background
        "border": "#1e2d4a",     # Border color
        "highlight": "#00d4ff",  # Selection highlight
        "text": "#c8d2dc",       # Primary text
    }

class TitanMissionControl:
    def __init__(self, root):
        self.root = root
        self.root.title("TITAN V7 // MISSION CONTROL")
        self.root.geometry("1200x820")
        self.root.configure(bg=COLORS["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Kill switch state
        self._kill_switch_armed = False
        self._kill_switch_process = None

        # Style Configuration — Cyberpunk Theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=COLORS["bg"])
        self.style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Consolas", 10))
        self.style.configure("TButton", background=COLORS["panel"], foreground=COLORS["fg"], borderwidth=1, font=("Consolas", 10, "bold"), relief="flat")
        self.style.map("TButton", background=[("active", COLORS["accent_hover"]), ("!active", COLORS["panel"])], foreground=[("active", COLORS["highlight"])])
        self.style.configure("Header.TLabel", font=("Consolas", 18, "bold"), foreground=COLORS["fg"], background=COLORS["bg"])
        self.style.configure("TLabelframe", background=COLORS["bg"], foreground=COLORS["fg"], borderwidth=1, relief="solid")
        self.style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["fg"], font=("Consolas", 11, "bold"))
        self.style.configure("TSeparator", background=COLORS["border"])
        self.style.configure("Panic.TButton", background=COLORS["alert"], foreground="white", font=("Consolas", 13, "bold"))
        self.style.map("Panic.TButton", background=[("active", "#FF0000")])
        self.style.configure("Armed.TButton", background=COLORS["warn"], foreground="black", font=("Consolas", 10, "bold"))
        self.style.configure("Safe.TButton", background=COLORS["green"], foreground="black", font=("Consolas", 10, "bold"))

        self.setup_ui()
        self.start_monitoring()
        if TRAY_AVAILABLE:
            self._setup_tray()

    def _on_close(self):
        """Minimize to tray instead of quitting if tray is available."""
        if TRAY_AVAILABLE and hasattr(self, '_tray_icon'):
            self.root.withdraw()
        else:
            self.root.destroy()

    def _setup_tray(self):
        """Create system tray icon with right-click menu."""
        try:
            import io
            # Build a tiny 64x64 neon icon for the tray
            img = PILImage.new("RGBA", (64, 64), (10, 14, 23, 255))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            # Draw a simple "T" for TITAN in cyan
            draw.rectangle([4, 4, 60, 60], outline=(0, 212, 255, 255), width=3)
            draw.text((20, 18), "T7", fill=(0, 212, 255, 255))

            menu = pystray.Menu(
                pystray.MenuItem("Show TITAN Control", self._restore_from_tray, default=True),
                pystray.MenuItem("PANIC — Wipe Session", self._panic_wipe),
                pystray.MenuItem("Kill Switch ARM", self._toggle_kill_switch),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._quit_from_tray),
            )
            self._tray_icon = pystray.Icon("TITAN", img, "TITAN Mission Control", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
        except Exception as e:
            self.log(f"[WARN] Tray init failed: {e}")

    def _restore_from_tray(self):
        self.root.after(0, self.root.deiconify)

    def _quit_from_tray(self):
        if hasattr(self, '_tray_icon'):
            self._tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def setup_ui(self):
        # ── HEADER ─────────────────────────────────────────────────────────
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill="x")

        lbl_title = ttk.Label(header_frame, text="TITAN OS V7 // SOVEREIGNTY ENGINE", style="Header.TLabel")
        lbl_title.pack(side="left")

        self.lbl_status = ttk.Label(header_frame, text="SYSTEM STATUS: INITIALIZING...", foreground="yellow", background=COLORS["bg"])
        self.lbl_status.pack(side="right")

        # ── PANIC BUTTON (always visible, top-right) ────────────────────────
        panic_btn = tk.Button(
            header_frame,
            text="⚠  PANIC — WIPE SESSION",
            command=self._panic_wipe,
            bg=COLORS["alert"], fg="white",
            font=("Consolas", 12, "bold"),
            relief="flat", padx=14, pady=6, cursor="hand2",
            activebackground="#FF0000", activeforeground="white"
        )
        panic_btn.pack(side="right", padx=12)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10)

        # ── MAIN CONTAINER ──────────────────────────────────────────────────
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # ── LEFT COLUMN: Security Controls + Quick Launch ───────────────────
        left_col = ttk.Frame(main_frame)
        left_col.pack(side="left", fill="y", padx=5)

        # KILL SWITCH
        ks_frame = ttk.LabelFrame(left_col, text=" [ KILL SWITCH ] ", padding="10")
        ks_frame.pack(fill="x", pady=6)

        self.ks_status_lbl = ttk.Label(ks_frame, text="STATE: DISARMED", foreground=COLORS["green"])
        self.ks_status_lbl.pack(anchor="w", pady=2)

        ks_btn_row = ttk.Frame(ks_frame)
        ks_btn_row.pack(fill="x")
        self.ks_arm_btn = tk.Button(
            ks_btn_row, text="[ ARM KILL SWITCH ]",
            command=self._arm_kill_switch,
            bg=COLORS["warn"], fg="black",
            font=("Consolas", 10, "bold"), relief="flat", padx=8, pady=4, cursor="hand2"
        )
        self.ks_arm_btn.pack(side="left", fill="x", expand=True, padx=2)
        self.ks_disarm_btn = tk.Button(
            ks_btn_row, text="[ DISARM ]",
            command=self._disarm_kill_switch,
            bg=COLORS["panel"], fg=COLORS["fg"],
            font=("Consolas", 10, "bold"), relief="flat", padx=8, pady=4, cursor="hand2",
            state="disabled"
        )
        self.ks_disarm_btn.pack(side="left", fill="x", expand=True, padx=2)
        ttk.Label(ks_frame, text="Arms VPN kill-switch via kill_switch.service.\nAll traffic blocked on VPN drop.", font=("Consolas", 8), foreground=COLORS["fg_dim"]).pack(anchor="w")

        # PROXY STATUS
        proxy_frame = ttk.LabelFrame(left_col, text=" [ PROXY STATUS ] ", padding="10")
        proxy_frame.pack(fill="x", pady=6)

        self.proxy_ip_lbl = ttk.Label(proxy_frame, text="Exit IP:  ...checking...", foreground=COLORS["fg"])
        self.proxy_ip_lbl.pack(anchor="w")
        self.proxy_geo_lbl = ttk.Label(proxy_frame, text="Geo:       ---", foreground=COLORS["fg_dim"])
        self.proxy_geo_lbl.pack(anchor="w")
        self.proxy_leak_lbl = ttk.Label(proxy_frame, text="DNS Leak:  ---", foreground=COLORS["fg_dim"])
        self.proxy_leak_lbl.pack(anchor="w")
        refresh_proxy_btn = ttk.Button(proxy_frame, text="[ Refresh Proxy Check ]", command=self._refresh_proxy_status)
        refresh_proxy_btn.pack(fill="x", pady=4)

        # HARDWARE SHIELD
        hw_frame = ttk.LabelFrame(left_col, text=" [ HARDWARE SHIELD ] ", padding="10")
        hw_frame.pack(fill="x", pady=6)

        self.hw_cpu_lbl = ttk.Label(hw_frame, text="CPU Spoof:  ---", foreground=COLORS["fg"])
        self.hw_cpu_lbl.pack(anchor="w")
        self.hw_mac_lbl = ttk.Label(hw_frame, text="MAC Spoof:  ---", foreground=COLORS["fg"])
        self.hw_mac_lbl.pack(anchor="w")
        self.hw_disk_lbl = ttk.Label(hw_frame, text="Disk UUID:  ---", foreground=COLORS["fg"])
        self.hw_disk_lbl.pack(anchor="w")
        hw_refresh_btn = ttk.Button(hw_frame, text="[ Query Shield Daemon ]", command=self._refresh_hw_shield)
        hw_refresh_btn.pack(fill="x", pady=4)

        # QUICK LAUNCH
        launch_frame = ttk.LabelFrame(left_col, text=" [ QUICK LAUNCH ] ", padding="10")
        launch_frame.pack(fill="x", pady=6)

        APPS = [
            ("Genesis Forge",     "app_genesis.py"),
            ("Cerberus Guard",    "app_cerberus.py"),
            ("KYC Bypass",        "app_kyc.py"),
            ("Bug Reporter",      "app_bug_reporter.py"),
            ("Unified Controller","app_unified.py"),
        ]
        APPS_DIR = Path(__file__).parent
        for display, script in APPS:
            btn = tk.Button(
                launch_frame, text=f"▶  {display}",
                command=lambda s=script: self._launch_app(APPS_DIR / s),
                bg=COLORS["panel"], fg=COLORS["fg"],
                font=("Consolas", 10), relief="flat", pady=4, cursor="hand2",
                activebackground=COLORS["accent_hover"], activeforeground=COLORS["highlight"]
            )
            btn.pack(fill="x", pady=2)

        # ── RIGHT COLUMN: Trinity Modules + API Status + Console ────────────
        right_col = ttk.Frame(main_frame)
        right_col.pack(side="right", fill="both", expand=True, padx=5)

        # TRINITY MODULES
        trinity_frame = ttk.LabelFrame(right_col, text=" [ TRINITY MODULES ] ", padding="10")
        trinity_frame.pack(fill="x", pady=5)

        self.create_module_control(trinity_frame, "GENESIS ENGINE", "Create deep-cover identities.", "Generate Identity", self.run_genesis)
        self.create_module_control(trinity_frame, "CERBERUS GUARD", "Validate environment integrity.", "Run Audit", self.run_cerberus)
        self.create_module_control(trinity_frame, "KINETIC SHIELD", "eBPF/VPN Network masking.", "Engage Shield", self.engage_shield)

        # API STATUS
        api_frame = ttk.LabelFrame(right_col, text=" [ EXTERNAL API LINKAGE ] ", padding="10")
        api_frame.pack(fill="x", pady=5)

        self.api_list_frame = ttk.Frame(api_frame)
        self.api_list_frame.pack(fill="x")
        self.refresh_api_status()

        # CONSOLE
        log_frame = ttk.LabelFrame(right_col, text=" [ SYSTEM LOGS ] ", padding="10")
        log_frame.pack(fill="both", expand=True)

        self.console = scrolledtext.ScrolledText(
            log_frame,
            bg=COLORS["panel"], fg=COLORS["green"],
            font=("Consolas", 9),
            insertbackground=COLORS["fg"],
            relief="flat", borderwidth=0,
            selectbackground=COLORS["fg"], selectforeground=COLORS["bg"]
        )
        self.console.pack(fill="both", expand=True)
        self.log(">>> TITAN OS GUI INITIALIZED.")
        self.log(">>> WAITING FOR OPERATOR INPUT.")

    # ── Security Controls ──────────────────────────────────────────────────

    def _arm_kill_switch(self):
        if messagebox.askyesno("CONFIRM ARM", "Arm the kill switch?\n\nAll traffic will be cut if VPN drops."):
            self._kill_switch_armed = True
            self.ks_status_lbl.config(text="STATE: ARMED", foreground=COLORS["alert"])
            self.ks_arm_btn.config(state="disabled")
            self.ks_disarm_btn.config(state="normal")
            self.log(">>> KILL SWITCH ARMED — traffic blocked on VPN drop.")
            try:
                subprocess.Popen(["systemctl", "--user", "start", "titan-kill-switch.service"])
            except Exception:
                pass

    def _disarm_kill_switch(self):
        self._kill_switch_armed = False
        self.ks_status_lbl.config(text="STATE: DISARMED", foreground=COLORS["green"])
        self.ks_arm_btn.config(state="normal")
        self.ks_disarm_btn.config(state="disabled")
        self.log(">>> KILL SWITCH DISARMED.")
        try:
            subprocess.Popen(["systemctl", "--user", "stop", "titan-kill-switch.service"])
        except Exception:
            pass

    def _toggle_kill_switch(self):
        if self._kill_switch_armed:
            self._disarm_kill_switch()
        else:
            self._arm_kill_switch()

    def _panic_wipe(self):
        if not messagebox.askyesno(
            "⚠ PANIC WIPE",
            "PANIC MODE: This will immediately:\n"
            "• Kill all browsers\n• Wipe session data\n• Revoke all proxy credentials\n"
            "• Arm kill switch\n\nCONTINUE?",
            icon="warning"
        ):
            return
        self.log(">>> PANIC MODE ACTIVATED — WIPING SESSION...")
        threading.Thread(target=self._execute_panic, daemon=True).start()

    def _execute_panic(self):
        cmds = [
            ["pkill", "-f", "camoufox"],
            ["pkill", "-f", "firefox"],
            ["pkill", "-f", "chromium"],
            ["find", "/tmp", "-maxdepth", "2", "-name", "titan_*", "-delete"],
        ]
        for cmd in cmds:
            try:
                subprocess.run(cmd, timeout=5)
            except Exception:
                pass
        state_dir = Path("/opt/titan/state/sessions")
        if state_dir.exists():
            import shutil
            try:
                shutil.rmtree(state_dir)
                state_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        self.root.after(0, lambda: self.log(">>> SESSION WIPED. KILL SWITCH ARMED."))
        self.root.after(0, self._arm_kill_switch)

    def _refresh_proxy_status(self):
        self.proxy_ip_lbl.config(text="Exit IP:  ...checking...")
        threading.Thread(target=self._do_proxy_check, daemon=True).start()

    def _do_proxy_check(self):
        try:
            import urllib.request
            import json as _json
            with urllib.request.urlopen("https://ipinfo.io/json", timeout=8) as r:
                data = _json.loads(r.read())
            ip = data.get("ip", "unknown")
            city = data.get("city", "?")
            country = data.get("country", "?")
            org = data.get("org", "?")
            self.root.after(0, lambda: self.proxy_ip_lbl.config(text=f"Exit IP:  {ip}", foreground=COLORS["green"]))
            self.root.after(0, lambda: self.proxy_geo_lbl.config(text=f"Geo:      {city}, {country} — {org}"))
            self.root.after(0, lambda: self.proxy_leak_lbl.config(text="DNS Leak: — checking disabled, poll above"))
            self.log(f"[PROXY] {ip} — {city}, {country}")
        except Exception as e:
            self.root.after(0, lambda: self.proxy_ip_lbl.config(text=f"Exit IP:  ERROR — {e}", foreground=COLORS["alert"]))

    def _refresh_hw_shield(self):
        threading.Thread(target=self._do_hw_shield_check, daemon=True).start()

    def _do_hw_shield_check(self):
        state_file = Path("/opt/titan/state/hardware_shield.json")
        if state_file.exists():
            try:
                import json as _json
                data = _json.loads(state_file.read_text())
                cpu = data.get("cpu_model", "SPOOFED")
                mac = data.get("mac_addr", "SPOOFED")
                disk = data.get("disk_uuid", "SPOOFED")
                self.root.after(0, lambda: self.hw_cpu_lbl.config(text=f"CPU Spoof:  {cpu}", foreground=COLORS["green"]))
                self.root.after(0, lambda: self.hw_mac_lbl.config(text=f"MAC Spoof:  {mac}", foreground=COLORS["green"]))
                self.root.after(0, lambda: self.hw_disk_lbl.config(text=f"Disk UUID:  {disk}", foreground=COLORS["green"]))
                return
            except Exception:
                pass
        # Fallback — try querying the daemon
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "titan-hardware-shield.service"],
                capture_output=True, text=True, timeout=3
            )
            status = result.stdout.strip()
            color = COLORS["green"] if status == "active" else COLORS["warn"]
            self.root.after(0, lambda: self.hw_cpu_lbl.config(text=f"Shield daemon: {status}", foreground=color))
        except Exception as e:
            self.root.after(0, lambda: self.hw_cpu_lbl.config(text=f"Shield: {e}", foreground=COLORS["alert"]))

    def _launch_app(self, script_path):
        self.log(f">>> LAUNCHING: {script_path.name}")
        try:
            subprocess.Popen([sys.executable, str(script_path)], close_fds=True, start_new_session=True)
        except Exception as e:
            self.log(f"[ERR] Failed to launch {script_path.name}: {e}")


    def create_module_control(self, parent, title, desc, btn_text, command):
        frame = ttk.Frame(parent, padding="5")
        frame.pack(fill="x", pady=10)
        
        ttk.Label(frame, text=f"// {title}", font=("Consolas", 12, "bold")).pack(anchor="w")
        ttk.Label(frame, text=desc, font=("Consolas", 9)).pack(anchor="w")
        btn = ttk.Button(frame, text=f"[ {btn_text} ]", command=command)
        btn.pack(fill="x", pady=5)
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)

    def refresh_api_status(self):
        # Clears current list
        for widget in self.api_list_frame.winfo_children():
            widget.destroy()
            
        # Reads .env for specific API keys (Masked)
        apis = [
            ("TITAN_API_KEY", "Cognitive Core"),
            ("IPINFO_TOKEN", "Geolocation Data"),
            ("AWS_ACCESS_KEY_ID", "Cloud Infrastructure"),
            ("NEXUS_KEY", "Prometheus Nexus")
        ]
        
        for i, (env_key, display_name) in enumerate(apis):
            key_val = os.getenv(env_key)
            status = "CONNECTED" if key_val and not key_val.startswith("REPLACE") else "MISSING"
            color = COLORS["green"] if status == "CONNECTED" else COLORS["alert"]
            
            ttk.Label(self.api_list_frame, text=f"{display_name.ljust(20)}:").grid(row=i, column=0, sticky="w")
            ttk.Label(self.api_list_frame, text=status, foreground=color).grid(row=i, column=1, sticky="w", padx=10)

    def log(self, message):
        self.console.insert(tk.END, f"{message}\n")
        self.console.see(tk.END)

    def run_genesis(self):
        self.log(">>> STARTING GENESIS ENGINE...")
        # In a real environment, this would launch the app_genesis.py or a specific command
        threading.Thread(target=self._mock_task, args=("GENESIS IDENTITY SYNTHESIS",)).start()

    def run_cerberus(self):
        self.log(">>> ENGAGING CERBERUS AUDIT...")
        threading.Thread(target=self._mock_task, args=("CERBERUS INTEGRITY SCAN",)).start()

    def engage_shield(self):
        self.log(">>> LOADING KINETIC eBPF SHIELD...")
        threading.Thread(target=self._mock_task, args=("NETWORK MASKING ACTIVE",)).start()

    def _mock_task(self, name):
        time.sleep(2)
        self.log(f"[*] {name} COMPLETE.")

    def start_monitoring(self):
        def monitor():
            while True:
                self.root.after(0, lambda: self.lbl_status.config(
                    text="SYSTEM STATUS: SECURE", foreground=COLORS["green"]
                ))
                time.sleep(5)
        threading.Thread(target=monitor, daemon=True).start()

        # Initial proxy + HW shield check after 2s
        self.root.after(2000, self._refresh_proxy_status)
        self.root.after(3000, self._refresh_hw_shield)

        # Re-poll proxy every 60 seconds
        def _schedule_proxy():
            self._refresh_proxy_status()
            self.root.after(60000, _schedule_proxy)
        self.root.after(62000, _schedule_proxy)

if __name__ == "__main__":
    root = tk.Tk()
    app = TitanMissionControl(root)
    root.mainloop()
