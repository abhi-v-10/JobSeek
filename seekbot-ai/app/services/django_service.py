import requests
from app.core.config import DJANGO_API_BASE_URL


def get_session_messages(session_id: str, auth_token: str = None):
    """
    Retrieve all messages for a session from Django.
    """
    url = f"{DJANGO_API_BASE_URL}/chat/sessions/{session_id}/messages/"
    headers = {"Authorization": auth_token} if auth_token else {}

    response = requests.get(url, headers=headers, timeout=10)
    if not response.ok:
        print(f"Django API Error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return response.json()


def save_message(
    session_id: str,
    role: str,
    content: str,
    message_type="text",
    metadata=None,
    auth_token: str = None,
):
    """
    Save a message to a session in Django.
    """
    url = f"{DJANGO_API_BASE_URL}/chat/sessions/{session_id}/messages/"
    headers = {"Authorization": auth_token} if auth_token else {}

    payload = {
        "role": role,
        "message_type": message_type,
        "content": content,
        "metadata": metadata or {},
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    if not response.ok:
        print(f"Django API Error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return response.json()


def fetch_user_resume(auth_token: str = None) -> dict:
    """
    Fetch the authenticated user's parsed resume from Django.

    Args:
        auth_token: The user's Authorization header value (Bearer token).

    Returns:
        Dict with keys: success, resume_text, resume_url, etc.

    Raises:
        RuntimeError: If the Django API call fails.
    """
    url = f"{DJANGO_API_BASE_URL}/users/me/resume/"
    headers = {"Authorization": auth_token} if auth_token else {}

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Failed to connect to Django API: {exc}") from exc

    if response.status_code == 404:
        return {"success": False, "message": "No resume uploaded."}

    if not response.ok:
        raise RuntimeError(
            f"Django resume API returned {response.status_code}: {response.text}"
        )

    return response.json()


def fetch_user_profile(auth_token: str = None) -> dict:
    """
    Fetch the authenticated user's full profile from Django.

    Returns the ProfileSerializer payload which includes:
    skills (list), parsed_resume (JSON), resume_text, full_name,
    linkedin_url, github_url, user_type, etc.

    Args:
        auth_token: The user's Authorization header value (Bearer token).

    Returns:
        Profile dict, or empty dict on any error.
    """
    url = f"{DJANGO_API_BASE_URL}/users/profile/"
    headers = {"Authorization": auth_token} if auth_token else {}

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Failed to connect to Django API: {exc}") from exc

    if not response.ok:
        return {}

    return response.json()
