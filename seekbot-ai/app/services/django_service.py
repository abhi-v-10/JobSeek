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


def fetch_application_dashboard(auth_token: str = None) -> dict:
    """
    Fetch the authenticated user's application dashboard data from Django.
    """
    url = f"{DJANGO_API_BASE_URL}/applications/dashboard/"
    headers = {"Authorization": auth_token} if auth_token else {}

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as exc:
        return {}

    if not response.ok:
        return {}

    return response.json()


def fetch_application_analytics(auth_token: str = None) -> dict:
    """
    Fetch the authenticated user's application analytics data from Django.
    """
    url = f"{DJANGO_API_BASE_URL}/applications/analytics/"
    headers = {"Authorization": auth_token} if auth_token else {}

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as exc:
        return {}

    if not response.ok:
        return {}

    return response.json()


def fetch_upcoming_interviews(auth_token: str = None) -> dict:
    """
    Fetch the authenticated user's upcoming interviews from Django.
    """
    url = f"{DJANGO_API_BASE_URL}/applications/upcoming-interviews/"
    headers = {"Authorization": auth_token} if auth_token else {}

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as exc:
        return {}

    if not response.ok:
        return {}

    return response.json()
