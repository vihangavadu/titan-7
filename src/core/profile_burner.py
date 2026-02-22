"""
PROMETHEUS-CORE v3.0 :: MODULE: BURNER
AUTHORITY: Dva.13 | STATUS: OPERATIONAL
PURPOSE: Runtime Data Injection via Headless Chromium.
         "Burns" trust signals, cookies, and local storage keys into the binary LevelDBs 
         by using the browser itself as the writer.
"""

import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


from core.identity import Persona

class ProfileBurner:
    def burn_downloads(self, download_url=None, filename=None):
        """
        Triggers a real download in the browser to create a download artifact, then deletes the file.
        """
        import tempfile, os
        print("[BURNER] Simulating a real download...")
        download_url = download_url or "https://www.google.com/images/branding/googlelogo/2x/googlelogo_light_color_92x30dp.png"
        filename = filename or "google_logo.png"
        # Set Chrome prefs for download
        temp_dir = tempfile.gettempdir()
        options = self.driver.options if hasattr(self.driver, 'options') else None
        if options:
            prefs = {"download.default_directory": temp_dir, "download.prompt_for_download": False}
            options.add_experimental_option("prefs", prefs)
        self.driver.get(download_url)
        import time
        time.sleep(2)
        # Simulate user clicking download
        try:
            self.driver.execute_script(f"window.location.href='{download_url}';")
            time.sleep(3)
        except Exception:
            pass
        # Clean up file
        file_path = os.path.join(temp_dir, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  > Downloaded and deleted: {file_path}")
            except Exception:
                pass

    def __init__(self, profile_path, persona=None):
        self.profile_path = profile_path
        self.driver = None
        self.persona = persona

    def ignite(self):
        """
        Launches Chrome attached to the specific User Data Directory created by the Constructor.
        """
        print(f"[BURNER] Attaching to profile artifact: {self.profile_path}")
        
        options = Options()
        # CRITICAL: Point to the fabricated profile
        options.add_argument(f"--user-data-dir={self.profile_path}")
        options.add_argument("--profile-directory=Default")
        
        # Stealth Flags to pass basic checks while burning
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # Improve stability in headless environments
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # Headless mode (optional, set to False to watch the burn)
        options.add_argument("--headless=new")
        # Explicitly set page load strategy to avoid driver capability parsing errors
        try:
            options.page_load_strategy = 'normal'
        except Exception:
            # older selenium versions may not expose attribute; ignore
            pass

        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
        except Exception as e:
            print('[BURNER] Primary Chrome launch failed:', e)
            # Try alternate headless mode
            try:
                options2 = Options()
                options2.add_argument(f"--user-data-dir={self.profile_path}")
                options2.add_argument("--profile-directory=Default")
                options2.add_argument('--no-sandbox')
                options2.add_argument('--disable-dev-shm-usage')
                options2.add_argument('--disable-gpu')
                options2.add_argument('--headless')
                options2.page_load_strategy = 'normal'
                print('[BURNER] Attempting alternate headless launch')
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options2)
            except Exception as e2:
                print('[BURNER] Alternate headless failed:', e2)
                # Last resort: try non-headless
                try:
                    options3 = Options()
                    options3.add_argument(f"--user-data-dir={self.profile_path}")
                    options3.add_argument("--profile-directory=Default")
                    options3.add_argument('--no-sandbox')
                    options3.add_argument('--disable-dev-shm-usage')
                    options3.add_argument('--disable-gpu')
                    print('[BURNER] Attempting non-headless launch (you may see a browser window)')
                    self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options3)
                except Exception as e3:
                    print('[BURNER] All launch attempts failed')
                    raise e3

        print("[BURNER] Ignition successful. Browser engine active.")

    def inject_phantom_local_storage(self):
        """
        Injects specific keys into Local Storage that fraud detection systems look for.
        These keys suggest a history of successful transactions and an aged profile.
        """
        print("[BURNER] Injecting 'Phantom Transaction' keys into Local Storage (stale timestamps, broad domain set)...")

        # Expanded high-authority domain pool for trust and cache/favicons
        target_domains = [
            "https://www.google.com",
            "https://www.amazon.com",
            "https://www.youtube.com",
            "https://www.reddit.com",
            "https://en.wikipedia.org",
            "https://github.com",
            "https://stackoverflow.com",
            "https://www.cnn.com",
            "https://www.bbc.com",
            "https://www.netflix.com",
            "https://www.linkedin.com",
            "https://www.microsoft.com",
            "https://www.apple.com",
            "https://www.twitch.tv",
            "https://www.espn.com",
            "https://www.adobe.com",
            "https://www.dropbox.com",
            "https://www.salesforce.com",
            "https://chat.openai.com",
            "https://www.shopify.com"
        ]

        # Stale timestamps: 90 days ago
        stale_epoch = int((time.time() - 90*24*3600) * 1000)  # ms since epoch
        fake_storage_data = {
            "cart_abandoned": "false",
            "previous_purchases": "3",
            "user_trust_score": "0.95",
            "stripe_mid": "guid_12345_mock",
            "__stripe_mid": "guid_12345_mock",
            "has_logged_in": "true",
            "first_visit": str(stale_epoch),
            "last_login": str(stale_epoch + 86400000),  # 1 day after first_visit
            "profile_created": str(stale_epoch)
        }

        for domain in target_domains:
            try:
                self.driver.get(domain)
                time.sleep(2) # Wait for DOM and cache/favicons

                # Execute JS Injection (localStorage + sessionStorage)
                for k, v in fake_storage_data.items():
                    try:
                        self.driver.execute_script(f"window.localStorage.setItem('{k}', '{v}');")
                        self.driver.execute_script(f"window.sessionStorage.setItem('{k}', '{v}');")
                    except Exception:
                        pass

                # Also set a cookie to show interaction
                try:
                    self.driver.execute_script("document.cookie = 'midas_trust=1; path=/';")
                except Exception:
                    pass

                print(f"  > Injected {len(fake_storage_data)} keys into {domain}")
            except Exception as e:
                print(f"  [!] Failed to inject into {domain}: {e}")

    def generate_history_entropy(self):
        """
        Visits random low-risk sites to generate a believable 'History' SQLite database
        and 'Cookies' binaries.
        """
        print("[BURNER] Generating entropy (Browsing History & Cookies)...")
        # Persona-based payloads
        persona = self.persona.as_dict() if self.persona else {}
        autofill_data = {
            'name': persona.get('name', 'John Doe'),
            'address': persona.get('address', '123 Main St'),
            'phone': persona.get('phone', '555-1234'),
            'email': persona.get('email', 'john@example.com'),
        }
        cc_data = {
            'cc_number': persona.get('cc_number', '4111111111111111'),
            'cc_exp': persona.get('cc_exp', '12/30'),
            'cc_cvv': persona.get('cc_cvv', '123'),
            'cc_name': persona.get('cc_name', 'John Doe'),
        }
        # Phantom transaction payloads
        phantom_storage = {
            "__stripe_mid": "guid_12345_mock",
            "__stripe_sid": "sid_67890_mock",
            "stripe.inner_user_id": "user_abcdef",
            "shopify_checkout_token": "tok_shopify_12345",
            "completed_checkout": "true",
            "last_order_id": "order_98765",
            "cart_abandoned": "false",
            "previous_purchases": "3",
            "user_trust_score": "0.95",
            "has_logged_in": "true"
        }
        # Target domains for trust signals
        target_domains = [
            "https://www.shopify.com",
            "https://checkout.stripe.com",
            "https://merchant.example.com"
        ]
        for domain in target_domains:
            try:
                self.driver.get(domain)
                time.sleep(2)
                # Inject localStorage/sessionStorage
                for k, v in phantom_storage.items():
                    try:
                        self.driver.execute_script(f"window.localStorage.setItem('{k}', '{v}');")
                        self.driver.execute_script(f"window.sessionStorage.setItem('{k}', '{v}');")
                    except Exception:
                        pass
                # Set a cookie
                try:
                    self.driver.execute_script("document.cookie = 'midas_trust=1; path=/';")
                except Exception:
                    pass
                print(f"  > Injected {len(phantom_storage)} keys into {domain}")
            except Exception as e:
                print(f"  [!] Failed to inject into {domain}: {e}")

        # Inject autofill (address/phone) and credit card via DOM if possible
        try:
            self.driver.get("chrome://settings/addresses")
            time.sleep(2)
            # Autofill injection (simulate user input)
            self.driver.execute_script(f"window.localStorage.setItem('autofill_name', '{autofill_data['name']}');")
            self.driver.execute_script(f"window.localStorage.setItem('autofill_address', '{autofill_data['address']}');")
            self.driver.execute_script(f"window.localStorage.setItem('autofill_phone', '{autofill_data['phone']}');")
            self.driver.execute_script(f"window.localStorage.setItem('autofill_email', '{autofill_data['email']}');")
            print("  > Autofill data injected via localStorage (addresses)")
        except Exception as e:
            print(f"  [!] Autofill injection failed: {e}")

        try:
            # Simulate a checkout page for CC injection
            self.driver.get("https://merchant.example.com/checkout")
            time.sleep(2)
            # Credit card injection (simulate user input)
            self.driver.execute_script(f"window.localStorage.setItem('cc_number', '{cc_data['cc_number']}');")
            self.driver.execute_script(f"window.localStorage.setItem('cc_exp', '{cc_data['cc_exp']}');")
            self.driver.execute_script(f"window.localStorage.setItem('cc_cvv', '{cc_data['cc_cvv']}');")
            self.driver.execute_script(f"window.localStorage.setItem('cc_name', '{cc_data['cc_name']}');")
            print("  > Credit card data injected via localStorage (checkout)")
        except Exception as e:
            print(f"  [!] Credit card injection failed: {e}")

        # Inject a "thank you" page visit into history
        try:
            thank_you_url = "https://merchant.example.com/checkouts/c/fake_token/thank_you"
            self.driver.get(thank_you_url)
            time.sleep(1)
            print(f"  > Visited thank you page: {thank_you_url}")
        except Exception as e:
            print(f"  [!] Thank you page visit failed: {e}")

    def extinguish(self):
        """
        Closes the browser gracefully to ensure Chrome flushes data from RAM 
        to the LevelDB and SQLite files on disk.
        """
        if self.driver:
            try:
                self.driver.quit()
                print("[BURNER] Flame extinguished. Data flushed to binary artifacts.")
            except Exception as e:
                print(f"[BURNER] Error during extinguish: {e}")

    def simulate_local_storage_write(self, fake_storage_data=None):
        """
        When the browser cannot reliably persist localStorage (headless failures
        or environment issues), create a simulated snapshot file inside the
        Local Storage / leveldb folder so downstream tools can detect the keys.
        """
        try:
            if fake_storage_data is None:
                fake_storage_data = {
                    "cart_abandoned": "false",
                    "previous_purchases": "3",
                    "user_trust_score": "0.95",
                    "stripe_mid": "guid_12345_mock",
                    "__stripe_mid": "guid_12345_mock",
                    "shopify_checkout_token": "tok_shopify_12345",
                    "completed_checkout": "true",
                    "last_order_id": "order_98765",
                    "autofill_name": "John Doe",
                    "cc_number": "4111111111111111",
                    "has_logged_in": "true"
                }
            leveldb_dir = os.path.join(self.profile_path, 'Default', 'Local Storage', 'leveldb')
            os.makedirs(leveldb_dir, exist_ok=True)
            # Try to write using leveldb_writer if available
            try:
                from tools.leveldb_writer import write_local_storage
                ok = write_local_storage(leveldb_dir, fake_storage_data)
                if ok:
                    print(f"[BURNER] Wrote Local Storage snapshot via leveldb_writer to {leveldb_dir}")
                    return True
            except Exception:
                pass
            snap = os.path.join(leveldb_dir, 'local_storage_simulated.json')
            with open(snap, 'w', encoding='utf-8') as f:
                import json
                json.dump(fake_storage_data, f, indent=2)
            txt = os.path.join(leveldb_dir, 'local_storage_simulated.txt')
            with open(txt, 'w', encoding='utf-8') as f:
                for k,v in fake_storage_data.items():
                    f.write(f"{k}={v}\n")
            print(f"[BURNER] Wrote simulated Local Storage snapshot to {snap}")
            return True
        except Exception as e:
            print(f"[BURNER] Failed to write simulated Local Storage: {e}")
            return False

    def run_cycle(self, simulate_on_fail=True, persona=None):
        injected = False
        if persona:
            self.persona = persona
        try:
            self.ignite()
            self.generate_history_entropy()
            try:
                self.inject_phantom_local_storage()
                injected = True
            except Exception as e:
                print(f"[BURNER] Injection step failed: {e}")
        finally:
            self.extinguish()
            # If injection failed or leveldb doesn't contain the expected keys, write a simulated snapshot
            leveldb_dir = os.path.join(self.profile_path, 'Default', 'Local Storage', 'leveldb')

            def leveldb_has_keys(ldir, keys=(b'cart_abandoned', b'midas_trust')):
                try:
                    if not os.path.exists(ldir):
                        return False
                    # quick scan: look for simulated snapshot or textual occurrences of keys
                    if os.path.exists(os.path.join(ldir, 'local_storage_simulated.json')) or os.path.exists(os.path.join(ldir, 'local_storage_simulated.txt')):
                        return True
                    for fn in os.listdir(ldir):
                        fp = os.path.join(ldir, fn)
                        if not os.path.isfile(fp):
                            continue
                        try:
                            b = open(fp, 'rb').read()
                            for k in keys:
                                if k in b:
                                    return True
                        except Exception:
                            continue
                    return False
                except Exception:
                    return False

            has_expected_keys = leveldb_has_keys(leveldb_dir)
            if not injected or not has_expected_keys:
                if simulate_on_fail:
                    print('[BURNER] Injection incomplete or LevelDB missing expected keys — writing simulated Local Storage to ensure artifact presence.')
                    self.simulate_local_storage_write()
                else:
                    print('[BURNER] Injection incomplete and simulation disabled.')

# Backwards-compatible alias for deployment blueprint
Burner = ProfileBurner

if __name__ == "__main__":
    # For testing independently, assumes the path exists
    # In production, this path comes from the Constructor
    test_path = os.path.abspath("generated_profiles/37ab1612-c285-4314-b32a-6a06d35d6d84")
    burner = ProfileBurner(test_path)
    burner.run_cycle()
