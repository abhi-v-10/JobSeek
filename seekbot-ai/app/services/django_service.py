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


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------
#
# IMPORTANT — additive only.
#
# Django exposes POST /users/skills/bulk/, but that endpoint DELETES every
# existing skill before recreating from the payload. The agent must never
# destroy user-entered data, so skill writes go one-at-a-time through
# POST /users/skills/, which only ever appends.


def add_user_skill(
    name: str,
    category: str = "technical",
    auth_token: str = None,
) -> dict:
    """
    Append a single skill to the authenticated user's profile.

    Additive only — never removes or overwrites existing skills.

    Args:
        name: Skill name (e.g. "FastAPI").
        category: One of "technical", "language", "other".
        auth_token: Bearer token forwarded from the user's request.

    Returns:
        {"success": bool, "name": str, "error": str | None}
    """
    if not name or not str(name).strip():
        return {"success": False, "name": name, "error": "Empty skill name."}

    safe_category = category if category in {"technical", "language", "other"} else "technical"

    url = f"{DJANGO_API_BASE_URL}/users/skills/"
    headers = {"Authorization": auth_token} if auth_token else {}
    payload = {"name": str(name).strip()[:100], "category": safe_category}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.exceptions.RequestException as exc:
        return {"success": False, "name": name, "error": f"Connection failed: {exc}"}

    if not response.ok:
        return {
            "success": False,
            "name": name,
            "error": f"Django returned {response.status_code}: {response.text[:200]}",
        }

    return {"success": True, "name": name, "error": None}


def add_user_skills(
    skills: list,
    category: str = "technical",
    auth_token: str = None,
) -> dict:
    """
    Append several skills to the profile, tolerating partial failure.

    Each skill is written independently — one rejected skill does not block
    the rest. Returns a summary so the agent can report exactly what landed.

    Args:
        skills: List of skill names, or dicts with "name"/"category" keys.
        category: Default category for bare string entries.
        auth_token: Bearer token forwarded from the user's request.

    Returns:
        {"success": bool, "added": [...], "failed": [{"name", "error"}]}
    """
    added: list[str] = []
    failed: list[dict] = []

    for entry in skills or []:
        if isinstance(entry, dict):
            name = entry.get("name")
            entry_category = entry.get("category") or category
        else:
            name = entry
            entry_category = category

        result = add_user_skill(name=name, category=entry_category, auth_token=auth_token)
        if result["success"]:
            added.append(result["name"])
        else:
            failed.append({"name": result["name"], "error": result["error"]})

    return {
        "success": bool(added) and not failed,
        "added": added,
        "failed": failed,
    }
