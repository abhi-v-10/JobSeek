from app.schemas.chat import AgentMessage, ChatResponse
from app.services.django_service import get_session_messages, save_message
from app.services.intent_service import detect_intent
from app.services.openai_service import ask_ai, generate_chat_title
from app.tools import job_tool
from app.tools import resume_tool
from fastapi import APIRouter, Header, UploadFile, File, Form, Body
from typing import Optional
from app.utils.file_parser import extract_text_from_file, encode_image

router = APIRouter()

@router.post("/title")
def get_title(payload: dict = Body(...)):
    """Generate a title for a chat session."""
    message = payload.get("message", "")
    title = generate_chat_title(message)
    return {"title": title}


@router.post("/", response_model=ChatResponse)
async def chat(
    session_id: str = Form(...),
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    authorization: str = Header(None)
):
    """
    Handle chat request by persisting messages to Django and getting AI reply.
    """
    file_context = None
    image_base64 = None
    
    if file:
        content = await file.read()
        filename = file.filename
        if filename.lower().split(".")[-1] in ["jpg", "jpeg", "png", "webp"]:
            image_base64 = encode_image(content)
        else:
            file_context = extract_text_from_file(content, filename)

    # Save user message
    save_message(
        session_id=session_id,
        role="user",
        content=message,
        auth_token=authorization,
    )

    # Load history with context
    history_response = get_session_messages(session_id, auth_token=authorization)
    history = history_response.get("data", [])

    # Detect intent
    intent = detect_intent(message)

    if intent == "job_search":
        ai_reply, job_data = job_tool.run_with_data(message)
        message_type = "jobs"
    elif intent == "resume_review":
        ai_reply = resume_tool.run(auth_token=authorization)
        message_type = "resume_feedback"
        job_data = None
    else:
        ai_reply = ask_ai(message, history, file_context=file_context, image_base64=image_base64)
        message_type = "text"
        job_data = None

    # Save AI reply
    save_message(
        session_id=session_id,
        role="assistant",
        content=ai_reply,
        message_type=message_type,
        metadata={"jobs": job_data} if job_data else {},
        auth_token=authorization,
    )

    return ChatResponse(
        success=True,
        session_id=session_id,
        message=AgentMessage(
            type=message_type,
            content=ai_reply,
            data=job_data,
        ),
    )

