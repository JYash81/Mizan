import { useState, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Mail, Shield, Trash2, UserPlus, Users } from "lucide-react";
import { apiGet, apiPost, apiDelete, ApiError } from "../../../lib/api/client";
import { useAuth } from "../../auth/AuthContext";
import type { InvitationItem, OrganizationMember } from "../../auth/types";

export function TeamManagementPage() {
  const { activeOrganization, user } = useAuth();
  const queryClient = useQueryClient();

  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");
  const [inviteError, setInviteError] = useState<string | null>(null);

  const orgId = activeOrganization?.id;

  // 1. Fetch Members
  const membersQuery = useQuery({
    queryKey: ["org-members", orgId],
    queryFn: () => apiGet<OrganizationMember[]>(`/organizations/${orgId}/members`),
    enabled: !!orgId,
  });

  // 2. Fetch Invitations
  const invitationsQuery = useQuery({
    queryKey: ["org-invitations", orgId],
    queryFn: () => apiGet<InvitationItem[]>(`/organizations/${orgId}/invitations`),
    enabled: !!orgId,
  });

  // 3. Create Invitation Mutation
  const inviteMutation = useMutation({
    mutationFn: (data: { email: string; organization_role: string }) =>
      apiPost(`/organizations/${orgId}/invitations`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-invitations", orgId] });
      setShowInviteModal(false);
      setInviteEmail("");
      setInviteError(null);
    },
    onError: (err: Error) => {
      setInviteError(err instanceof ApiError ? err.message : "Failed to issue invitation.");
    },
  });

  // 4. Revoke Invitation Mutation
  const revokeMutation = useMutation({
    mutationFn: (invitationId: string) => apiDelete(`/invitations/${invitationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-invitations", orgId] });
    },
  });

  // 5. Remove Member Mutation
  const removeMemberMutation = useMutation({
    mutationFn: (memberId: string) =>
      apiDelete(`/organizations/${orgId}/members/${memberId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-members", orgId] });
    },
  });

  const handleSendInvite = (e: FormEvent) => {
    e.preventDefault();
    setInviteError(null);
    inviteMutation.mutate({ email: inviteEmail, organization_role: inviteRole });
  };

  const isOwnerOrAdmin =
    activeOrganization?.role === "OWNER" || activeOrganization?.role === "ADMIN";

  if (!activeOrganization) {
    return (
      <div className="empty-panel">
        <Users size={32} className="text-muted-foreground" />
        <h3>No active organization</h3>
        <p>Please select or create an organization to manage team members.</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2>Team & Permissions</h2>
          <p>
            Manage users, permissions, and pending invitations for{" "}
            <strong>{activeOrganization.name}</strong>
          </p>
        </div>
        {isOwnerOrAdmin && (
          <button
            onClick={() => setShowInviteModal(true)}
            className="btn-primary inline-flex items-center gap-2"
          >
            <UserPlus size={16} />
            Invite Member
          </button>
        )}
      </div>

      {/* Members Section */}
      <section className="panel mt-6">
        <div className="panel-header">
          <h3>Active Members</h3>
          <span className="badge">
            {membersQuery.data?.length ?? 0} {membersQuery.data?.length === 1 ? "member" : "members"}
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Joined</th>
                {isOwnerOrAdmin && <th className="text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {membersQuery.data?.map((m) => {
                const isCurrentUser = m.user_id === user?.id;
                const isOwner = m.role === "OWNER";
                return (
                  <tr key={m.user_id}>
                    <td>
                      <div>
                        <strong>{m.full_name}</strong>
                        {isCurrentUser && <span className="badge-subtle ml-2">You</span>}
                        <div className="text-muted-foreground text-xs">{m.email}</div>
                      </div>
                    </td>
                    <td>
                      <span className={`role-badge ${m.role.toLowerCase()}`}>
                        <Shield size={12} className="inline mr-1" />
                        {m.role}
                      </span>
                    </td>
                    <td>
                      <span className="status-pill active">{m.membership_status}</span>
                    </td>
                    <td>{new Date(m.created_at).toLocaleDateString()}</td>
                    {isOwnerOrAdmin && (
                      <td className="text-right">
                        {!isCurrentUser && !isOwner && (
                          <button
                            onClick={() => {
                              if (confirm(`Remove ${m.full_name} from this organization?`)) {
                                removeMemberMutation.mutate(m.user_id);
                              }
                            }}
                            className="btn-destructive-ghost"
                            title="Remove member"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Pending Invitations Section */}
      <section className="panel mt-6">
        <div className="panel-header">
          <h3>Pending Invitations</h3>
          <span className="badge">{invitationsQuery.data?.length ?? 0}</span>
        </div>

        {invitationsQuery.data && invitationsQuery.data.length > 0 ? (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Invited Email</th>
                  <th>Assigned Role</th>
                  <th>Expires</th>
                  {isOwnerOrAdmin && <th className="text-right">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {invitationsQuery.data.map((inv) => (
                  <tr key={inv.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        <Mail size={16} className="text-muted-foreground" />
                        <span>{inv.invited_email}</span>
                      </div>
                    </td>
                    <td>
                      <span className="role-badge member">{inv.organization_role}</span>
                    </td>
                    <td>{new Date(inv.expires_at).toLocaleDateString()}</td>
                    {isOwnerOrAdmin && (
                      <td className="text-right">
                        <button
                          onClick={() => revokeMutation.mutate(inv.id)}
                          className="btn-destructive-ghost"
                          title="Revoke invitation"
                        >
                          Revoke
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted-foreground text-sm p-4 text-center">
            No pending invitations for this organization.
          </p>
        )}
      </section>

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Invite New Team Member</h3>
              <button onClick={() => setShowInviteModal(false)} className="close-btn">
                &times;
              </button>
            </div>

            {inviteError && <div className="alert-error mb-4">{inviteError}</div>}

            <form onSubmit={handleSendInvite}>
              <div className="form-group">
                <label htmlFor="invEmail">Work Email Address</label>
                <input
                  id="invEmail"
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="input-field"
                />
              </div>

              <div className="form-group">
                <label htmlFor="invRole">Organization Role</label>
                <select
                  id="invRole"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="input-field"
                >
                  <option value="MEMBER">Member (Standard access)</option>
                  <option value="ADMIN">Admin (Manage members & workspaces)</option>
                  <option value="VIEWER">Viewer (Read-only)</option>
                </select>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviteMutation.isPending}
                  className="btn-primary"
                >
                  {inviteMutation.isPending ? "Sending invite..." : "Send Invitation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
