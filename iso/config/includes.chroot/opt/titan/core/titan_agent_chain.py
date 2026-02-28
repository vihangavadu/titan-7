"""
TITAN V7.6 SINGULARITY — Agentic LLM Orchestration (LangChain)
Makes the cognitive core agentic with tool-calling chains.

Provides:
1. Tool Registry       — Register Titan modules as callable tools
2. Agent Executor      — LangChain ReAct agent with Ollama backend
3. Operation Planner   — Multi-step reasoning for complex operations
4. Memory Integration  — ChromaDB vector memory as retrieval tool
5. Web Search Tool     — SerpAPI integration for real-time intel

Architecture:
    - LangChain agent with Ollama (local) or cloud LLM backend
    - ReAct-style reasoning: Thought → Action → Observation → loop
    - Tools registered from existing Titan modules
    - Vector memory provides long-term context
    - Falls back to direct Ollama calls if LangChain unavailable
"""

import json
import time
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

__version__ = "8.0.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-AGENT")

# ═══════════════════════════════════════════════════════════════════════════════
# LANGCHAIN INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

_LANGCHAIN_AVAILABLE = False
_LANGCHAIN_COMMUNITY_AVAILABLE = False

try:
    from langchain_core.tools import Tool as LCTool
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.output_parsers import StrOutputParser
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not installed. Install with: pip install langchain langchain-core")

try:
    from langchain_community.llms import Ollama as LCOllama
    from langchain_community.chat_models import ChatOllama
    _LANGCHAIN_COMMUNITY_AVAILABLE = True
except ImportError:
    try:
        from langchain_ollama import ChatOllama
        _LANGCHAIN_COMMUNITY_AVAILABLE = True
    except ImportError:
        logger.warning("LangChain Ollama not available. Install: pip install langchain-ollama")


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TitanTool:
    """A tool that the agent can call."""
    name: str
    description: str
    func: Callable
    category: str = "general"  # analysis, recon, risk, memory, search
    requires_args: bool = True


