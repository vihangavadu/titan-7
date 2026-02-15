#!/usr/bin/env python3
"""
Cerberus AI Analyst
Local AI analysis for financial intelligence using Ollama

Provides offline BIN analysis and risk assessment without cloud exposure
OPSEC: Fully local processing, no data leakage

Author: Dva.12
"""

import asyncio
import aiohttp
import json
import logging
import subprocess
import time
from typing import Dict, List, Optional
from datetime import datetime

from . import CardAsset

logger = logging.getLogger('cerberus.ai_analyst')

class AIAnalyst:
    """
    Local AI analyst using Ollama for financial intelligence
    
    Features:
    - BIN pattern analysis and risk assessment
    - Transaction limit recommendations
    - Fraud pattern detection
    - Historical success rate prediction
    """
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model_name = "mistral:7b-instruct-v0.2-q4_0"  # Quantized model
        self.session = None
        self.ollama_process = None
        self.model_loaded = False
        
        # AI analysis prompts
        self.system_prompt = """You are a financial risk analyst specializing in payment card intelligence. 
Analyze the provided BIN data and validation results to assess risk and recommend transaction limits.

Key factors to consider:
- Card tier (Standard, Gold, Platinum, Infinite)
- Issuing bank risk profile
- Geographic risk factors
- Historical success patterns
- AVS/CVV verification results

Respond with JSON format:
{
    "risk_level": "low|medium|high|critical",
    "confidence_score": 0.0-1.0,
    "recommended_limit": 0.0,
    "risk_factors": ["factor1", "factor2"],
    "analysis_summary": "Brief explanation"
}"""
        
    async def initialize(self):
        """Initialize Ollama server and load model"""
        await self._start_ollama()
        await self._wait_for_ollama()
        await self._load_model()
        await self._setup_session()
        
    async def _start_ollama(self):
        """Start Ollama server in background"""
        try:
            # Check if Ollama is already running
            response = await aiohttp.ClientSession().get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status == 200:
                logger.info("Ollama already running")
                return
        except Exception:
            pass
            
        # Start Ollama server
        logger.info("Starting Ollama server...")
        try:
            self.ollama_process = await asyncio.create_subprocess_exec(
                'ollama', 'serve',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info("Ollama server started")
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            raise
            
    async def _wait_for_ollama(self, timeout: int = 60):
        """Wait for Ollama server to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.ollama_url}/api/tags", timeout=5) as response:
                        if response.status == 200:
                            logger.info("Ollama server is ready")
                            return
            except Exception:
                pass
                
            await asyncio.sleep(2)
            
        raise TimeoutError("Ollama server failed to start within timeout")
        
    async def _load_model(self):
        """Load and verify AI model"""
        try:
            # Check if model is available
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get('models', [])
                        
                        for model in models:
                            if self.model_name in model.get('name', ''):
                                logger.info(f"Model {self.model_name} is available")
                                self.model_loaded = True
                                return
                                
            # Pull model if not available
            logger.info(f"Pulling model {self.model_name}...")
            pull_payload = {"name": self.model_name}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.ollama_url}/api/pull", json=pull_payload, timeout=300) as response:
                    if response.status == 200:
                        logger.info("Model pulled successfully")
                        self.model_loaded = True
                    else:
                        raise Exception(f"Failed to pull model: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Fallback to smaller model
            await self._load_fallback_model()
            
    async def _load_fallback_model(self):
        """Load fallback smaller model"""
        fallback_model = "phi:2.7b-chat-v2.2-q4_0"
        logger.info(f"Loading fallback model: {fallback_model}")
        
        try:
            pull_payload = {"name": fallback_model}
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.ollama_url}/api/pull", json=pull_payload, timeout=300) as response:
                    if response.status == 200:
                        self.model_name = fallback_model
                        self.model_loaded = True
                        logger.info("Fallback model loaded successfully")
                    else:
                        raise Exception("Failed to load fallback model")
        except Exception as e:
            logger.error(f"Failed to load fallback model: {e}")
            raise
            
    async def _setup_session(self):
        """Setup HTTP session for Ollama API"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120),
            headers={"Content-Type": "application/json"}
        )
        
    async def analyze_card(self, card: CardAsset, bin_info: Dict, api_result: Dict) -> Dict:
        """
        Analyze card using local AI
        
        Args:
            card: Card asset data
            bin_info: BIN database information
            api_result: API validation results
            
        Returns:
            Dict with AI analysis results
        """
        if not self.model_loaded:
            logger.warning("AI model not loaded, using fallback analysis")
            return await self._fallback_analysis(card, bin_info, api_result)
            
        # Prepare analysis context
        context = self._prepare_analysis_context(card, bin_info, api_result)
        
        # Generate AI analysis
        try:
            analysis = await self._query_ai(context)
            return analysis
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return await self._fallback_analysis(card, bin_info, api_result)
            
    def _prepare_analysis_context(self, card: CardAsset, bin_info: Dict, api_result: Dict) -> str:
        """Prepare context for AI analysis"""
        context = f"""
CARD ANALYSIS REQUEST:
=====================

BIN Information:
- BIN: {card.number[:6]}
- Brand: {bin_info.get('brand', 'Unknown')}
- Type: {bin_info.get('type', 'Unknown')}
- Category: {bin_info.get('category', 'Unknown')}
- Bank: {bin_info.get('bank', 'Unknown')}
- Country: {bin_info.get('country', 'Unknown')}
- Tier: {bin_info.get('tier', 'Standard')}

Validation Results:
- Card Live: {api_result.get('card_live', False)}
- AVS Check: {api_result.get('avs_check', 'Unknown')}
- CVV Check: {api_result.get('cvv_check', 'Unknown')}

Card Details:
- Expiration: {card.exp_month}/{card.exp_year}
- Cardholder Name: {card.name}
- Country: {card.address_country}

ANALYSIS REQUIREMENTS:
Assess the risk level and recommend a safe transaction limit based on:
1. Card tier and issuing bank reputation
2. Geographic and fraud risk factors
3. Verification success (AVS/CVV)
4. Historical patterns for similar BINs

Provide specific, actionable recommendations.
"""
        return context
        
    async def _query_ai(self, context: str) -> Dict:
        """Query Ollama AI model"""
        payload = {
            "model": self.model_name,
            "prompt": f"{self.system_prompt}\n\n{context}",
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 500
            }
        }
        
        async with self.session.post(f"{self.ollama_url}/api/generate", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                ai_response = data.get('response', '')
                
                # Parse JSON response
                try:
                    # Extract JSON from response
                    json_start = ai_response.find('{')
                    json_end = ai_response.rfind('}') + 1
                    
                    if json_start != -1 and json_end != -1:
                        json_str = ai_response[json_start:json_end]
                        analysis = json.loads(json_str)
                        
                        # Validate required fields
                        required_fields = ['risk_level', 'confidence_score', 'recommended_limit']
                        for field in required_fields:
                            if field not in analysis:
                                analysis[field] = None
                                
                        return analysis
                    else:
                        logger.warning("Could not extract JSON from AI response")
                        return await self._parse_text_response(ai_response)
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse AI JSON response: {e}")
                    return await self._parse_text_response(ai_response)
            else:
                raise Exception(f"AI query failed: {response.status}")
                
    async def _parse_text_response(self, response: str) -> Dict:
        """Parse non-JSON AI response"""
        # Simple text parsing fallback
        risk_level = "medium"
        confidence_score = 0.5
        recommended_limit = 100.0
        
        response_lower = response.lower()
        
        if "low risk" in response_lower or "safe" in response_lower:
            risk_level = "low"
            confidence_score = 0.8
            recommended_limit = 500.0
        elif "high risk" in response_lower or "dangerous" in response_lower:
            risk_level = "high"
            confidence_score = 0.3
            recommended_limit = 25.0
        elif "critical" in response_lower or "avoid" in response_lower:
            risk_level = "critical"
            confidence_score = 0.9
            recommended_limit = 0.0
            
        return {
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "recommended_limit": recommended_limit,
            "risk_factors": ["text_parse_fallback"],
            "analysis_summary": response[:200] + "..." if len(response) > 200 else response
        }
        
    async def _fallback_analysis(self, card: CardAsset, bin_info: Dict, api_result: Dict) -> Dict:
        """Fallback analysis without AI"""
        risk_score = 0
        risk_factors = []
        
        # BIN-based risk assessment
        tier = bin_info.get('tier', 'Standard')
        if tier == 'Standard':
            risk_score += 20
        elif tier == 'Gold':
            risk_score += 15
        elif tier == 'Platinum':
            risk_score += 10
        elif tier == 'Infinite':
            risk_score += 5
        else:
            risk_score += 25
            risk_factors.append("unknown_tier")
            
        # Verification-based assessment
        if api_result.get('card_live'):
            risk_score -= 10
        else:
            risk_score += 30
            risk_factors.append("card_not_live")
            
        if api_result.get('avs_check') == 'pass':
            risk_score -= 5
        elif api_result.get('avs_check') == 'fail':
            risk_score += 15
            risk_factors.append("avs_failed")
            
        if api_result.get('cvv_check') == 'pass':
            risk_score -= 5
        elif api_result.get('cvv_check') == 'fail':
            risk_score += 20
            risk_factors.append("cvv_failed")
            
        # Determine risk level
        if risk_score <= 10:
            risk_level = "low"
            recommended_limit = 1000.0
        elif risk_score <= 25:
            risk_level = "medium"
            recommended_limit = 250.0
        elif risk_score <= 40:
            risk_level = "high"
            recommended_limit = 50.0
        else:
            risk_level = "critical"
            recommended_limit = 0.0
            
        return {
            "risk_level": risk_level,
            "confidence_score": 0.6,
            "recommended_limit": recommended_limit,
            "risk_factors": risk_factors,
            "analysis_summary": f"Fallback analysis based on risk score {risk_score}"
        }
        
    async def get_bin_insights(self, bin_number: str) -> Dict:
        """Get detailed BIN insights from AI"""
        if not self.model_loaded:
            return {"error": "AI model not available"}
            
        context = f"""
Provide detailed insights for BIN {bin_number}:
- Typical cardholder profile
- Common usage patterns
- Fraud risk factors
- Geographic considerations
- Recommended verification methods
"""
        
        try:
            payload = {
                "model": self.model_name,
                "prompt": context,
                "stream": False,
                "options": {"temperature": 0.3, "max_tokens": 300}
            }
            
            async with self.session.post(f"{self.ollama_url}/api/generate", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"insights": data.get('response', '')}
                else:
                    return {"error": "AI query failed"}
        except Exception as e:
            return {"error": str(e)}
            
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            
        if self.ollama_process:
            try:
                self.ollama_process.terminate()
                await self.ollama_process.wait()
            except Exception:
                pass
