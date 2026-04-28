from fastapi import APIRouter, Header, Request
from app.schemas.chat import ChatRequest, ChatResponse, AgentMessage
from app.services.session_service import get_or_create_session
from app.services.django_service import get_session_messages, save_message
from app.services.openai_service import ask_ai
from app.services.intent_service import detect_intent

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest, authorization: str = Header(None)):
    """
    Handle chat request by persisting messages to Django and getting AI reply.
    The authorization header is forwarded to Django for session ownership verification.
    """
    session_id = payload.session_id

    # Save user message (forwarding auth token)
    save_message(
        session_id=session_id,
        role="user",
        content=payload.message,
        auth_token=authorization
    )

    # Load history with context
    history_response = get_session_messages(session_id, auth_token=authorization)
    history = history_response.get("data", [])

    # Ask AI with context
    ai_reply = ask_ai(payload.message, history)

    # Save AI reply
    save_message(
        session_id=session_id,
        role="assistant",
        content=ai_reply,
        auth_token=authorization
    )

    return ChatResponse(
        success=True,
        session_id=session_id,
        message=AgentMessage(
            type="text",
            content=ai_reply
        )
    )