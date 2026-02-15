# LUCID EMPIRE :: BIN FINDER
# Discover browser executables and essential binaries

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

class BinaryFinder:
    """Find and validate browser binaries."""
    
    FIREFOX_PATHS = [
        "/usr/bin/firefox",
        "/usr/local/bin/firefox",
        "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
        "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
        "/Applications/Firefox.app/Contents/MacOS/firefox",
    ]
    
    CHROME_PATHS = [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    
    @staticmethod
    def find_firefox():
        """Find Firefox executable."""
        for path in BinaryFinder.FIREFOX_PATHS:
            if os.path.exists(path):
                logger.info(f"Found Firefox at {path}")
                return path
        logger.warning("Firefox not found")
        return None
    
    @staticmethod
    def find_chrome():
        """Find Chrome/Chromium executable."""
        for path in BinaryFinder.CHROME_PATHS:
            if os.path.exists(path):
                logger.info(f"Found Chrome at {path}")
                return path
        logger.warning("Chrome not found")
        return None
    
    @staticmethod
    def get_browser_version(binary_path):
        """Get browser version from binary."""
        try:
            result = subprocess.run([binary_path, "--version"], capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to get version: {e}")
            return None
