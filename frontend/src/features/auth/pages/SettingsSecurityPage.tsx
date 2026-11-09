import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Laptop, LogOut, Trash2 } from "lucide-react";
import { apiGet, apiDelete } from "../../../lib/api/client";
import { useAuth } from "../AuthContext";
import type { SessionInfo } from "../types";

export function SettingsSecurityPage() {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();

  const sessionsQuery = useQuery({
    queryKey: ["auth-sessions"],
    queryFn: () => apiGet<SessionInfo[]>("/auth/sessions"),
  });

  const revokeMutation = useMutation({
    mutationFn: (sessionId: string) => apiDelete(`/auth/sessions/${sessionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth-sessions"] });
    },
  });

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2>Account Security & Sessions</h2>
          <p>Review your active sessions and credentials for <strong>{user?.email}</strong></p>
        </div>
      </div>

      <section className="panel mt-6">
        <div className="panel-header">
          <h3>Active Sessions</h3>
          <span className="badge">{sessionsQuery.data?.length ?? 0}</span>
        </div>

        <div className="divide-y divide-border">
          {sessionsQuery.data?.map((s) => (
            <div key={s.id} className="py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-muted rounded-md text-foreground">
                  <Laptop size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Web Browser Session</strong>
                    {s.is_current && <span className="badge-subtle">Current Device</span>}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Last active: {new Date(s.last_activity_at).toLocaleString()} · Expires:{" "}
                    {new Date(s.expires_at).toLocaleDateString()}
                  </div>
                </div>
              </div>

              {!s.is_current && (
                <button
                  onClick={() => revokeMutation.mutate(s.id)}
                  disabled={revokeMutation.isPending}
                  className="btn-destructive-ghost text-xs"
                >
                  <Trash2 size={14} className="mr-1 inline" />
                  Revoke
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="panel mt-6 border-red-500/20">
        <div className="panel-header">
          <h3 className="text-destructive">Session Termination</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          End your current session and sign out of Mizan on this computer.
        </p>
        <button onClick={() => void logout()} className="btn-secondary text-destructive">
          <LogOut size={16} className="mr-1 inline" />
          Sign out of Mizan
        </button>
      </section>
    </div>
  );
}
