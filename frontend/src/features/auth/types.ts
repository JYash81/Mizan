export interface UserProfile {
  id: string;
  full_name: string;
  email: string;
  status: string;
  email_verified_at: string | null;
  created_at: string;
}

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export interface WorkspaceSummary {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: string;
  role?: string | null;
}

export interface SessionInfo {
  id: string;
  created_at: string;
  last_activity_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface OrganizationMember {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  membership_status: string;
  created_at: string;
}

export interface InvitationItem {
  id: string;
  organization_id: string;
  workspace_id: string | null;
  invited_email: string;
  organization_role: string;
  workspace_role: string | null;
  status: string;
  expires_at: string;
  created_at: string;
}
