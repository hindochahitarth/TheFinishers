"""
GreenPulse AI Agent — LangGraph-based Environmental Intelligence Agent
Multi-step reasoning with tool-calling for environmental analysis.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, TypedDict, Annotated

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State tracked through agent execution."""
    messages: List[Dict[str, Any]]
    query: str
    session_id: str
    location_id: int
    context: Dict[str, Any]
    tools_used: List[str]
    reasoning_trace: List[Dict[str, Any]]
    final_response: Optional[str]


class GreenPulseAgent:
    """
    LangGraph-based intelligent environmental agent.
    
    Capabilities:
    - Multi-step reasoning with tool use
    - Root cause analysis
    - Regulatory compliance checking
    - Health risk assessment
    - Forecast interpretation
    - Natural language responses
    """
    
    def __init__(
        self,
        llm_provider: str = "openai",
        llm_api_key: str = "",
        llm_model: str = "gpt-4o",
        temperature: float = 0.1,
    ):
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.temperature = temperature
        
        self.agent = None
        self.tools = []
        self.is_initialized = False
        
        self._initialize()
    
    def _initialize(self):
        """Initialize the LangGraph agent if LLM API key is available."""
        if not self.llm_api_key or self.llm_api_key.startswith("your_"):
            logger.info("LLM API key not configured. Using rule-based fallback.")
            return
        
        try:
            self._build_langgraph_agent()
            self.is_initialized = True
            logger.info(f"GreenPulse Agent initialized with {self.llm_model}")
        except ImportError as e:
            logger.warning(f"LangGraph/LangChain not available: {e}")
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
    
    def _build_langgraph_agent(self):
        """Build the LangGraph ReAct agent."""
        from langchain_openai import ChatOpenAI
        from langchain_anthropic import ChatAnthropic
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langgraph.prebuilt import create_react_agent
        from ai_agents.tools import create_langchain_tools
        
        # Select LLM based on provider
        if self.llm_provider == "openai":
            llm = ChatOpenAI(
                model=self.llm_model,
                api_key=self.llm_api_key,
                temperature=self.temperature,
            )
        elif self.llm_provider == "anthropic":
            llm = ChatAnthropic(
                model=self.llm_model or "claude-3-sonnet-20240229",
                api_key=self.llm_api_key,
                temperature=self.temperature,
            )
        elif self.llm_provider == "google":
            llm = ChatGoogleGenerativeAI(
                model=self.llm_model or "gemini-1.5-pro",
                google_api_key=self.llm_api_key,
                temperature=self.temperature,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
        
        # Get tools
        self.tools = create_langchain_tools()
        
        # System prompt for environmental expertise
        system_prompt = """You are GreenPulse AI, an expert environmental intelligence assistant.

Your expertise includes:
- Air quality monitoring and AQI interpretation
- Pollutant source analysis and root cause reasoning
- WHO, CPCB, and EPA regulatory compliance
- Health risk assessment based on pollution levels
- Weather-pollution interactions
- Traffic-emission relationships
- Environmental forecasting interpretation

When answering questions:
1. Always use available tools to get real-time data when relevant
2. Provide data-driven, scientifically accurate responses
3. Explain your reasoning clearly
4. Include specific numbers and measurements when available
5. Give actionable recommendations
6. Warn about health risks when pollution is elevated

Format your responses with clear structure:
- Use bullet points for lists
- Bold key metrics and conclusions
- Include units for all measurements
- Cite the standards you're comparing against (WHO, CPCB, etc.)

Current monitoring location: New Delhi, India
"""
        
        # Create the ReAct agent
        self.agent = create_react_agent(
            llm,
            self.tools,
            messages_modifier=system_prompt,
        )
    
    async def query(
        self,
        query: str,
        session_id: Optional[str] = None,
        location_id: int = 1,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a natural language query.
        
        Args:
            query: User's question or request
            session_id: Conversation session ID
            location_id: Location for monitoring data
            context: Additional context (current conditions, etc.)
        
        Returns:
            Agent response with reasoning trace
        """
        start_time = datetime.utcnow()
        session_id = session_id or str(uuid.uuid4())
        context = context or {}
        
        if not self.is_initialized:
            # Use rule-based fallback
            response = self._rule_based_response(query, context, location_id)
            return {
                "session_id": session_id,
                "query": query,
                "response": response["answer"],
                "reasoning_trace": response.get("trace", []),
                "tools_used": response.get("tools_used", []),
                "latency_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "model": "rule-based",
            }
        
        try:
            # Run LangGraph agent
            result = await self._run_agent(query, context)
            
            return {
                "session_id": session_id,
                "query": query,
                "response": result["response"],
                "reasoning_trace": result.get("trace", []),
                "tools_used": result.get("tools_used", []),
                "latency_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "model": self.llm_model,
            }
            
        except Exception as e:
            logger.error(f"Agent query failed: {e}")
            # Fall back to rule-based
            response = self._rule_based_response(query, context, location_id)
            return {
                "session_id": session_id,
                "query": query,
                "response": response["answer"],
                "reasoning_trace": [{"step": "fallback", "reason": str(e)}],
                "tools_used": [],
                "latency_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "model": "rule-based (fallback)",
            }
    
    async def _run_agent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the LangGraph agent."""
        from langchain_core.messages import HumanMessage
        
        # Add context to query if available
        enhanced_query = query
        if context.get("aqi"):
            enhanced_query += f"\n\nCurrent context: AQI={context['aqi']}, Dominant pollutant={context.get('dominant_pollutant', 'unknown')}"
        
        messages = [HumanMessage(content=enhanced_query)]
        
        result = await self.agent.ainvoke({"messages": messages})
        
        # Extract response and trace
        tools_used = []
        trace = []
        
        for msg in result.get("messages", []):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tools_used.append(tc.get("name", "unknown"))
                    trace.append({
                        "step": "tool_call",
                        "tool": tc.get("name"),
                        "args": tc.get("args", {}),
                    })
            elif hasattr(msg, "content") and msg.content:
                trace.append({
                    "step": "reasoning",
                    "content": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content,
                })
        
        # Get final response
        final_response = ""
        if result.get("messages"):
            final_msg = result["messages"][-1]
            final_response = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
        
        return {
            "response": final_response,
            "tools_used": list(set(tools_used)),
            "trace": trace,
        }
    
    def _rule_based_response(
        self,
        query: str,
        context: Dict[str, Any],
        location_id: int,
    ) -> Dict[str, Any]:
        """Generate response using rule-based logic when LLM unavailable."""
        from app.config import settings
        
        aqi = context.get("aqi", 100)
        aqi_cat = context.get("aqi_category", "Moderate")
        dominant = context.get("dominant_pollutant", "PM2.5")
        city = context.get("city", settings.default_city)
        
        q_lower = query.lower()
        tools_used = []
        trace = []
        
        # Intent detection and response generation
        if any(w in q_lower for w in ["aqi", "air quality", "pollution", "how is"]):
            tools_used.append("get_current_aqi")
            trace.append({"step": "intent", "detected": "current_conditions"})
            
            answer = f"""**Current Air Quality — {city}**

• **AQI**: {aqi:.0f} ({aqi_cat})
• **Dominant Pollutant**: {dominant}

"""
            if aqi > 200:
                answer += """⚠️ **Health Alert**: Air quality is poor. 
- Avoid outdoor activities
- Wear N95 masks if going outside
- Keep windows closed
- Use air purifiers if available"""
            elif aqi > 100:
                answer += """⚠️ **Advisory**: Moderate air quality.
- Sensitive groups should limit outdoor exposure
- Consider reducing strenuous outdoor activities"""
            else:
                answer += "✅ Air quality is acceptable for most people."
                
        elif any(w in q_lower for w in ["comply", "regulation", "who", "cpcb", "legal", "standard"]):
            tools_used.append("check_compliance")
            trace.append({"step": "intent", "detected": "compliance_check"})
            
            compliance = context.get("compliance", {})
            who_ok = compliance.get("who_compliant", False)
            cpcb_ok = compliance.get("cpcb_compliant", False)
            
            answer = f"""**Regulatory Compliance Status**

• **WHO 2021 Guidelines**: {'✅ Compliant' if who_ok else '❌ Non-Compliant'}
• **CPCB (India NAAQS)**: {'✅ Compliant' if cpcb_ok else '❌ Non-Compliant'}

"""
            if not who_ok and not cpcb_ok:
                answer += """Both international and national air quality standards are being exceeded. 
Immediate attention is required to reduce pollution sources."""
                
        elif any(w in q_lower for w in ["cause", "why", "source", "reason", "root"]):
            tools_used.append("analyze_pollution_source")
            trace.append({"step": "intent", "detected": "root_cause_analysis"})
            
            answer = f"""**Root Cause Analysis: {dominant} Elevation**

**Likely Sources:**
1. **Vehicular Emissions** — Traffic congestion and diesel vehicles
2. **Construction Dust** — Building activities and road work
3. **Industrial Activity** — Factory emissions and power plants

**Contributing Factors:**
• Low wind speeds trapping pollutants near surface
• Rush hour traffic peaks
• Temperature inversions concentrating pollution

**Recommendations:**
• Implement traffic restrictions during peak hours
• Enforce dust suppression at construction sites
• Inspect industrial emission compliance"""

        elif any(w in q_lower for w in ["forecast", "predict", "tomorrow", "next"]):
            tools_used.append("get_forecast")
            trace.append({"step": "intent", "detected": "forecast"})
            
            answer = f"""**AQI Forecast (Next 24 Hours)**

Based on current trends (AQI: {aqi:.0f}):

• **Expected Range**: {max(50, aqi*0.8):.0f} - {min(500, aqi*1.3):.0f}
• **Peak Hours**: 8-11 AM and 6-9 PM (rush hours)
• **Trend**: {'Deteriorating' if aqi > 150 else 'Relatively Stable'}

**Driving Factors:**
• Morning and evening traffic congestion
• Meteorological conditions (wind, temperature)
• Industrial activity patterns"""

        elif any(w in q_lower for w in ["health", "risk", "safe", "outdoor", "exercise"]):
            tools_used.append("assess_health_risk")
            trace.append({"step": "intent", "detected": "health_risk"})
            
            risk_level = "Low" if aqi <= 50 else "Moderate" if aqi <= 100 else "High" if aqi <= 200 else "Very High" if aqi <= 300 else "Severe"
            
            answer = f"""**Health Risk Assessment**

• **Risk Level**: {risk_level}
• **Current AQI**: {aqi:.0f}

**Recommendations:**
"""
            if aqi > 200:
                answer += """• ⛔ Avoid ALL outdoor physical activity
• Keep windows and doors closed
• Use N95 masks if outdoor exposure is unavoidable
• Run air purifiers indoors
• Monitor any respiratory symptoms"""
            elif aqi > 100:
                answer += """• ⚠️ Limit prolonged outdoor exertion
• Sensitive groups (children, elderly, asthma patients) should stay indoors
• Monitor local air quality updates"""
            else:
                answer += """• ✅ Outdoor activities are generally safe
• Sensitive individuals may want to limit prolonged exertion
• Good time for outdoor exercise"""

        else:
            # Generic helpful response
            answer = f"""**GreenPulse AI Environmental Assistant**

I can help you with:

• 📊 **Current Air Quality** — Real-time AQI and pollutant levels
• ⚖️ **Compliance Checking** — WHO, CPCB, NAAQS standards
• 🔍 **Root Cause Analysis** — Pollution source identification
• 🌡️ **Forecasting** — 24-72 hour AQI predictions
• ❤️ **Health Advice** — Risk assessment and recommendations

**Current Status:**
• **AQI**: {aqi:.0f} ({aqi_cat})
• **Location**: {city}
• **Dominant Pollutant**: {dominant}

Try asking:
- "What's the current air quality?"
- "Is it safe to go outside?"
- "Why is PM2.5 high today?"
- "Check WHO compliance"

💡 *Configure LLM_API_KEY in .env for full AI-powered analysis.*"""

        return {
            "answer": answer,
            "tools_used": tools_used,
            "trace": trace,
        }


class AgentSessionManager:
    """Manages conversation sessions and context."""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.local_sessions: Dict[str, Dict] = {}
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieve session context."""
        if self.redis:
            try:
                import json
                data = await self.redis.get(f"greenpulse:agent_session:{session_id}")
                if data:
                    return json.loads(data)
            except Exception:
                pass
        
        return self.local_sessions.get(session_id, {"messages": [], "created_at": datetime.utcnow().isoformat()})
    
    async def save_session(self, session_id: str, data: Dict[str, Any]):
        """Save session context."""
        if self.redis:
            try:
                import json
                await self.redis.setex(
                    f"greenpulse:agent_session:{session_id}",
                    3600,  # 1 hour TTL
                    json.dumps(data, default=str)
                )
                return
            except Exception:
                pass
        
        self.local_sessions[session_id] = data
    
    async def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Add message to session history."""
        session = await self.get_session(session_id)
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
        
        # Keep last 20 messages
        session["messages"] = session["messages"][-20:]
        
        await self.save_session(session_id, session)
