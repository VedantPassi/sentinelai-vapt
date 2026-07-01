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

// Agent Scans
export interface ProgressEvent {
  node: string;
  status: string;
  message: string;
  timestamp: string;
}

export interface AgentScan {
  id: string;
  status: string;
  target_url: string;
  target_type: string;
  created_at: string;
  progress_events: ProgressEvent[];
  error: string | null;
}

export interface AgentFinding {
  id: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  description: string;
  remediation: string | null;
  status: string;
  srs_score: number | null;
  validation_reasoning: string;
  confirmed: boolean;
}

export interface FindingDetail extends AgentFinding {
  scan_id: string;
  poc_evidence: string | null;
}

export interface FindingUpdate {
  status?: "open" | "confirmed" | "false_positive" | "fixed";
  remediation?: string;
}

export async function getFinding(id: string): Promise<FindingDetail> {
  return request<FindingDetail>(`/findings/${id}`);
}

export async function patchFinding(
  id: string,
  data: FindingUpdate
): Promise<FindingDetail> {
  return request<FindingDetail>(`/findings/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function revalidateFinding(id: string): Promise<FindingDetail> {
  return request<FindingDetail>(`/findings/${id}/validate`, {
    method: "POST",
  });
}

export interface AgentFindingsResponse {
  scan_id: string;
  total: number;
  findings: AgentFinding[];
}

export async function createAgentScan(data: {
  target_id: string;
  target_url: string;
  target_type: string;
  config?: Record<string, unknown>;
}): Promise<AgentScan> {
  return request<AgentScan>("/agent-scans", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getAgentScan(id: string): Promise<AgentScan> {
  return request<AgentScan>(`/agent-scans/${id}`);
}

export async function getAgentScanFindings(
  id: string,
  severity?: string
): Promise<AgentFindingsResponse> {
  const qs = severity ? `?severity=${severity}` : "";
  return request<AgentFindingsResponse>(`/agent-scans/${id}/findings${qs}`);
}

export function connectAgentScanWS(
  scanId: string,
  onEvent: (event: ProgressEvent | { node: string; status: string; message: string; error?: string }) => void
): WebSocket {
  const wsBase = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1")
    .replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/agent-scans/ws/${scanId}?token=${getToken() ?? ""}`);
  ws.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)); } catch { /* ignore malformed */ }
  };
  return ws;
}
