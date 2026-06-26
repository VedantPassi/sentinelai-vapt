export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight mb-1">Overview</h1>
      <p className="text-sm text-muted-foreground mb-8">
        Your security posture at a glance.
      </p>
      <div className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">
        Scan data will appear here once Phase 2 scanning engine is complete.
      </div>
    </div>
  );
}
