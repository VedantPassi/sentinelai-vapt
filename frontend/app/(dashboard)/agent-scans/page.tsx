"use client";

import { useEffect, useRef, useState } from "react";
import {
  AgentFinding,
  AgentScan,
  ProgressEvent,
  connectAgentScanWS,
  createAgentScan,
  getAgentScan,
  getAgentScanFindings,
  listAgentScans,
  listTargets,
  patchFinding,
  revalidateFinding,
  Target,
} from "@/lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "text-red-600 bg-red-50",
  high: "text-orange-600 bg-orange-50",
  medium: "text-yellow-600 bg-yellow-50",
  low: "text-blue-600 bg-blue-50",
  info: "text-gray-600 bg-gray-50",
};

const STATUS_COLOR: Record<string, string> = {
  pending: "text-gray-500",
  running: "text-blue-600 animate-pulse",
  completed: "text-green-600",
  failed: "text-red-600",
};

function srsColor(score: number | null): string {
  if (score === null) return "bg-gray-100 text-gray-500";
  if (score >= 70) return "bg-red-100 text-red-700";
  if (score >= 40) return "bg-orange-100 text-orange-700";
  return "bg-gray-100 text-gray-500";
}

function FindingStatusBadge({ status }: { status: string }) {
  if (status === "confirmed")
    return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-green-100 text-green-700">CONFIRMED</span>;
  if (status === "false_positive")
    return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-red-100 text-red-500 line-through">FALSE POSITIVE</span>;
  if (status === "fixed")
    return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-600">FIXED</span>;
  return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gray-100 text-gray-500">OPEN</span>;
}