class TitanToolRegistry:
    """
    Registry of tools available to the Titan agent.

    Tools are registered from existing Titan modules and exposed
    to the LangChain agent for autonomous decision-making.
    """

    def __init__(self):
        self._tools: Dict[str, TitanTool] = {}
        self._lock = threading.Lock()
        self._register_builtin_tools()

    def register(self, name: str, description: str, func: Callable,
                 category: str = "general") -> None:
        """Register a tool."""
        with self._lock:
            self._tools[name] = TitanTool(
                name=name, description=description,
                func=func, category=category,
            )
        logger.info(f"Registered tool: {name} [{category}]")

    def get(self, name: str) -> Optional[TitanTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: str = None) -> List[TitanTool]:
        """List all tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def to_langchain_tools(self) -> list:
        """Convert registered tools to LangChain Tool objects."""
        if not _LANGCHAIN_AVAILABLE:
            return []

        lc_tools = []
        for tool in self._tools.values():
            lc_tools.append(LCTool(
                name=tool.name,
                description=tool.description,
                func=tool.func,
            ))
        return lc_tools

    def _register_builtin_tools(self):
        """Register built-in tools from Titan modules."""

        # --- BIN Analysis Tool ---
        def analyze_bin_tool(input_str: str) -> str:
            """Analyze a BIN number for risk and strategy."""
            try:
                from ai_intelligence_engine import analyze_bin
                parts = input_str.strip().split()
                bin_num = parts[0] if parts else input_str.strip()
                target = parts[1] if len(parts) > 1 else ""
                amount = float(parts[2]) if len(parts) > 2 else 0
                result = analyze_bin(bin_num, target, amount)
                return (
                    f"BIN {result.bin_number}: {result.bank_name} "
                    f"({result.network} {result.card_type} {result.card_level}) | "
                    f"Country: {result.country} | Risk: {result.risk_level.value} | "
                    f"AI Score: {result.ai_score} | "
                    f"Success: {result.success_prediction:.0%} | "
                    f"Best targets: {result.best_targets} | "
                    f"Notes: {result.strategic_notes}"
                )
            except Exception as e:
                return f"BIN analysis error: {e}"

        self.register("analyze_bin",
                       "Analyze a credit card BIN number. Input: 'BIN_NUMBER [TARGET] [AMOUNT]'. "
                       "Returns bank, card type, risk level, success prediction, and strategy.",
                       analyze_bin_tool, category="analysis")

        # --- Target Recon Tool ---
        def recon_target_tool(input_str: str) -> str:
            """Reconnaissance on a merchant target."""
            try:
                from ai_intelligence_engine import recon_target
                domain = input_str.strip().split()[0]
                result = recon_target(domain)
                return (
                    f"Target: {result.domain} ({result.name}) | "
                    f"Fraud engine: {result.fraud_engine_guess} | "
                    f"PSP: {result.payment_processor_guess} | "
                    f"Friction: {result.estimated_friction} | "
                    f"3DS rate: {result.three_ds_probability:.0%} | "
                    f"Best cards: {result.optimal_card_types} | "
                    f"Warmup: {result.warmup_strategy} | "
                    f"Tips: {result.checkout_tips}"
                )
            except Exception as e:
                return f"Target recon error: {e}"

        self.register("recon_target",
                       "Reconnaissance on a merchant website. Input: 'DOMAIN'. "
                       "Returns fraud engine, payment processor, 3DS rate, and checkout tips.",
                       recon_target_tool, category="recon")

        # --- Risk Assessment Tool ---
        def assess_risk_tool(input_str: str) -> str:
            """Assess transaction risk."""
            try:
                from ai_intelligence_engine import plan_operation
                parts = input_str.strip().split()
                bin_num = parts[0] if parts else ""
                target = parts[1] if len(parts) > 1 else ""
                amount = float(parts[2]) if len(parts) > 2 else 100
                plan = plan_operation(bin_num, target, amount)
                return plan.executive_summary
            except Exception as e:
                return f"Risk assessment error: {e}"

        self.register("assess_risk",
                       "Full risk assessment for an operation. Input: 'BIN TARGET AMOUNT'. "
                       "Returns GO/NO-GO decision with score and strategy.",
                       assess_risk_tool, category="risk")

        # --- Vector Memory Search Tool ---
        def search_memory_tool(input_str: str) -> str:
            """Search vector memory for relevant past data."""
            try:
                from titan_vector_memory import get_vector_memory
                mem = get_vector_memory()
                if not mem.is_available:
                    return "Vector memory unavailable"

                results = mem.search_knowledge(input_str, n=3)
                if not results:
                    # Try operations
                    results = mem.recall_similar_operations(input_str, n=3)
                if not results:
                    return "No relevant memories found"

                output = []
                for r in results:
                    output.append(f"[{r.score:.0%}] {r.content}")
                return "\n".join(output)
            except Exception as e:
                return f"Memory search error: {e}"

        self.register("search_memory",
                       "Search Titan's vector memory for past operations, targets, BINs, "
                       "and threat intel. Input: natural language query.",
                       search_memory_tool, category="memory")

        # --- Web Search Tool ---
        def web_search_tool(input_str: str) -> str:
            """Search the web for real-time intelligence."""
            try:
                from titan_web_intel import get_web_intel
                intel = get_web_intel()
                if not intel.is_available:
                    return "Web search unavailable (no API key configured)"
                results = intel.search(input_str, num_results=3)
                if not results:
                    return "No web results found"
                output = []
                for r in results:
                    output.append(f"[{r.get('source', '?')}] {r.get('title', '')} — {r.get('snippet', '')}")
                return "\n".join(output)
            except Exception as e:
                return f"Web search error: {e}"

        self.register("web_search",
                       "Search the web for real-time information about merchants, "
                       "antifraud systems, payment processors, or security news. "
                       "Input: search query.",
                       web_search_tool, category="search")

        # --- Decline Pattern Tool ---
        def decline_pattern_tool(input_str: str) -> str:
            """Check decline patterns for a BIN."""
            try:
                from ai_intelligence_engine import get_bin_decline_pattern
                bin_num = input_str.strip().split()[0]
                pattern = get_bin_decline_pattern(bin_num)
                return json.dumps(pattern, indent=2)
            except Exception as e:
                return f"Decline pattern error: {e}"

        self.register("check_declines",
                       "Check decline history and patterns for a BIN. Input: 'BIN_NUMBER'. "
                       "Returns decline count, pattern type, and recommendation.",
                       decline_pattern_tool, category="analysis")

        # --- Antifraud Detection Tool ---
        def detect_antifraud_tool(input_str: str) -> str:
            """Detect antifraud systems on a page."""
            try:
                from cognitive_core import AntifraudPatternRecognizer
                recognizer = AntifraudPatternRecognizer()
                result = recognizer.analyze_page(input_str)
                vendors = [v["vendor"] for v in result.get("vendors_detected", [])]
                return (
                    f"Detected: {vendors or 'none'} | "
                    f"Threat level: {result.get('threat_level', 'unknown')} | "
                    f"Strategy: {json.dumps(result.get('evasion_strategy', {}))}"
                )
            except Exception as e:
                return f"Antifraud detection error: {e}"

        self.register("detect_antifraud",
                       "Detect antifraud systems in page HTML. Input: HTML content. "
                       "Returns detected vendors, threat level, and evasion strategy.",
                       detect_antifraud_tool, category="analysis")


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

# ReAct prompt template for Titan agent
TITAN_AGENT_SYSTEM_PROMPT = """You are TITAN's autonomous intelligence agent. You have access to tools for analyzing payment operations, reconnaissance, risk assessment, and memory search.

