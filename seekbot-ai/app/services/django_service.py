import requests
from app.core.config import DJANGO_API_BASE_URL


def get_session_messages(session_id: str, auth_token: str = None):
    """
    Retrieve all messages for a session from Django.
    """
    url = f"{DJANGO_API_BASE_URL}/sessions/{session_id}/messages/"
    headers = {"Authorization": auth_token} if auth_token else {}
    
    response = requests.get(url, headers=headers, timeout=10)
    if not response.ok:
        print(f"Django API Error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return response.json()


def save_message(session_id: str, role: str, content: str, message_type="text", metadata=None, auth_token: str = None):
    """
    Save a message to a session in Django.
    """
    url = f"{DJANGO_API_BASE_URL}/sessions/{session_id}/messages/"
    headers = {"Authorization": auth_token} if auth_token else {}

    payload = {
        "role": role,
        "message_type": message_type,
        "content": content,
        "metadata": metadata or {}
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    if not response.ok:
        print(f"Django API Error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return response.json()