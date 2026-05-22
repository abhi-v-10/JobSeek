import { logout } from "../utils/authUtils";

// ── Structured job data returned by the search tool ───────────────────────────
export interface JobSearchResult {
  id: number;
  title: string;
  company_name: string;
  location: string;
  is_remote: boolean;
  job_type: string;
  skills?: string | null;
  created_at: string;
}

// ── Full job object from Django's JobSerializer ────────────────────────────────
export interface FullJobData {
  id: number;
  status: string;
  posted_by: number;
  posted_by_username: string | null;
  job_type: string;
  company: string;
  position: string;
  type: string;
  required_experience_years: number | null;
  required_experience_fields: string;
  work: string;
  daily_work_time: number | null;
  hourly_wage: string;
  location: string;
  salary_min: number | null;
  salary_max: number | null;
  description: string;
  work_mode: string;
  is_saved: boolean;
  is_applied: boolean;
  is_own_job: boolean;
  applied_count: number;
  viewed_count: number;
  saved_count: number;
  created_at: string;
  updated_at: string;
}

// ── Chat session & message shapes (Django) ─────────────────────────────────────
export interface ChatSessionData {
  id: string;
  title: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageData {
  id: number;
  session: string;
  role: "user" | "assistant" | "system";
  message_type: string;
  content: string;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}

// ── FastAPI response shape ─────────────────────────────────────────────────────
export interface SendMessageResponse {
  success: boolean;
  session_id: string;
  message: {
    type: string;
    content: string;
    /** Structured job list when type === 'jobs', null otherwise */
    data?: JobSearchResult[] | null;
  };
}

// ── Internal helpers ───────────────────────────────────────────────────────────
const DJANGO_BASE = "http://127.0.0.1:8000/api";
const FASTAPI_BASE = "http://127.0.0.1:8001";

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

/**
 * Wrapper around fetch that automatically logs the user out on a 401 response
 * (expired / invalid / revoked token).
 */
async function authFetch(
  input: RequestInfo,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401) {
    logout();
  }
  return response;
}

// ── Service object ─────────────────────────────────────────────────────────────
export const chatService = {
  /** Create a new chat session in Django. */
  async createSession(title: string = "New Chat"): Promise<ChatSessionData> {
    const response = await authFetch(`${DJANGO_BASE}/chat/sessions/`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ title }),
    });
    if (!response.ok) {
      throw new Error(
        `Failed to create session: ${response.status} ${response.statusText}`,
      );
    }
    return response.json() as Promise<ChatSessionData>;
  },

  /** List all sessions for the current user. Handles both paginated and plain-array responses. */
  async getSessions(): Promise<ChatSessionData[]> {
    const response = await authFetch(`${DJANGO_BASE}/chat/sessions/`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error(
        `Failed to fetch sessions: ${response.status} ${response.statusText}`,
      );
    }
    const data = await response.json();
    if (Array.isArray(data)) return data as ChatSessionData[];
    if (data && Array.isArray(data.results))
      return data.results as ChatSessionData[];
    return [];
  },

  /** Retrieve all messages for a session from Django. */
  async getMessages(sessionId: string): Promise<ChatMessageData[]> {
    const response = await authFetch(
      `${DJANGO_BASE}/chat/sessions/${sessionId}/messages/`,
      {
        method: "GET",
        headers: getAuthHeaders(),
      },
    );
    if (!response.ok) {
      throw new Error(
        `Failed to fetch messages: ${response.status} ${response.statusText}`,
      );
    }
    const data = await response.json();
    // Response shape: { success: true, data: ChatMessageData[] }
    return (data?.data ?? []) as ChatMessageData[];
  },

  /** Generate an AI title for a chat session based on the first message. */
  async generateTitle(message: string): Promise<string> {
    const response = await fetch(`${FASTAPI_BASE}/chat/title`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!response.ok) return message.slice(0, 30);
    const data = await response.json();
    return data.title;
  },

  /** Delete a chat session. */
  async deleteSession(sessionId: string): Promise<void> {
    const response = await authFetch(
      `${DJANGO_BASE}/chat/sessions/${sessionId}/`,
      {
        method: "DELETE",
        headers: getAuthHeaders(),
      },
    );
    if (!response.ok) {
      throw new Error("Failed to delete session");
    }
  },

  /** Update chat session title. */
  async updateSession(sessionId: string, title: string): Promise<void> {
    const response = await authFetch(
      `${DJANGO_BASE}/chat/sessions/${sessionId}/`,
      {
        method: "PATCH",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title }),
      },
    );
    if (!response.ok) {
      throw new Error("Failed to update session title");
    }
  },

  /** Send a message to the FastAPI AI engine. Returns structured data for job results. */
  async sendMessage(
    sessionId: string,
    message: string,
    signal?: AbortSignal,
    file?: File | null,
  ): Promise<SendMessageResponse> {
    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("message", message);
    if (file) {
      formData.append("file", file);
    }

    const token = localStorage.getItem("access_token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await authFetch(`${FASTAPI_BASE}/chat/`, {
      method: "POST",
      headers,
      body: formData,
      signal,
    });
    if (!response.ok) {
      throw new Error(
        `Failed to send message: ${response.status} ${response.statusText}`,
      );
    }
    return response.json() as Promise<SendMessageResponse>;
  },

  /** Fetch full job details from Django's JobSerializer (all fields including description, salary, etc.). */
  async getJobDetail(jobId: number): Promise<FullJobData> {
    const response = await authFetch(`${DJANGO_BASE}/jobs/${jobId}/`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error(
        `Failed to fetch job details: ${response.status} ${response.statusText}`,
      );
    }
    return response.json() as Promise<FullJobData>;
  },
};