Your goal is to provide actionable intelligence for operations. You think step-by-step:
1. Understand the request
2. Use tools to gather information
3. Synthesize findings into a clear recommendation

IMPORTANT RULES:
- Always check vector memory first for relevant past data
- Use multiple tools when needed for comprehensive analysis
- Provide specific, actionable recommendations
- Include confidence levels in your assessments
- Flag any critical risks immediately

Available tools: {tool_names}

Use this format:
Thought: [your reasoning about what to do next]
Action: [tool name]
Action Input: [input to the tool]
Observation: [tool output]
... (repeat Thought/Action/Observation as needed)
Thought: I have enough information to answer
Final Answer: [your comprehensive response]"""


class TitanAgent:
    """
    LangChain-powered autonomous agent for Titan OS.

    Uses ReAct reasoning pattern with registered tools to
    autonomously gather intelligence and make recommendations.

    Usage:
        agent = get_titan_agent()

        # Ask the agent to analyze an operation
        result = agent.run(
            "Analyze BIN 411111 for a $299 purchase on amazon.com. "
            "Check if we've tried this before and what the risks are."
        )

        # The agent will autonomously:
        # 1. Search vector memory for past operations
        # 2. Analyze the BIN
        # 3. Recon the target
        # 4. Assess overall risk
        # 5. Provide a comprehensive recommendation
    """

    def __init__(self, model: str = None, base_url: str = None,
                 temperature: float = 0.3, max_iterations: int = 6):
        import os
        self._model = model or os.getenv("OLLAMA_MODEL", "mistral:7b-instruct-v0.2-q4_0")
        self._base_url = base_url or os.getenv("OLLAMA_API", "http://127.0.0.1:11434")
        self._temperature = temperature
        self._max_iterations = max_iterations
        self._tool_registry = TitanToolRegistry()
        self._agent_executor = None
        self._llm = None
        self._initialized = False
        self._lock = threading.Lock()

        self._init_agent()

    def _init_agent(self):
        """Initialize the LangChain agent."""
        if not _LANGCHAIN_AVAILABLE or not _LANGCHAIN_COMMUNITY_AVAILABLE:
            logger.warning("LangChain not fully available — agent will use fallback mode")
            return

        try:
            # Initialize Ollama LLM via LangChain
            self._llm = ChatOllama(
                model=self._model,
                base_url=self._base_url,
                temperature=self._temperature,
            )

            # Get tools
            lc_tools = self._tool_registry.to_langchain_tools()
            if not lc_tools:
                logger.warning("No tools registered — agent has no capabilities")
                return

            tool_names = ", ".join([t.name for t in lc_tools])

            # Build ReAct prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", TITAN_AGENT_SYSTEM_PROMPT.format(tool_names=tool_names)),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            # Create ReAct agent
            agent = create_react_agent(self._llm, lc_tools, prompt)

            self._agent_executor = AgentExecutor(
                agent=agent,
                tools=lc_tools,
                verbose=True,
                max_iterations=self._max_iterations,
                handle_parsing_errors=True,
                return_intermediate_steps=True,
            )

            self._initialized = True
            logger.info(f"Titan Agent initialized with {len(lc_tools)} tools "
                        f"(model={self._model})")

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            self._initialized = False

    @property
    def is_available(self) -> bool:
        return self._initialized and self._agent_executor is not None

    def register_tool(self, name: str, description: str,
                      func: Callable, category: str = "general") -> None:
        """Register an additional tool and reinitialize agent."""
        self._tool_registry.register(name, description, func, category)
        # Reinitialize to pick up new tool
        self._init_agent()

    def run(self, query: str, chat_history: list = None) -> Dict[str, Any]:
        """
        Run the agent on a query.

        Args:
            query: Natural language query/instruction
            chat_history: Optional conversation history

        Returns:
            Dict with 'output', 'steps', 'success', 'latency_ms'
        """
        t0 = time.time()

        if not self.is_available:
            # Fallback: direct tool execution without agent reasoning
            return self._fallback_run(query)

        try:
            with self._lock:
                result = self._agent_executor.invoke({
                    "input": query,
                    "chat_history": chat_history or [],
                })

            elapsed = (time.time() - t0) * 1000

            # Extract intermediate steps
            steps = []
            for step in result.get("intermediate_steps", []):
                action, observation = step
                steps.append({
                    "tool": action.tool,
                    "input": action.tool_input,
                    "output": str(observation)[:500],
                })

            return {
                "output": result.get("output", ""),
                "steps": steps,
                "success": True,
                "latency_ms": round(elapsed, 2),
                "model": self._model,
                "tools_used": [s["tool"] for s in steps],
            }

        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            logger.error(f"Agent execution failed: {e}")
            return {
                "output": f"Agent error: {e}",
                "steps": [],
                "success": False,
                "latency_ms": round(elapsed, 2),
                "model": self._model,
                "tools_used": [],
            }

    def _fallback_run(self, query: str) -> Dict[str, Any]:
        """
        Fallback execution when LangChain is unavailable.
        Runs tools directly based on keyword matching.
        """
        t0 = time.time()
        query_lower = query.lower()
        results = []
        tools_used = []

        # Keyword-based tool dispatch
        if any(kw in query_lower for kw in ["bin", "card", "411", "511", "371"]):
            # Extract BIN-like numbers
            import re
            bins = re.findall(r'\b\d{6,8}\b', query)
            if bins:
                tool = self._tool_registry.get("analyze_bin")
                if tool:
                    result = tool.func(bins[0])
                    results.append(f"BIN Analysis: {result}")
                    tools_used.append("analyze_bin")

        if any(kw in query_lower for kw in ["target", "merchant", ".com", ".net", "site"]):
            import re
            domains = re.findall(r'[\w-]+\.(?:com|net|org|co\.uk|io)', query)
            if domains:
                tool = self._tool_registry.get("recon_target")
                if tool:
                    result = tool.func(domains[0])
                    results.append(f"Target Recon: {result}")
                    tools_used.append("recon_target")

        if any(kw in query_lower for kw in ["risk", "assess", "plan", "operation"]):
            tool = self._tool_registry.get("assess_risk")
            if tool:
                # Try to extract BIN + target + amount
                import re
                bins = re.findall(r'\b\d{6,8}\b', query)
                domains = re.findall(r'[\w-]+\.(?:com|net|org|co\.uk|io)', query)
                amounts = re.findall(r'\$?([\d.]+)', query)
                input_str = f"{bins[0] if bins else '411111'} {domains[0] if domains else ''} {amounts[-1] if amounts else '100'}"
                result = tool.func(input_str)
                results.append(f"Risk Assessment: {result}")
                tools_used.append("assess_risk")

        if any(kw in query_lower for kw in ["remember", "memory", "past", "history", "similar"]):
            tool = self._tool_registry.get("search_memory")
            if tool:
                result = tool.func(query)
                results.append(f"Memory: {result}")
                tools_used.append("search_memory")

        if any(kw in query_lower for kw in ["search", "web", "news", "latest", "current"]):
            tool = self._tool_registry.get("web_search")
            if tool:
                result = tool.func(query)
                results.append(f"Web Intel: {result}")
                tools_used.append("web_search")

        elapsed = (time.time() - t0) * 1000

        if not results:
            # Last resort: try memory search
            tool = self._tool_registry.get("search_memory")
            if tool:
                result = tool.func(query)
                results.append(f"Memory: {result}")
                tools_used.append("search_memory")

        output = "\n\n".join(results) if results else "No relevant tools matched your query. Try being more specific."

        return {
            "output": output,
            "steps": [{"tool": t, "input": query, "output": "fallback"} for t in tools_used],
            "success": bool(results),
            "latency_ms": round(elapsed, 2),
            "model": "fallback_keyword_dispatch",
            "tools_used": tools_used,
            "fallback_mode": True,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # SPECIALIZED CHAINS
    # ═══════════════════════════════════════════════════════════════════════

    def plan_operation(self, bin_number: str, target: str,
                       amount: float) -> Dict[str, Any]:
        """
        Run a full operation planning chain.
        The agent autonomously gathers all needed intelligence.
        """
        query = (
            f"Plan a complete operation for BIN {bin_number} on {target} "
            f"for ${amount:.2f}. Steps:\n"
            f"1. Search memory for past operations with this BIN and target\n"
            f"2. Analyze the BIN for risk and card properties\n"
            f"3. Recon the target for antifraud and payment processor\n"
            f"4. Check decline patterns for this BIN\n"
            f"5. Provide a GO/NO-GO decision with detailed strategy"
        )
        return self.run(query)

    def investigate_decline(self, bin_number: str, target: str,
                            decline_code: str) -> Dict[str, Any]:
        """
        Investigate a decline and recommend next steps.
        """
        query = (
            f"Investigate decline: BIN {bin_number} was declined on {target} "
            f"with code '{decline_code}'. Steps:\n"
            f"1. Check decline patterns for this BIN\n"
            f"2. Search memory for similar declines\n"
            f"3. Recon the target for its antifraud system\n"
            f"4. Search web for any recent changes to {target}'s fraud detection\n"
            f"5. Recommend whether to retry, switch target, or abandon this BIN"
        )
        return self.run(query)

    def threat_briefing(self, target: str = None) -> Dict[str, Any]:
        """
        Generate a threat briefing for a target or general landscape.
        """
        if target:
            query = (
                f"Generate a threat briefing for {target}:\n"
                f"1. Recon the target\n"
                f"2. Search web for latest antifraud news about {target}\n"
                f"3. Search memory for past operations on {target}\n"
                f"4. Provide threat level, recommended approach, and timing"
            )
        else:
            query = (
                "Generate a general threat landscape briefing:\n"
                "1. Search web for latest antifraud and payment security news\n"
                "2. Search memory for recent decline patterns\n"
                "3. Identify trending threats and recommended countermeasures"
            )
        return self.run(query)

    def get_status(self) -> Dict:
        """Get agent status."""
        return {
            "available": self.is_available,
            "langchain_available": _LANGCHAIN_AVAILABLE,
            "langchain_community_available": _LANGCHAIN_COMMUNITY_AVAILABLE,
            "model": self._model,
            "base_url": self._base_url,
            "tools_count": len(self._tool_registry.list_tools()),
            "tools": [t.name for t in self._tool_registry.list_tools()],
            "max_iterations": self._max_iterations,
            "fallback_mode": not self.is_available,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE CHAIN — For non-agentic sequential tool execution
# ═══════════════════════════════════════════════════════════════════════════════

class TitanChain:
    """
    Simple sequential chain for predictable multi-step operations.
    Unlike the agent, this runs tools in a fixed order without
    autonomous reasoning. Faster and more predictable.

    Usage:
        chain = TitanChain()
        chain.add_step("analyze_bin", "411111 amazon.com 299")
        chain.add_step("recon_target", "amazon.com")
        chain.add_step("search_memory", "BIN 411111 amazon decline")
        result = chain.execute()
    """

    def __init__(self):
        self._steps: List[Tuple[str, str]] = []
        self._registry = TitanToolRegistry()

    def add_step(self, tool_name: str, input_str: str) -> 'TitanChain':
        """Add a step to the chain. Returns self for chaining."""
        self._steps.append((tool_name, input_str))
        return self

    def execute(self) -> Dict[str, Any]:
        """Execute all steps sequentially."""
        t0 = time.time()
        results = []
        errors = []

        for tool_name, input_str in self._steps:
            tool = self._registry.get(tool_name)
            if tool is None:
                errors.append(f"Tool not found: {tool_name}")
                continue

            try:
                step_t0 = time.time()
                output = tool.func(input_str)
                step_ms = (time.time() - step_t0) * 1000
                results.append({
                    "tool": tool_name,
                    "input": input_str,
                    "output": output,
                    "latency_ms": round(step_ms, 2),
                    "success": True,
                })
            except Exception as e:
                results.append({
                    "tool": tool_name,
                    "input": input_str,
                    "output": str(e),
                    "latency_ms": 0,
                    "success": False,
                })
                errors.append(f"{tool_name}: {e}")

        elapsed = (time.time() - t0) * 1000
        return {
            "steps": results,
            "total_steps": len(self._steps),
            "successful_steps": sum(1 for r in results if r["success"]),
            "errors": errors,
            "latency_ms": round(elapsed, 2),
        }

    def clear(self) -> 'TitanChain':
        """Clear all steps."""
        self._steps.clear()
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_titan_agent: Optional[TitanAgent] = None
_agent_lock = threading.Lock()


def get_titan_agent(model: str = None, base_url: str = None) -> TitanAgent:
    """Get singleton TitanAgent instance."""
    global _titan_agent
    with _agent_lock:
        if _titan_agent is None:
            _titan_agent = TitanAgent(model=model, base_url=base_url)
    return _titan_agent


def get_tool_registry() -> TitanToolRegistry:
    """Get the tool registry from the singleton agent."""
    agent = get_titan_agent()
    return agent._tool_registry


def is_agent_available() -> bool:
    """Check if the agent is operational."""
    try:
        agent = get_titan_agent()
        return agent.is_available
    except Exception:
        return False
