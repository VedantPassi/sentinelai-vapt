"use client";

import { useEffect, useState } from "react";
import {
  Schedule,
  ScheduleCreate,
  createSchedule,
  deleteSchedule,
  listSchedules,
  listTargets,
  Target,
  toggleSchedule,
} from "@/lib/api";
import { useUser } from "@/contexts/UserContext";

const SCAN_TYPES = ["web", "api", "network", "container", "cloud", "ad"];

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function fmtInterval(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours === 24) return "24h (daily)";
  if (hours === 168) return "7d (weekly)";
  return `${hours}h`;
}

export default function SchedulesPage() {
  const { user } = useUser();
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // form state
  const [targetId, setTargetId] = useState("");
  const [scanType, setScanType] = useState("web");
  const [intervalHours, setIntervalHours] = useState(24);
  const [creating, setCreating] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [s, t] = await Promise.all([listSchedules(), listTargets()]);
      setSchedules(s);
      setTargets(t);
      if (t.length > 0 && !targetId) setTargetId(t[0].id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate() {
    if (!targetId) return;
    setCreating(true);
    setError(null);
    try {
      const payload: ScheduleCreate = { target_id: targetId, scan_type: scanType, interval_hours: intervalHours };
      await createSchedule(payload);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  async function handleToggle(s: Schedule) {
    try {
      await toggleSchedule(s.id, !s.is_active);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Toggle failed");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this schedule?")) return;
    try {
      await deleteSchedule(id);
      setSchedules((prev) => prev.filter((s) => s.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Continuous Monitoring</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Schedule recurring scans — Beat worker re-runs them automatically every interval.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Create form */}
      <div className="rounded-lg border border-border bg-card p-5 space-y-4">
        <h2 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground">New Schedule</h2>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Target</label>
            <select
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm min-w-[180px]"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
            >
              {targets.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Scan Type</label>
            <select
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              value={scanType}
              onChange={(e) => setScanType(e.target.value)}
            >
              {SCAN_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Interval (hours)</label>
            <input
              type="number"
              min={0.5}
              max={8760}
              step={0.5}
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm w-28"
              value={intervalHours}
              onChange={(e) => setIntervalHours(Number(e.target.value))}
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !targetId}
            className="rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {creating ? "Creating…" : "Create"}
          </button>
        </div>
      </div>

      {/* Schedule list */}
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : schedules.length === 0 ? (
        <p className="text-sm text-muted-foreground">No schedules yet.</p>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground uppercase text-xs">
              <tr>
                <th className="px-4 py-2 text-left">Target</th>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Interval</th>
                <th className="px-4 py-2 text-left">Last Run</th>
                <th className="px-4 py-2 text-left">Next Run</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => {
                const target = targets.find((t) => t.id === s.target_id);
                return (
                  <tr key={s.id} className="border-t border-border hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 font-medium">{target?.name ?? s.target_id.slice(0, 8)}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-primary/10 text-primary px-2 py-0.5 text-xs font-mono">
                        {s.scan_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{fmtInterval(s.interval_hours)}</td>
                    <td className="px-4 py-3 text-muted-foreground">{fmtDate(s.last_run_at)}</td>
                    <td className="px-4 py-3 text-muted-foreground">{fmtDate(s.next_run_at)}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          s.is_active
                            ? "bg-green-500/10 text-green-600"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {s.is_active ? "Active" : "Paused"}
                      </span>
                    </td>
                    <td className="px-4 py-3 flex gap-2">
                      <button
                        onClick={() => handleToggle(s)}
                        className="text-xs rounded-md border border-border px-2 py-1 hover:bg-muted transition-colors"
                      >
                        {s.is_active ? "Pause" : "Resume"}
                      </button>
                      <button
                        onClick={() => handleDelete(s.id)}
                        className="text-xs rounded-md border border-destructive/40 px-2 py-1 text-destructive hover:bg-destructive/10 transition-colors"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
