const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.detail ?? res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// Auth
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function register(
  email: string,
  password: string,
  org_name: string
): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, org_name }),
  });
}

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// Targets
export interface Target {
  id: string;
  org_id: string;
  name: string;
  type: "web" | "api" | "network";
  url: string;
  scope_definition: Record<string, unknown> | null;
  asset_criticality: number;
  verified: boolean;
}

export interface TargetCreate {
  name: string;
  type: "web" | "api" | "network";
  url: string;
  scope_definition?: Record<string, unknown>;
  asset_criticality?: number;
}

export async function listTargets(): Promise<Target[]> {
  return request<Target[]>("/targets");
}

export async function createTarget(data: TargetCreate): Promise<Target> {
  return request<Target>("/targets", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getTarget(id: string): Promise<Target> {
  return request<Target>(`/targets/${id}`);
}

export async function updateTarget(
  id: string,
  data: Partial<TargetCreate>
): Promise<Target> {
  return request<Target>(`/targets/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteTarget(id: string): Promise<void> {
  return request<void>(`/targets/${id}`, { method: "DELETE" });
}
