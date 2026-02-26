"""
ORM Model: Agent Log
Traces LLM reasoning chains, tool calls, and responses.
"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    agent_response: Mapped[str] = mapped_column(Text, nullable=True)
    reasoning_trace: Mapped[dict] = mapped_column(JSON, nullable=True)  # steps + tool calls
    tools_used: Mapped[dict] = mapped_column(JSON, nullable=True)       # list of tool names
    llm_model: Mapped[str] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Integer, default=1)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<AgentLog id={self.id} session='{self.session_id}'>"
