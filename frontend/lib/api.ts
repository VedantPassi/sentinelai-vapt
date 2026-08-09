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
    const detail = body?.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join("; ")
        : res.statusText;
    throw new ApiError(res.status, message);
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

export async function listAgentScans(): Promise<AgentScan[]> {
  return request<AgentScan[]>("/agent-scans");
}

export async function getAgentScanFindings(
  id: string,
  severity?: string
): Promise<AgentFindingsResponse> {
  const qs = severity ? `?severity=${severity}` : "";
  return request<AgentFindingsResponse>(`/agent-scans/${id}/findings${qs}`);
}

export interface ChainStep {
  step: number;
  action: string;
  mitre_id: string | null;
  finding_id: string | null;
  surface: string | null;
}

export interface AgentChain {
  id: string;
  title: string;
  description: string;
  impact: "critical" | "high" | "medium" | "low";
  likelihood: "high" | "medium" | "low";
  mitre_ids: string[];
  finding_ids: string[];
  steps: ChainStep[];
  created_at: string;
}

export async function listAgentScanChains(id: string): Promise<AgentChain[]> {
  const res = await request<{ scan_id: string; total: number; chains: AgentChain[] }>(
    `/agent-scans/${id}/chains`
  );
  return res.chains;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "finding" | "chain" | "step";
  severity: string | null;
  surface: string | null;
  risk_score: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface AttackGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface BlastRadius {
  finding_id: string;
  finding_title: string;
  chains_affected: number;
  chain_titles: string[];
  max_impact: string;
}

export async function getAttackGraph(scanId: string): Promise<AttackGraph> {
  return request<AttackGraph>(`/attack-graph/scan/${scanId}`);
}

export async function getBlastRadius(scanId: string): Promise<BlastRadius[]> {
  return request<BlastRadius[]>(`/attack-graph/scan/${scanId}/blast-radius`);
}

// Schedules
export interface Schedule {
  id: string;
  target_id: string;
  scan_type: string;
  interval_hours: number;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string;
  created_at: string;
}

export interface ScheduleCreate {
  target_id: string;
  scan_type: string;
  interval_hours: number;
  config?: Record<string, unknown>;
}

export async function listSchedules(): Promise<Schedule[]> {
  return request<Schedule[]>("/schedules");
}

export async function createSchedule(data: ScheduleCreate): Promise<Schedule> {
  return request<Schedule>("/schedules", { method: "POST", body: JSON.stringify(data) });
}

export async function toggleSchedule(id: string, is_active: boolean): Promise<Schedule> {
  return request<Schedule>(`/schedules/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ is_active }),
  });
}

export async function deleteSchedule(id: string): Promise<void> {
  return request<void>(`/schedules/${id}`, { method: "DELETE" });
}

// Users
export type UserRole = "admin" | "analyst" | "viewer";

export interface CurrentUser {
  id: string;
  email: string;
  role: UserRole;
  org_id: string;
}

export type OrgUser = CurrentUser;

export async function getCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/me");
}

export async function listUsers(): Promise<OrgUser[]> {
  return request<OrgUser[]>("/users");
}

export async function inviteUser(email: string, password: string, role: UserRole): Promise<OrgUser> {
  return request<OrgUser>("/users", {
    method: "POST",
    body: JSON.stringify({ email, password, role }),
  });
}

export async function updateUserRole(userId: string, role: UserRole): Promise<OrgUser> {
  return request<OrgUser>(`/users/${userId}/role`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export async function removeUser(userId: string): Promise<void> {
  return request<void>(`/users/${userId}`, { method: "DELETE" });
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
