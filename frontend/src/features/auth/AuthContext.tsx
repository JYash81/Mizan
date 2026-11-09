import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, setCsrfToken, setSessionToken } from "../../lib/api/client";
import type { OrganizationSummary, UserProfile, WorkspaceSummary } from "./types";

interface AuthContextType {
  user: UserProfile | null;
  organizations: OrganizationSummary[];
  activeOrganization: OrganizationSummary | null;
  workspaces: WorkspaceSummary[];
  activeWorkspace: WorkspaceSummary | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  switchOrganization: (orgId: string) => Promise<void>;
  switchWorkspace: (wsId: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([]);
  const [activeOrganization, setActiveOrganization] = useState<OrganizationSummary | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const queryClient = useQueryClient();

  const loadWorkspacesForOrg = async (orgId: string) => {
    try {
      const data = await apiGet<WorkspaceSummary[]>(`/organizations/${orgId}/workspaces`);
      setWorkspaces(data);
      if (data.length > 0) {
        const savedWsId = localStorage.getItem(`mizan_active_ws_${orgId}`);
        const found = data.find((w) => w.id === savedWsId);
        setActiveWorkspace(found ?? data[0]);
      } else {
        setActiveWorkspace(null);
      }
    } catch {
      setWorkspaces([]);
      setActiveWorkspace(null);
    }
  };

  const refreshProfile = async () => {
    try {
      const data = await apiGet<{ user: UserProfile; organizations: OrganizationSummary[] }>("/auth/me");
      setUser(data.user);
      setOrganizations(data.organizations);

      if (data.organizations.length > 0) {
        const savedOrgId = localStorage.getItem("mizan_active_org");
        const foundOrg = data.organizations.find((o) => o.id === savedOrgId) ?? data.organizations[0];
        setActiveOrganization(foundOrg);
        await loadWorkspacesForOrg(foundOrg.id);
      } else {
        setActiveOrganization(null);
        setWorkspaces([]);
        setActiveWorkspace(null);
      }
    } catch {
      setUser(null);
      setOrganizations([]);
      setActiveOrganization(null);
      setWorkspaces([]);
      setActiveWorkspace(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (email: string, password: string) => {
    const res = await apiPost<{ user: UserProfile; csrf_token: string; session_token?: string }>("/auth/login", {
      email,
      password,
    });
    setCsrfToken(res.csrf_token);
    if (res.session_token) {
      setSessionToken(res.session_token);
    }
    await refreshProfile();
  };

  const logout = async () => {
    try {
      await apiPost("/auth/logout");
    } finally {
      setCsrfToken(null);
      setSessionToken(null);
      setUser(null);
      setOrganizations([]);
      setActiveOrganization(null);
      setWorkspaces([]);
      setActiveWorkspace(null);
      queryClient.clear();
    }
  };

  const switchOrganization = async (orgId: string) => {
    const org = organizations.find((o) => o.id === orgId);
    if (org) {
      setActiveOrganization(org);
      localStorage.setItem("mizan_active_org", org.id);
      queryClient.clear();
      await loadWorkspacesForOrg(org.id);
    }
  };

  const switchWorkspace = (wsId: string) => {
    const ws = workspaces.find((w) => w.id === wsId);
    if (ws && activeOrganization) {
      setActiveWorkspace(ws);
      localStorage.setItem(`mizan_active_ws_${activeOrganization.id}`, ws.id);
      queryClient.invalidateQueries();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        organizations,
        activeOrganization,
        workspaces,
        activeWorkspace,
        isLoading,
        login,
        logout,
        refreshProfile,
        switchOrganization,
        switchWorkspace,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
