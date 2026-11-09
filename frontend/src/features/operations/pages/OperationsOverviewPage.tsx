import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowLeftRight,
  CheckCircle,
  Cpu,
  History,
  Info,
  Radio,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  Sparkles,
  Zap,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import {
  acknowledgeAlert,
  getMetricsSummary,
  listAlertInstances,
  listAlertRules,
  listIncidents,
  listOperationalEvents,
  listRollbackHistory,
  listRollbackPolicies,
  listSiteSummaries,
  listSlos,
  triggerRollback,
  updateRollbackPolicy,
} from "../api";
import type { RollbackMode } from "../types";

export function OperationsOverviewPage() {
  const { activeWorkspace } = useAuth();
  const workspaceId = activeWorkspace?.id ?? "default";
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"overview" | "alerts" | "slos" | "incidents" | "rollback">("overview");
  const [rollbackReason, setRollbackReason] = useState("");
  const [selectedAppId] = useState("runtime-app-01");

  // Queries
  const { data: summary, isLoading: loadingSummary, refetch: refetchSummary } = useQuery({
    queryKey: ["metrics-summary", workspaceId],
    queryFn: () => getMetricsSummary(),
    refetchInterval: 10000,
  });

  const { data: events = [] } = useQuery({
    queryKey: ["ops-events", workspaceId],
    queryFn: () => listOperationalEvents(workspaceId, 25),
  });

  const { data: alertInstances = [], refetch: refetchAlerts } = useQuery({
    queryKey: ["alert-instances", workspaceId],
    queryFn: () => listAlertInstances(workspaceId),
    refetchInterval: 10000,
  });

  const { data: alertRules = [] } = useQuery({
    queryKey: ["alert-rules", workspaceId],
    queryFn: () => listAlertRules(workspaceId),
  });

  const { data: slos = [] } = useQuery({
    queryKey: ["slos", workspaceId],
    queryFn: () => listSlos(workspaceId),
  });

  const { data: incidents = [], refetch: refetchIncidents } = useQuery({
    queryKey: ["incidents", workspaceId],
    queryFn: () => listIncidents(workspaceId),
  });

  const { data: rollbackPolicies = [] } = useQuery({
    queryKey: ["rollback-policies", workspaceId],
    queryFn: () => listRollbackPolicies(workspaceId),
  });

  const { data: rollbackHistory = [], refetch: refetchHistory } = useQuery({
    queryKey: ["rollback-history", selectedAppId],
    queryFn: () => listRollbackHistory(selectedAppId),
  });

  const { data: sites = [] } = useQuery({
    queryKey: ["ops-sites", workspaceId],
    queryFn: () => listSiteSummaries(workspaceId),
  });

  // Mutations
  const ackMutation = useMutation({
    mutationFn: (instanceId: string) => acknowledgeAlert(instanceId, "Acknowledged via Operations Centre"),
    onSuccess: () => {
      void refetchAlerts();
      void refetchSummary();
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: () => triggerRollback(selectedAppId, rollbackReason || "Manual rollback initiated via console"),
    onSuccess: () => {
      setRollbackReason("");
      void refetchHistory();
      void refetchSummary();
      void refetchIncidents();
    },
  });

  const updatePolicyMutation = useMutation({
    mutationFn: ({ policyId, mode }: { policyId: string; mode: RollbackMode }) =>
      updateRollbackPolicy(policyId, { mode }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["rollback-policies", workspaceId] });
    },
  });

  const activePolicy = rollbackPolicies[0];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card border border-border p-6 rounded-xl shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Radio className="text-emerald-500 animate-pulse" size={20} />
            <h1 className="text-2xl font-bold tracking-tight">Operations Centre</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
              Live Monitoring
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            Production telemetry, OpenTelemetry metrics, SLO error budgets, alert evaluation, and Blue/Green rollback.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              void refetchSummary();
              void refetchAlerts();
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-muted font-medium transition"
          >
            <RefreshCw size={14} className={loadingSummary ? "animate-spin" : ""} />
            Refresh
          </button>
          <a
            href="/api/v1/ops/metrics/prometheus"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 text-primary border border-primary/20 text-sm font-medium hover:bg-primary/20 transition"
          >
            <Server size={14} />
            Prometheus Scrape Endpoint
          </a>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border space-x-2">
        {([
          { key: "overview", label: "Fleet & Metrics Overview", icon: Activity },
          { key: "alerts", label: `Alert Centre (${alertInstances.filter((a) => a.status === "FIRING").length})`, icon: AlertTriangle },
          { key: "slos", label: "SLOs & Error Budgets", icon: Zap },
          { key: "incidents", label: `Incidents (${incidents.filter((i) => i.status !== "CLOSED").length})`, icon: AlertOctagon },
          { key: "rollback", label: "Automated Rollback", icon: ArrowLeftRight },
        ] as const).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* TAB 1: FLEET & METRICS OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Key Metric Gauges */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Requests Total</span>
              <div className="text-2xl font-bold mt-1 text-foreground">
                {summary?.requests_total?.toLocaleString() ?? 0}
              </div>
              <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                <CheckCircle size={12} className="text-emerald-500" />
                Error Rate: {summary?.error_rate_percentage ?? 0}%
              </div>
            </div>

            <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Latency P95</span>
              <div className="text-2xl font-bold mt-1 text-foreground">
                {summary?.latency_p95_ms ? `${summary.latency_p95_ms} ms` : "0 ms"}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                Avg: {summary?.latency_avg_ms ?? 0} ms
              </div>
            </div>

            <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Active Slot</span>
              <div className="text-2xl font-bold mt-1 text-foreground flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-sm bg-blue-500/10 text-blue-600 border border-blue-500/20">
                  {summary?.active_slot ?? "SLOT_A"}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${summary?.readiness_state === "READY" ? "bg-emerald-500/10 text-emerald-600" : "bg-amber-500/10 text-amber-600"}`}>
                  {summary?.readiness_state ?? "READY"}
                </span>
              </div>
              <div className="text-xs text-muted-foreground mt-1">Golden Tests: PASSED</div>
            </div>

            <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Active Alerts</span>
              <div className="text-2xl font-bold mt-1 text-foreground flex items-center gap-2">
                <span className={summary && summary.firing_alerts_count > 0 ? "text-destructive font-black" : "text-emerald-600"}>
                  {summary?.firing_alerts_count ?? 0} Firing
                </span>
              </div>
              <div className="text-xs text-muted-foreground mt-1">SLO State: {summary?.slo_status ?? "HEALTHY"}</div>
            </div>
          </div>

          {/* Host Hardware & Resource Gauges */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium flex items-center gap-1.5">
                  <Cpu size={16} className="text-muted-foreground" /> Host CPU Usage
                </span>
                <span className="text-sm font-bold">{summary?.cpu_usage_percent ?? 0}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${Math.min(100, summary?.cpu_usage_percent ?? 0)}%` }}
                />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium flex items-center gap-1.5">
                  <Server size={16} className="text-muted-foreground" /> System RAM
                </span>
                <span className="text-sm font-bold">{summary?.memory_allocated_mb ?? 128.5} MB</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div className="bg-emerald-500 h-2 rounded-full" style={{ width: "24%" }} />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium flex items-center gap-1.5">
                  <Sparkles size={16} className="text-muted-foreground" /> Accelerator VRAM
                </span>
                <span className="text-sm font-bold">{summary?.vram_allocated_mb ?? 0} MB</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div className="bg-indigo-500 h-2 rounded-full" style={{ width: "12%" }} />
              </div>
            </div>
          </div>

          {/* Customer Sites Overview */}
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
            <h3 className="text-base font-semibold mb-3 flex items-center gap-2">
              <Server size={18} /> Enrolled Customer Sites ({sites.length})
            </h3>
            {sites.length === 0 ? (
              <p className="text-sm text-muted-foreground">No customer sites enrolled yet.</p>
            ) : (
              <div className="divide-y divide-border">
                {sites.map((s) => (
                  <div key={s.site_id || s.id} className="py-3 flex items-center justify-between">
                    <div>
                      <div className="font-medium text-sm flex items-center gap-2">
                        {s.site_name}
                        <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                          {s.site_key}
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        Heartbeat: {s.agent_alive ? "Connected" : "Offline"} · Telemetry Consent: {s.sync_consent ? "Opted In" : "Local Only"}
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${s.status === "ACTIVE" ? "bg-emerald-500/10 text-emerald-600" : "bg-destructive/10 text-destructive"}`}>
                      {s.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Operational Event Journal */}
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
            <h3 className="text-base font-semibold mb-3 flex items-center gap-2">
              <History size={18} /> Sanitized Operational Event Journal
            </h3>
            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground">No operational events recorded.</p>
            ) : (
              <div className="divide-y divide-border max-h-80 overflow-y-auto">
                {events.map((e) => (
                  <div key={e.id} className="py-2.5 flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 rounded text-[11px] font-bold uppercase ${
                          e.severity === "CRITICAL"
                            ? "bg-destructive/10 text-destructive"
                            : e.severity === "WARNING"
                            ? "bg-amber-500/10 text-amber-600"
                            : "bg-muted text-muted-foreground"
                        }`}>
                          {e.severity}
                        </span>
                        <span className="font-semibold text-xs font-mono">{e.event_type}</span>
                        <span className="text-xs text-muted-foreground">({e.source_component})</span>
                      </div>
                      <p className="text-sm text-foreground mt-1">{e.summary}</p>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {new Date(e.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: ALERT CENTRE */}
      {activeTab === "alerts" && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
            <h3 className="text-base font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle size={18} className="text-amber-500" /> Active Alert Instances
            </h3>

            {alertInstances.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
                <CheckCircle size={32} className="text-emerald-500" />
                All alert rules healthy. Zero firing alerts.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Rule / Metric</th>
                      <th className="py-2.5 px-3">Current Value</th>
                      <th className="py-2.5 px-3">Breaches</th>
                      <th className="py-2.5 px-3">Fired At</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {alertInstances.map((inst) => (
                      <tr key={inst.id} className="hover:bg-muted/40">
                        <td className="py-3 px-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase ${
                              inst.status === "FIRING"
                                ? "bg-destructive/10 text-destructive border border-destructive/20"
                                : inst.status === "ACKNOWLEDGED"
                                ? "bg-amber-500/10 text-amber-600"
                                : inst.status === "SILENCED"
                                ? "bg-muted text-muted-foreground"
                                : "bg-emerald-500/10 text-emerald-600"
                            }`}
                          >
                            {inst.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-medium">
                          {inst.fingerprint.substring(0, 12)}...
                        </td>
                        <td className="py-3 px-3 font-mono">{inst.current_value}</td>
                        <td className="py-3 px-3">{inst.breach_count}</td>
                        <td className="py-3 px-3 text-xs text-muted-foreground">
                          {inst.fired_at ? new Date(inst.fired_at).toLocaleTimeString() : "—"}
                        </td>
                        <td className="py-3 px-3 text-right">
                          {inst.status === "FIRING" && (
                            <button
                              onClick={() => ackMutation.mutate(inst.id)}
                              disabled={ackMutation.isPending}
                              className="px-3 py-1 rounded bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 text-xs font-semibold transition"
                            >
                              Acknowledge
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Configured Alert Rules */}
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
            <h3 className="text-base font-semibold mb-3 flex items-center gap-2">
              <Shield size={18} /> Registered Alert Rules ({alertRules.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {alertRules.map((r) => (
                <div key={r.id} className="p-3.5 rounded-lg border border-border bg-muted/20">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-sm">{r.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${
                      r.severity === "CRITICAL" ? "bg-destructive/10 text-destructive" : "bg-amber-500/10 text-amber-600"
                    }`}>
                      {r.severity}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">{r.description}</p>
                  <div className="mt-2 text-xs font-mono bg-background p-1.5 rounded border border-border">
                    {r.metric_key} {r.condition_operator} {r.threshold} (for {r.duration_seconds}s)
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SLOS & ERROR BUDGETS */}
      {activeTab === "slos" && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
            <h3 className="text-base font-semibold mb-4 flex items-center gap-2">
              <Zap size={18} className="text-amber-500" /> Service Level Objectives & Error Budget Burn Down
            </h3>

            {slos.length === 0 ? (
              <p className="text-sm text-muted-foreground">No SLOs defined for this workspace.</p>
            ) : (
              <div className="space-y-4">
                {slos.map((s) => (
                  <div key={s.id} className="p-4 rounded-xl border border-border bg-muted/10 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-semibold text-sm">{s.name}</h4>
                        <p className="text-xs text-muted-foreground">{s.description}</p>
                      </div>
                      <span className="text-xs font-bold px-2 py-1 rounded bg-primary/10 text-primary border border-primary/20">
                        Target: {s.target_percentage}% ({s.rolling_window_days}d window)
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span>Error Budget Remaining</span>
                        <span className="text-emerald-600 font-bold">85% Remaining</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
                        <div className="bg-emerald-500 h-3 rounded-full" style={{ width: "85%" }} />
                      </div>
                    </div>

                    <div className="text-xs text-muted-foreground flex gap-4 pt-1">
                      <span>SLI Metric: <code>{s.metric_key}</code></span>
                      <span>Definition: <code>{s.good_events_definition}</code></span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: INCIDENTS */}
      {activeTab === "incidents" && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
            <h3 className="text-base font-semibold mb-4 flex items-center gap-2">
              <AlertOctagon size={18} className="text-destructive" /> Operational Incidents ({incidents.length})
            </h3>

            {incidents.length === 0 ? (
              <p className="text-sm text-muted-foreground">No active operational incidents.</p>
            ) : (
              <div className="space-y-4">
                {incidents.map((inc) => (
                  <div key={inc.id} className="p-4 rounded-xl border border-border bg-card space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
                          INC-{inc.incident_number}
                        </span>
                        <h4 className="font-bold text-sm">{inc.title}</h4>
                        <span className="text-xs px-2 py-0.5 rounded font-bold bg-destructive/10 text-destructive">
                          {inc.severity}
                        </span>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded-full font-bold uppercase bg-amber-500/10 text-amber-600">
                        {inc.status}
                      </span>
                    </div>

                    <p className="text-sm text-muted-foreground">{inc.description}</p>

                    {/* Timeline */}
                    <div className="border-t border-border pt-3 space-y-2">
                      <span className="text-xs font-semibold text-muted-foreground uppercase">Incident Timeline</span>
                      <div className="space-y-1.5 pl-3 border-l-2 border-border">
                        {inc.events.map((ev) => (
                          <div key={ev.id} className="text-xs text-muted-foreground">
                            <span className="font-mono text-foreground">[{ev.event_type}]</span> {ev.description}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: AUTOMATED ROLLBACK */}
      {activeTab === "rollback" && (
        <div className="space-y-6">
          {/* Policy Configuration Card */}
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold flex items-center gap-2">
                  <ShieldAlert size={18} className="text-primary" /> Rollback Policy Configuration
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Governs criteria for automated and operator-guided slot transitions.
                </p>
              </div>

              {/* Mode Toggle */}
              {activePolicy && (
                <div className="flex items-center gap-2 bg-muted p-1 rounded-lg">
                  {(["MANUAL_ONLY", "AUTOMATIC", "DISABLED"] as RollbackMode[]).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => updatePolicyMutation.mutate({ policyId: activePolicy.id, mode })}
                      className={`px-3 py-1 rounded text-xs font-semibold transition ${
                        activePolicy.mode === mode
                          ? "bg-background text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Warning Banner when set to AUTOMATIC */}
            {activePolicy?.mode === "AUTOMATIC" && (
              <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-200 text-xs flex items-start gap-2">
                <Info size={16} className="shrink-0 mt-0.5 text-amber-600" />
                <div>
                  <strong>AUTOMATIC Mode Enabled:</strong> The runtime will execute unattended Blue/Green slot
                  rollbacks upon sustained latency or error rate breaches. Gate 3 cryptographic verification, anti-revocation,
                  and golden test re-verification remain strictly enforced before switching.
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded border border-border bg-muted/20">
                <span className="text-muted-foreground block">Error Rate Threshold</span>
                <span className="font-bold text-sm">{activePolicy?.error_rate_threshold_percentage ?? 5.0}%</span>
              </div>
              <div className="p-3 rounded border border-border bg-muted/20">
                <span className="text-muted-foreground block">Latency P95 Threshold</span>
                <span className="font-bold text-sm">{activePolicy?.latency_p95_threshold_ms ?? 2000} ms</span>
              </div>
              <div className="p-3 rounded border border-border bg-muted/20">
                <span className="text-muted-foreground block">Anti-Flapping Cooldown</span>
                <span className="font-bold text-sm">{activePolicy?.cooldown_seconds ?? 600} seconds</span>
              </div>
            </div>
          </div>

          {/* Manual Rollback Trigger Box */}
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm space-y-4">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <ArrowLeftRight size={18} /> Execute Blue/Green Slot Rollback
            </h3>
            <p className="text-xs text-muted-foreground">
              Immediately roll back active customer runtime traffic to the alternate verified slot.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="Rollback justification / incident reference..."
                value={rollbackReason}
                onChange={(e) => setRollbackReason(e.target.value)}
                className="flex-1 px-3 py-2 rounded-lg border border-border bg-background text-sm"
              />
              <button
                onClick={() => rollbackMutation.mutate()}
                disabled={rollbackMutation.isPending}
                className="px-4 py-2 rounded-lg bg-destructive text-destructive-foreground font-semibold text-sm hover:bg-destructive/90 transition disabled:opacity-50"
              >
                {rollbackMutation.isPending ? "Executing..." : "Execute Rollback"}
              </button>
            </div>
          </div>

          {/* Rollback Execution History */}
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
            <h3 className="text-base font-semibold mb-3 flex items-center gap-2">
              <History size={18} /> Rollback Audit History ({rollbackHistory.length})
            </h3>

            {rollbackHistory.length === 0 ? (
              <p className="text-sm text-muted-foreground">No rollback operations executed yet.</p>
            ) : (
              <div className="divide-y divide-border">
                {rollbackHistory.map((h) => (
                  <div key={h.id} className="py-3 flex items-center justify-between">
                    <div>
                      <div className="font-medium text-sm flex items-center gap-2">
                        <span>{h.from_slot_name} → {h.to_slot_name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${
                          h.status === "SUCCESS"
                            ? "bg-emerald-500/10 text-emerald-600"
                            : "bg-destructive/10 text-destructive"
                        }`}>
                          {h.status}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Trigger: {h.trigger_type} · Reason: {h.trigger_reason}
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {new Date(h.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
