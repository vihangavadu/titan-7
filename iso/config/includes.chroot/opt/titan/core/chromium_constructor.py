"""
PROMETHEUS-CORE v3.0 :: MODULE: CONSTRUCTOR
AUTHORITY: Dva.13 | STATUS: OPERATIONAL
PURPOSE: Structural Synthesis of Chromium/Multilogin X Profile Directories.
         Creates the empty '37ab...' scaffolding required for the Burner to attach.
"""

import os
import json
import shutil
from pathlib import Path

class ProfileConstructor:
    def __init__(self, output_dir="generated_profiles", uuid="37ab1612-c285-4314-b32a-6a06d35d6d84"):
        self.base_dir = Path(output_dir)
        self.uuid = uuid
        self.profile_path = self.base_dir / self.uuid
        self.default_dir = self.profile_path / "Default"

    def _kill_chrome_procs(self):
        """Attempt to terminate local Chrome processes to release profile locks."""
        try:
            import subprocess
            subprocess.run(['taskkill', '/IM', 'chrome.exe', '/F'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print('[CONSTRUCTOR] Attempted to kill chrome processes to release locks.')
        except Exception:
            pass

    def scaffold(self, force=False):
        """
        Builds the directory skeleton. If it exists, it obliterates it first to ensure
        a sterile environment for the Burner. Pass `force=True` to attempt killing Chrome
        and aggressively remove the previous artifact to guarantee exact UUID creation.
        """
        print(f"[CONSTRUCTOR] Initiating structural synthesis for UUID: {self.uuid}...")
        
        if self.profile_path.exists():
            print("[CONSTRUCTOR] Detected existing artifact. Purging...")
            try:
                if force:
                    self._kill_chrome_procs()
                shutil.rmtree(self.profile_path)
            except Exception as e:
                print(f"[CONSTRUCTOR] Initial purge failed: {e}. Attempting forced cleanup...")
                # Attempt to reset permissions and remove files manually
                for root, dirs, files in os.walk(self.profile_path, topdown=False):
                    for name in files:
                        fn = os.path.join(root, name)
                        try:
                            os.chmod(fn, 0o666)
                            os.remove(fn)
                        except Exception:
                            pass
                    for name in dirs:
                        dn = os.path.join(root, name)
                        try:
                            os.rmdir(dn)
                        except Exception:
                            pass
                try:
                    shutil.rmtree(self.profile_path)
                except Exception as e2:
                    if force:
                        print(f"[CONSTRUCTOR] Forced cleanup failed: {e2}. Will attempt to move aside the locked folder and proceed.")
                        try:
                            import time
                            archive = self.base_dir / f"{self.uuid}.locked.{int(time.time())}"
                            shutil.move(str(self.profile_path), str(archive))
                            print(f"[CONSTRUCTOR] Moved locked folder to {archive}")
                        except Exception as e:
                            print(f"[CONSTRUCTOR] Move aside failed ({e}). Will attempt to populate the existing locked folder in place.")
                            # Instead of failing or creating a new UUID, proceed to use the existing folder
                            self.use_existing = True
                            self.profile_path = self.base_dir / self.uuid
                            self.default_dir = self.profile_path / "Default"
                            print(f"[CONSTRUCTOR] Proceeding with existing artifact UUID: {self.uuid}")

                    else:
                        print(f"[CONSTRUCTOR] Forced cleanup failed: {e2}. Will create a new artifact UUID to avoid locked files.")
                        # Fallback: do not raise; create a new uuid suffix to avoid collision with locked directory
                        import time
                        self.uuid = f"{self.uuid}-{int(time.time())}"
                        self.profile_path = self.base_dir / self.uuid
                        self.default_dir = self.profile_path / "Default"
                        print(f"[CONSTRUCTOR] New artifact UUID: {self.uuid}")

        # Create Core Directories
        dirs_to_create = [
            self.default_dir,
            self.default_dir / "Local Storage" / "leveldb",
            self.default_dir / "Network",
            self.default_dir / "Session Storage",
            self.profile_path / "ShaderCache",
            self.profile_path / "GrShaderCache"
        ]

        for d in dirs_to_create:
            d.mkdir(parents=True, exist_ok=True)
            print(f"  > Created node: {d}")

    def inject_preferences(self):
        """
        Injects the 'Preferences' JSON to pre-configure the browser state 
        (e.g., disabling automation bars, setting flags).
        """
        prefs = {
            "browser": {
                "show_home_button": True,
                "check_default_browser": False
            },
            "credentials_enable_service": False,
            "profile": {
                "password_manager_enabled": True,
                "name": "Person 1"
            },
            # Anti-Fingerprinting pre-seeds
            "webrtc": {
                "multiple_routes_enabled": False
            }
        }
        
        prefs_path = self.default_dir / "Preferences"
        with open(prefs_path, "w") as f:
            json.dump(prefs, f)
        print(f"[CONSTRUCTOR] Injected 'Preferences' seed file.")

    def build_skeleton(self, proxy_config=None, persona=None):
        """Compatibility wrapper for the deployment blueprint.

        Returns (profile_path, uuid_str)
        """
        # Ensure base dir exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Scaffold directory tree and preferences
        self.scaffold(force=False)
        self.inject_preferences()
        return str(self.profile_path.absolute()), self.uuid

    def run(self, force=False):
        self.scaffold(force=force)
        self.inject_preferences()
        print("[CONSTRUCTOR] Structure complete. Ready for Burner attachment.")
        return str(self.profile_path.absolute())

# Backwards-compatible alias for previous interface
Constructor = ProfileConstructor

if __name__ == "__main__":
    c = ProfileConstructor()
    c.run()
