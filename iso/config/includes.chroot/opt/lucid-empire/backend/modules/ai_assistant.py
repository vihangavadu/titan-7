#!/usr/bin/env python3
"""
TITAN AI Assistant — Local LLM/VLM Integration via Ollama

Authority: Dva.12 | Status: TITAN_ACTIVE | Version: 7.0

Provides on-device AI capabilities for the human operator:
  - CAPTCHA analysis: VLM analyzes screenshot, displays solution to user
  - Page context: LLM summarizes page structure for manual navigation
  - Profile advice: Suggests persona-consistent behavior patterns

CRITICAL: This module does NOT automate any browser interaction.
The AI provides ANALYSIS and SUGGESTIONS that the USER manually executes.
No Selenium, Playwright, CDP, or any browser automation protocol is used.

The human-in-the-loop model ensures authentic behavioral biometrics
(mouse dynamics, keystroke latency, scroll patterns) that no automation
framework can replicate.

Requires: Ollama running locally (ollama serve)
Models:  llama3.1:8b (text), llava:13b (vision)
"""

import os
import json
import base64
import logging
import subprocess
import time
import threading
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_TEXT_MODEL = "llama3.1:8b"
DEFAULT_VISION_MODEL = "llava:13b"


class AIAssistant:
    """
    Local AI assistant that provides analysis and suggestions to the
    human operator. All results are displayed — never auto-executed.
    """

    def __init__(self, text_model=DEFAULT_TEXT_MODEL,
                 vision_model=DEFAULT_VISION_MODEL):
        self.text_model = text_model
        self.vision_model = vision_model
        self.logger = logging.getLogger("AIAssistant")
        logging.basicConfig(level=logging.INFO,
                            format="[TITAN-AI] %(levelname)s: %(message)s")
        self.ollama_url = OLLAMA_BASE_URL
        self._server_process = None

    # ========================================================================
    # Ollama Server Management
    # ========================================================================

    def check_ollama(self) -> bool:
        """Check if Ollama server is running and accessible."""
        if not HAS_HTTPX:
            self.logger.warning("httpx not installed — using fallback urllib")
            return self._check_ollama_urllib()

        try:
            resp = httpx.get(f"{self.ollama_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def _check_ollama_urllib(self) -> bool:
        """Fallback Ollama check using stdlib."""
        import urllib.request
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start_ollama(self) -> bool:
        """Start Ollama server if not already running."""
        if self.check_ollama():
            self.logger.info("Ollama server already running")
            return True

        self.logger.info("Starting Ollama server...")
        try:
            self._server_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)

            # Wait for server to become ready
            for _ in range(30):
                time.sleep(1)
                if self.check_ollama():
                    self.logger.info("Ollama server started successfully")
                    return True

            self.logger.error("Ollama server failed to start within 30s")
            return False
        except FileNotFoundError:
            self.logger.error(
                "Ollama binary not found. Install with: "
                "curl -fsSL https://ollama.ai/install.sh | sh")
            return False

    def ensure_model(self, model_name: str) -> bool:
        """Pull a model if not already available locally."""
        if not self.check_ollama():
            if not self.start_ollama():
                return False

        self.logger.info(f"Ensuring model '{model_name}' is available...")
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                self.logger.info(f"Model '{model_name}' ready")
                return True
            else:
                self.logger.error(f"Failed to pull model: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.logger.error(f"Model pull timed out for '{model_name}'")
            return False
        except FileNotFoundError:
            self.logger.error("Ollama binary not found")
            return False

    # ========================================================================
    # Core API Call
    # ========================================================================

    def _generate(self, model: str, prompt: str,
                  images: list = None,
                  system: str = None,
                  temperature: float = 0.3) -> Optional[str]:
        """
        Call Ollama generate API.
        Returns the response text or None on failure.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1024,
            },
        }

        if system:
            payload["system"] = system

        if images:
            payload["images"] = images  # Base64-encoded image list

        try:
            if HAS_HTTPX:
                resp = httpx.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=120)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
                else:
                    self.logger.error(f"Ollama API error: {resp.status_code}")
                    return None
            else:
                return self._generate_urllib(payload)
        except Exception as e:
            self.logger.error(f"Ollama API call failed: {e}")
            return None

    def _generate_urllib(self, payload: dict) -> Optional[str]:
        """Fallback generate using stdlib."""
        import urllib.request
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result.get("response", "")
        except Exception as e:
            self.logger.error(f"Urllib fallback failed: {e}")
            return None

    # ========================================================================
    # CAPTCHA Analysis (Vision — User manually solves)
    # ========================================================================

    def analyze_captcha(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Analyze a CAPTCHA screenshot using the local VLM.
        Returns a structured analysis that the USER reads and manually acts on.

        THIS DOES NOT SOLVE OR INTERACT WITH THE CAPTCHA AUTOMATICALLY.
        The user takes the screenshot, reads the analysis, and manually
        clicks/types the solution in the browser.

        Args:
            screenshot_path: Path to a screenshot of the CAPTCHA challenge.

        Returns:
            dict with 'challenge_type', 'description', 'suggested_solution',
            and 'confidence' keys.
        """
        if not os.path.exists(screenshot_path):
            return {"error": f"Screenshot not found: {screenshot_path}"}

        # Encode image as base64
        with open(screenshot_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        system_prompt = (
            "You are a visual analysis assistant. The user is looking at a "
            "CAPTCHA challenge on their screen and needs help understanding "
            "what is being asked. Analyze the image and describe:\n"
            "1. The type of CAPTCHA (image selection, text, puzzle, etc.)\n"
            "2. What the challenge is asking the user to do\n"
            "3. Your best analysis of the correct answer\n"
            "4. Your confidence level (low/medium/high)\n"
            "Respond in JSON format with keys: challenge_type, description, "
            "suggested_solution, confidence"
        )

        prompt = (
            "Analyze this CAPTCHA image. What type of challenge is it, "
            "what is it asking, and what appears to be the correct answer? "
            "The user will manually solve it based on your analysis."
        )

        response = self._generate(
            model=self.vision_model,
            prompt=prompt,
            images=[image_b64],
            system=system_prompt,
            temperature=0.2)

        if response is None:
            return {"error": "VLM analysis failed — is Ollama running?"}

        # Try to parse as JSON, fallback to raw text
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {
                "challenge_type": "unknown",
                "description": response,
                "suggested_solution": "See description above",
                "confidence": "low",
            }

        self.logger.info(
            f"CAPTCHA analysis complete: {result.get('challenge_type', 'unknown')}")
        return result

    # ========================================================================
    # Page Context Analysis (Text — User manually navigates)
    # ========================================================================

    def analyze_page_context(self, page_text: str,
                             user_goal: str) -> Dict[str, Any]:
        """
        Analyze page content and suggest navigation steps for the user.

        THIS DOES NOT NAVIGATE OR INTERACT WITH THE BROWSER.
        The user copies page text, reads the suggestions, and manually
        performs the actions.

        Args:
            page_text: Visible text content of the current page (user pastes).
            user_goal: What the user wants to accomplish on this page.

        Returns:
            dict with 'page_type', 'suggested_steps', 'warnings' keys.
        """
        system_prompt = (
            "You are a navigation assistant for a human user browsing the web. "
            "The user will give you the visible text of a web page and their "
            "goal. Suggest what elements they should look for and click on. "
            "Be specific about button text, link labels, or form fields. "
            "The user will MANUALLY perform all actions — you only advise. "
            "Respond in JSON format with keys: page_type, suggested_steps "
            "(list of strings), warnings (list of potential issues)."
        )

        prompt = (
            f"USER GOAL: {user_goal}\n\n"
            f"PAGE CONTENT:\n{page_text[:3000]}\n\n"
            f"What should the user look for and click on to achieve their goal?"
        )

        response = self._generate(
            model=self.text_model,
            prompt=prompt,
            system=system_prompt,
            temperature=0.3)

        if response is None:
            return {"error": "LLM analysis failed"}

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "page_type": "unknown",
                "suggested_steps": [response],
                "warnings": [],
            }

    # ========================================================================
    # Persona Behavior Advisor
    # ========================================================================

    def get_behavior_advice(self, persona_name: str,
                            site_name: str) -> Dict[str, Any]:
        """
        Generate persona-consistent behavior suggestions for the user.

        Advises the user on browsing patterns that match their persona
        (e.g., a "casual shopper" should browse reviews before buying,
        a "power user" should use keyboard shortcuts).

        Args:
            persona_name: The active persona profile name.
            site_name: The website being visited.

        Returns:
            dict with behavioral recommendations.
        """
        system_prompt = (
            "You are a behavioral consultant for digital identity management. "
            "Given a persona type and target website, suggest realistic "
            "browsing behaviors that a real person matching this persona "
            "would exhibit. Focus on: time spent on page, sections to visit, "
            "typical interaction patterns, and things to avoid. "
            "The user will MANUALLY follow these suggestions. "
            "Respond in JSON with keys: persona_summary, recommended_actions "
            "(list), time_guidance, things_to_avoid (list)."
        )

        prompt = (
            f"PERSONA: {persona_name}\n"
            f"WEBSITE: {site_name}\n\n"
            f"How should this persona naturally behave on this website? "
            f"What would a real person matching this profile do?"
        )

        response = self._generate(
            model=self.text_model,
            prompt=prompt,
            system=system_prompt,
            temperature=0.5)

        if response is None:
            return {"error": "LLM analysis failed"}

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "persona_summary": persona_name,
                "recommended_actions": [response],
                "time_guidance": "Browse naturally for 2-5 minutes",
                "things_to_avoid": ["Rushing through pages"],
            }

    # ========================================================================
    # Status
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return AI subsystem status for console display."""
        ollama_running = self.check_ollama()

        status = {
            "ollama_running": ollama_running,
            "text_model": self.text_model,
            "vision_model": self.vision_model,
            "models_available": [],
        }

        if ollama_running:
            try:
                if HAS_HTTPX:
                    resp = httpx.get(f"{self.ollama_url}/api/tags", timeout=5)
                    if resp.status_code == 200:
                        models = resp.json().get("models", [])
                        status["models_available"] = [
                            m.get("name", "") for m in models]
                else:
                    import urllib.request
                    req = urllib.request.Request(
                        f"{self.ollama_url}/api/tags")
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        status["models_available"] = [
                            m.get("name", "") for m in data.get("models", [])]
            except Exception:
                pass

        return status


if __name__ == "__main__":
    assistant = AIAssistant()
    status = assistant.get_status()
    print(json.dumps(status, indent=2))

    if not status["ollama_running"]:
        print("\nOllama is not running. Start with: ollama serve")
        print("Then pull models:")
        print(f"  ollama pull {DEFAULT_TEXT_MODEL}")
        print(f"  ollama pull {DEFAULT_VISION_MODEL}")
