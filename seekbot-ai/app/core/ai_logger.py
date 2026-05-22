"""
Compact AI activity logger for SeekBot.

Writes a single, human-readable log line per event to logs/ai.log.
Every line includes: timestamp | session-id | event-kind | detail.

Usage:
    from app.core.ai_logger import log_user_message, log_tool_call, log_agent_response
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Log file setup — seekbot-ai/logs/ai.log
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_DIR = os.path.join(_BASE_DIR, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_LOG_FILE = os.path.join(_LOG_DIR, "ai.log")

_logger = logging.getLogger("seekbot.ai_activity")
_logger.setLevel(logging.INFO)
_logger.propagate = False  # Don't bubble up to root logger

if not _logger.handlers:
    _handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5_000_000,  # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)


# ---------------------------------------------------------------------------
# Internal formatter
# ---------------------------------------------------------------------------


def _line(session_id: str, kind: str, detail: str) -> str:
    """Build a single compact log line with an ISO timestamp."""
    from datetime import datetime

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sid = (session_id or "—")[:16]
    return f"{ts} | SID:{sid} | {kind:<14} | {detail}"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def log_user_message(session_id: str, message: str) -> None:
    """Log a message sent by the user to the agent."""
    preview = message[:150].replace("\n", " ")
    _logger.info(_line(session_id, "USER_MSG", f'"{preview}"'))


def log_tool_call(session_id: str, tool_name: str, detail: str = "") -> None:
    """Log a tool being invoked by the agent."""
    suffix = f" — {detail}" if detail else ""
    _logger.info(_line(session_id, "TOOL", f"{tool_name}{suffix}"))


def log_agent_response(session_id: str, message_type: str, content: str) -> None:
    """Log the agent's reply before it is returned to the client."""
    preview = (content or "")[:150].replace("\n", " ")
    _logger.info(_line(session_id, "AGENT_RESP", f'type={message_type} | "{preview}"'))
