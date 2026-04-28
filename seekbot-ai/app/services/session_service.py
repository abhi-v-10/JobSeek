import uuid

def create_session() -> str:
    return str(uuid.uuid4())

def get_or_create_session(session_id: str | None) -> str:
    if session_id:
        return session_id
    return create_session()