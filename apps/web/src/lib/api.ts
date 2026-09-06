/**
 * Thin API client. The access token lives in memory only; the refresh token
 * is an httpOnly cookie the browser sends to /api/v1/auth/refresh and nowhere
 * else.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function hasAccessToken(): boolean {
  return accessToken !== null;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "content-type": "application/json",
      ...(accessToken ? { authorization: `Bearer ${accessToken}` } : {}),
      ...init.headers,
    },
  });

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      body?.error?.code ?? "unknown",
      body?.error?.message ?? "The request could not be completed.",
    );
  }
  return body as T;
}

/**
 * Use the in-memory token if we have one, otherwise try the refresh cookie.
 *
 * Calling refresh unconditionally on every mount costs a round trip and, more
 * importantly, turns a page load straight after login into a 401 whenever the
 * cookie has not settled.
 */
export async function ensureSession(): Promise<boolean> {
  if (accessToken) return true;
  try {
    const { access_token } = await api.refresh();
    setAccessToken(access_token);
    return true;
  } catch {
    return false;
  }
}

export interface TokenResponse {
  access_token: string;
  expires_in: number;
}

export interface Course {
  id: string;
  slug: string;
  title: string;
  description: string | null;
}

export interface QuestionForLearner {
  id: string;
  type: string;
  stem: string;
  options: { id: string; text: string }[] | null;
}

export interface NextQuestion {
  question: QuestionForLearner | null;
  decision_id: string;
  rationale: string;
  exhausted: boolean;
}

export interface AttemptResult {
  attempt_id: string;
  recorded_at: string;
  is_correct: boolean | null;
  diagnosis: string | null;
  confidence: number | null;
  feedback: string | null;
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, display_name: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    }),

  refresh: () => request<TokenResponse>("/auth/refresh", { method: "POST" }),

  me: () => request<{ id: string; email: string; display_name: string; role: string }>("/auth/me"),

  courses: () => request<Course[]>("/courses"),

  startSession: (course_id: string, mode = "practice") =>
    request<{ id: string; course_id: string; mode: string; started_at: string }>("/sessions", {
      method: "POST",
      body: JSON.stringify({ course_id, mode }),
    }),

  nextQuestion: (sessionId: string) =>
    request<NextQuestion>(`/sessions/${sessionId}/next`),

  submit: (
    sessionId: string,
    payload: { question_id: string; response_text?: string; latency_ms?: number },
  ) =>
    request<AttemptResult>(`/sessions/${sessionId}/attempts`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
