import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import time
import os
import sys
import json
from dotenv import load_dotenv

# === TITAN CONFIGURATION ===
# Load External APIs from .env
ENV_PATH = "/opt/titan/config/titan.env"
if not os.path.exists(ENV_PATH):
    ENV_PATH = ".env" # Fallback for local dev
load_dotenv(ENV_PATH)

# TITAN THEME PALETTE
COLORS = {
    "bg": "#0f0f0f",
    "fg": "#00ff41",  # Matrix Green
    "accent": "#003b00",
    "alert": "#ff3333",
    "panel": "#1a1a1a"
}

class TitanMissionControl:
    def __init__(self, root):
        self.root = root
        self.root.title("System Control Panel")
        self.root.geometry("1024x768")
        self.root.configure(bg=COLORS["bg"])
        
        # Style Configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=COLORS["bg"])
        self.style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["fg"], font=("Consolas", 10))
        self.style.configure("TButton", background=COLORS["panel"], foreground=COLORS["fg"], borderwidth=1, font=("Consolas", 10, "bold"))
        self.style.map("TButton", background=[("active", COLORS["accent"])])
        self.style.configure("Header.TLabel", font=("Consolas", 16, "bold"), foreground="#ffffff")
        
        self.setup_ui()
        self.start_monitoring()

    def setup_ui(self):
        # --- HEADER ---
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill="x")
        
        lbl_title = ttk.Label(header_frame, text="TITAN OS V7 // SOVEREIGNTY ENGINE", style="Header.TLabel")
        lbl_title.pack(side="left")
        
        self.lbl_status = ttk.Label(header_frame, text="SYSTEM STATUS: INITIALIZING...", foreground="yellow")
        self.lbl_status.pack(side="right")
        
        # --- MAIN CONTAINER ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # --- LEFT PANEL: TRINITY MODULES ---
        left_panel = ttk.LabelFrame(main_frame, text=" [ TRINITY MODULES ] ", padding="10")
        left_panel.pack(side="left", fill="y", padx=5)
        
        # 1. GENESIS (Profile Creation)
        self.create_module_control(left_panel, "GENESIS ENGINE", "Create deep-cover identities.", "Generate Identity", self.run_genesis)
        
        # 2. CERBERUS (Validation)
        self.create_module_control(left_panel, "CERBERUS GUARD", "Validate environment integrity.", "Run Audit", self.run_cerberus)
        
        # 3. NETWORK SHIELD (VPN/eBPF)
        self.create_module_control(left_panel, "KINETIC SHIELD", "eBPF/VPN Network masking.", "Engage Shield", self.engage_shield)

        # --- RIGHT PANEL: API & LOGS ---
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=5)
        
        # API Status Monitor
        api_frame = ttk.LabelFrame(right_panel, text=" [ EXTERNAL API LINKAGE ] ", padding="10")
        api_frame.pack(fill="x", pady=5)
        
        self.api_list_frame = ttk.Frame(api_frame)
        self.api_list_frame.pack(fill="x")
        self.refresh_api_status()
        
        # Console Output
        log_frame = ttk.LabelFrame(right_panel, text=" [ SYSTEM LOGS ] ", padding="10")
        log_frame.pack(fill="both", expand=True)
        
        self.console = scrolledtext.ScrolledText(log_frame, bg="black", fg=COLORS["fg"], font=("Consolas", 9), insertbackground="white")
        self.console.pack(fill="both", expand=True)
        self.log(">>> TITAN OS GUI INITIALIZED.")
        self.log(">>> WAITING FOR OPERATOR INPUT.")

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
            color = COLORS["fg"] if status == "CONNECTED" else COLORS["alert"]
            
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
                self.lbl_status.config(text="SYSTEM STATUS: SECURE", foreground=COLORS["fg"])
                time.sleep(5)
        threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TitanMissionControl(root)
    root.mainloop()