function FindingCard({
  finding,
  onUpdate,
}: {
  finding: AgentFinding;
  onUpdate: (updated: AgentFinding) => void;
}) {
  const [revalidating, setRevalidating] = useState(false);
  const [patching, setPatching] = useState<string | null>(null);
  const [showReasoning, setShowReasoning] = useState(false);

  async function handlePatch(newStatus: "confirmed" | "false_positive") {
    setPatching(newStatus);
    const optimistic = { ...finding, status: newStatus, confirmed: newStatus === "confirmed" };
    onUpdate(optimistic);
    try {
      const updated = await patchFinding(finding.id, { status: newStatus });
      onUpdate({ ...finding, ...updated });
    } catch {
      onUpdate(finding); // revert
    } finally {
      setPatching(null);
    }
  }

  async function handleRevalidate() {
    setRevalidating(true);
    try {
      const updated = await revalidateFinding(finding.id);
      onUpdate({ ...finding, ...updated });
    } catch { /* non-critical */ }
    finally {
      setRevalidating(false);
    }
  }

  const canAct = finding.status === "open" || finding.status === "confirmed";

  return (
    <div className="border rounded p-3 space-y-2">
      <div className="flex items-start gap-2">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded shrink-0 ${SEVERITY_COLOR[finding.severity] ?? ""}`}>
          {finding.severity.toUpperCase()}
        </span>
        <span className="font-medium text-sm flex-1">{finding.title}</span>
        <div className="flex items-center gap-2 shrink-0">
          {finding.srs_score !== null && finding.srs_score !== undefined && (
            <span className={`text-xs font-mono px-2 py-0.5 rounded ${srsColor(finding.srs_score)}`}>
              SRS: {finding.srs_score}
            </span>
          )}
          <FindingStatusBadge status={finding.status} />
          <span className="text-xs text-gray-400">{finding.category}</span>
        </div>
      </div>

      <p className="text-sm text-gray-600">{finding.description}</p>

      {finding.validation_reasoning && (
        <div>
          <button
            onClick={() => setShowReasoning((v) => !v)}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            {showReasoning ? "▾ Hide reasoning" : "▸ Show reasoning"}
          </button>
          {showReasoning && (
            <p className="text-xs text-gray-500 italic mt-1">{finding.validation_reasoning}</p>
          )}
        </div>
      )}

      {finding.remediation && (
        <p className="text-xs text-gray-500">
          <span className="font-medium">Fix:</span> {finding.remediation}
        </p>
      )}

      {canAct && (
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={() => handlePatch("confirmed")}
            disabled={!!patching || revalidating || finding.status === "confirmed"}
            className="text-xs px-2 py-1 rounded bg-green-50 text-green-700 hover:bg-green-100 disabled:opacity-40 font-medium"
          >
            ✓ Confirm
          </button>
          <button
            onClick={() => handlePatch("false_positive")}
            disabled={!!patching || revalidating}
            className="text-xs px-2 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100 disabled:opacity-40 font-medium"
          >
            ✗ False Positive
          </button>
          <button
            onClick={handleRevalidate}
            disabled={revalidating || !!patching}
            className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 font-medium"
          >
            {revalidating ? "↻ Validating…" : "↻ Re-validate"}
          </button>
        </div>
      )}
    </div>
  );
}

export default function AgentScansPage() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [selectedTarget, setSelectedTarget] = useState("");
  const [scanType, setScanType] = useState<"web" | "api" | "network">("web");
  const [activeScan, setActiveScan] = useState<AgentScan | null>(null);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [findings, setFindings] = useState<AgentFinding[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listTargets().then(setTargets).catch(() => setTargets([]));
  }, []);

  useEffect(() => {
    listAgentScans()
      .then((scans) => {
        if (scans.length > 0 && !activeScan) {
          const latest = scans[0];
          setActiveScan(latest);
          if (latest.status === "completed") loadFindings(latest.id);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  useEffect(() => {
    if (activeScan?.status === "completed" && findings.length === 0) {
      loadFindings(activeScan.id);
    }
  }, [activeScan?.status]);

  async function startScan() {
    if (!selectedTarget) { setError("Select a target first"); return; }
    const target = targets.find((t) => t.id === selectedTarget);
    if (!target) return;

    setError(null);
    setLoading(true);
    setEvents([]);
    setFindings([]);

    try {
      const scan = await createAgentScan({
        target_id: selectedTarget,
        target_url: target.url,
        target_type: scanType,
      });
      setActiveScan(scan);
      openWebSocket(scan.id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start scan");
    } finally {
      setLoading(false);
    }
  }

  function openWebSocket(scanId: string) {
    wsRef.current?.close();
    const ws = connectAgentScanWS(scanId, (event) => {
      if ("node" in event && event.node === "system") {
        setActiveScan((prev) => prev ? { ...prev, status: event.status } : prev);
        if (event.status === "completed") loadFindings(scanId);
        ws.close();
        return;
      }
      setEvents((prev) => [...prev, event as ProgressEvent]);
    });
    ws.onclose = () => pollUntilDone(scanId);
    wsRef.current = ws;
  }

  async function pollUntilDone(scanId: string) {
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 3000));
      try {
        const scan = await getAgentScan(scanId);
        setActiveScan(scan);
        if (scan.status === "completed") { loadFindings(scanId); return; }
        if (scan.status === "failed") return;
      } catch { return; }
    }
  }

  async function loadFindings(scanId: string) {
    try {
      const res = await getAgentScanFindings(scanId);
      setFindings(res.findings);
    } catch { /* non-critical */ }
  }

  function updateFinding(updated: AgentFinding) {
    setFindings((prev) => prev.map((f) => f.id === updated.id ? updated : f));
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">AI Agent Scans</h1>

      {/* Launcher */}
      <div className="bg-white border rounded-lg p-5 space-y-4">
        <h2 className="font-semibold text-lg">New Agent Scan</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Target</label>
            <select
              className="w-full border rounded px-3 py-2 text-sm"
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
            >
              <option value="">Select a target…</option>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} — {t.url}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Scan Type</label>
            <select
              className="w-full border rounded px-3 py-2 text-sm"
              value={scanType}
              onChange={(e) => setScanType(e.target.value as typeof scanType)}
            >
              <option value="web">Web App</option>
              <option value="api">API</option>
              <option value="network">Network</option>
            </select>
          </div>
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          onClick={startScan}
          disabled={loading || !selectedTarget}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Starting…" : "Launch Agent Scan"}
        </button>
      </div>

      {/* Active scan status */}
      {activeScan && (
        <div className="bg-white border rounded-lg p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">Scan Progress</h2>
            <span className={`text-sm font-medium ${STATUS_COLOR[activeScan.status] ?? ""}`}>
              {activeScan.status.toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-gray-400 font-mono">{activeScan.id}</p>

          <div className="bg-gray-950 rounded p-3 h-48 overflow-y-auto font-mono text-xs space-y-1">
            {events.length === 0 && (
              <p className="text-gray-500">Waiting for events…</p>
            )}
            {events.map((ev, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-gray-500 shrink-0">
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
                <span className={ev.status === "completed" ? "text-green-400" : ev.status === "failed" ? "text-red-400" : "text-blue-300"}>
                  [{ev.node}]
                </span>
                <span className="text-gray-200">{ev.message}</span>
              </div>
            ))}
            <div ref={eventsEndRef} />
          </div>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <div className="bg-white border rounded-lg p-5 space-y-3">
          <h2 className="font-semibold text-lg">
            Findings <span className="text-gray-400 font-normal">({findings.length})</span>
          </h2>
          <div className="space-y-2">
            {findings.map((f) => (
              <FindingCard key={f.id} finding={f} onUpdate={updateFinding} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
