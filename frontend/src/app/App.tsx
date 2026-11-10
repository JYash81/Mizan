import { useState, lazy, Suspense, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Archive,
  ArrowRight,
  Award,
  Bell,
  Boxes,
  Check,
  ChevronDown,
  Cpu,
  Database,
  FlaskConical,
  FolderKanban,
  Hammer,
  LayoutDashboard,
  LogOut,
  PackageCheck,
  Plus,
  Radio,
  RefreshCw,
  Server,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import {
  Link,
  Navigate,
  NavLink,
  Route,
  BrowserRouter as Router,
  Routes,
  useNavigate,
} from "react-router-dom";

import { apiGet } from "../lib/api/client";
import { AuthProvider, useAuth } from "../features/auth/AuthContext";
import { ForgotPasswordPage } from "../features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "../features/auth/pages/LoginPage";
import { RegisterPage } from "../features/auth/pages/RegisterPage";
import { ResetPasswordPage } from "../features/auth/pages/ResetPasswordPage";
import { SettingsSecurityPage } from "../features/auth/pages/SettingsSecurityPage";
import { VerifyEmailPage } from "../features/auth/pages/VerifyEmailPage";
import { OnboardingPage } from "../features/workspaces/pages/OnboardingPage";
import { TeamManagementPage } from "../features/workspaces/pages/TeamManagementPage";
import { HomePage } from "../features/home/HomePage";

const WorkspacesPage = lazy(() =>
  import("../features/workspaces/pages/WorkspacesPage").then((m) => ({ default: m.WorkspacesPage }))
);

const DatasetsPage = lazy(() =>
  import("../features/datasets/pages/DatasetsPage").then((m) => ({ default: m.DatasetsPage }))
);
const DatasetDetailPage = lazy(() =>
  import("../features/datasets/pages/DatasetDetailPage").then((m) => ({ default: m.DatasetDetailPage }))
);
const DataProtectionOverviewPage = lazy(() =>
  import("../features/data-protection/pages/DataProtectionOverviewPage").then((m) => ({
    default: m.DataProtectionOverviewPage,
  }))
);
const MaskingReviewPage = lazy(() =>
  import("../features/data-protection/pages/MaskingReviewPage").then((m) => ({
    default: m.MaskingReviewPage,
  }))
);
const RAGPlaygroundPage = lazy(() =>
  import("../features/rag/pages/RAGPlaygroundPage").then((m) => ({ default: m.RAGPlaygroundPage }))
);
const EvaluationOverviewPage = lazy(() =>
  import("../features/evaluation/pages/EvaluationOverviewPage").then((m) => ({
    default: m.EvaluationOverviewPage,
  }))
);
const EvaluationSuiteDetailPage = lazy(() =>
  import("../features/evaluation/pages/EvaluationSuiteDetailPage").then((m) => ({
    default: m.EvaluationSuiteDetailPage,
  }))
);
const EvaluationRunPage = lazy(() =>
  import("../features/evaluation/pages/EvaluationRunPage").then((m) => ({
    default: m.EvaluationRunPage,
  }))
);
const ExperimentListPage = lazy(() =>
  import("../features/experiments/pages/ExperimentListPage").then((m) => ({
    default: m.ExperimentListPage,
  }))
);
const ExperimentWizardPage = lazy(() =>
  import("../features/experiments/pages/ExperimentWizardPage").then((m) => ({
    default: m.ExperimentWizardPage,
  }))
);
const ExperimentDetailPage = lazy(() =>
  import("../features/experiments/pages/ExperimentDetailPage").then((m) => ({
    default: m.ExperimentDetailPage,
  }))
);
const ExperimentComparisonPage = lazy(() =>
  import("../features/experiments/pages/ExperimentComparisonPage").then((m) => ({
    default: m.ExperimentComparisonPage,
  }))
);
const HardwareCentrePage = lazy(() =>
  import("../features/hardware/pages/HardwareCentrePage").then((m) => ({
    default: m.HardwareCentrePage,
  }))
);
const RecommendationOverviewPage = lazy(() =>
  import("../features/recommendations/pages/RecommendationOverviewPage").then((m) => ({
    default: m.RecommendationOverviewPage,
  }))
);
const RecommendationDetailPage = lazy(() =>
  import("../features/recommendations/pages/RecommendationDetailPage").then((m) => ({
    default: m.RecommendationDetailPage,
  }))
);
const ModelBuildingOverviewPage = lazy(() =>
  import("../features/model-building/pages/ModelBuildingOverviewPage").then((m) => ({
    default: m.ModelBuildingOverviewPage,
  }))
);
const ModelBuildingDetailPage = lazy(() =>
  import("../features/model-building/pages/ModelBuildingDetailPage").then((m) => ({
    default: m.ModelBuildingDetailPage,
  }))
);
const ArtifactRegistryOverviewPage = lazy(() =>
  import("../features/artifact-registry/pages/ArtifactRegistryOverviewPage").then((m) => ({
    default: m.ArtifactRegistryOverviewPage,
  }))
);
const ModelVersionDetailPage = lazy(() =>
  import("../features/artifact-registry/pages/ModelVersionDetailPage").then((m) => ({
    default: m.ModelVersionDetailPage,
  }))
);
const ModelZooPage = lazy(() =>
  import("../features/zoo/pages/ModelZooPage").then((m) => ({ default: m.ModelZooPage }))
);
const ModelDetailPage = lazy(() =>
  import("../features/zoo/pages/ModelDetailPage").then((m) => ({ default: m.ModelDetailPage }))
);
const AppZooPage = lazy(() =>
  import("../features/zoo/pages/AppZooPage").then((m) => ({ default: m.AppZooPage }))
);
const AppDetailPage = lazy(() =>
  import("../features/zoo/pages/AppDetailPage").then((m) => ({ default: m.AppDetailPage }))
);
const CatalogManagePage = lazy(() =>
  import("../features/zoo/pages/CatalogManagePage").then((m) => ({ default: m.CatalogManagePage }))
);
const SitesPage = lazy(() =>
  import("../features/runtime/pages/SitesPage").then((m) => ({ default: m.SitesPage }))
);
const RuntimeDashboardPage = lazy(() =>
  import("../features/runtime/pages/RuntimeDashboardPage").then((m) => ({
    default: m.RuntimeDashboardPage,
  }))
);
const OperationsOverviewPage = lazy(() =>
  import("../features/operations/pages/OperationsOverviewPage").then((m) => ({
    default: m.OperationsOverviewPage,
  }))
);

type Version = { name: string; version: string; environment: string };

const nav = [
  { label: "Overview", path: "/dashboard", icon: LayoutDashboard },
  { label: "Team", path: "/team", icon: Users },
  { label: "Workspaces", path: "/workspaces", icon: FolderKanban },
  { label: "Datasets", path: "/datasets", icon: Database },
  { label: "Evaluation", path: "/evaluation", icon: Award },
  { label: "Experiments", path: "/experiments", icon: FlaskConical },
  { label: "Hardware & Cost", path: "/hardware", icon: Cpu },
  { label: "Approvals", path: "/approvals", icon: ShieldCheck },
  { label: "Recommendations", path: "/recommendations", icon: Sparkles },
  { label: "Model Building", path: "/model-building", icon: Hammer },
  { label: "Artifact Registry", path: "/artifact-registry", icon: Archive },
  { label: "Model Zoo", path: "/zoo/models", icon: PackageCheck },
  { label: "App Zoo", path: "/zoo/apps", icon: Boxes },
  { label: "Customer Sites", path: "/sites", icon: Server },
  { label: "Customer Runtime", path: "/runtime", icon: Activity },
  { label: "Operations Centre", path: "/operations", icon: Radio },
  { label: "Settings", path: "/settings", icon: Settings },
];

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, organizations, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="auth-container">
        <div className="text-center">
          <div className="auth-logo mx-auto animate-pulse">M</div>
          <p className="text-muted-foreground text-sm">Loading Mizan workspace...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (organizations.length === 0 && window.location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}

function Shell({ children }: { children: ReactNode }) {
  const {
    user,
    organizations,
    activeOrganization,
    workspaces,
    activeWorkspace,
    switchOrganization,
    switchWorkspace,
    logout,
  } = useAuth();

  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const navigate = useNavigate();

  const healthQuery = useQuery({
    queryKey: ["backend-health-ping"],
    queryFn: () => apiGet<{ status: string }>("/health"),
    refetchInterval: 30000,
    retry: 3,
  });

  const userInitials =
    user?.full_name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .substring(0, 2)
      .toUpperCase() ?? "MZ";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">M</span>
          <span>Mizan</span>
        </div>

        <nav aria-label="Main navigation" className="sidebar-scroll">
          {nav.map(({ label, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/dashboard"}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="account" onClick={() => setShowUserMenu(!showUserMenu)}>
          <span className="avatar">{userInitials}</span>
          <div>
            <strong>{user?.full_name ?? "User"}</strong>
            <small>{activeOrganization?.name ?? "No organization"}</small>
          </div>
          <ChevronDown size={16} />
        </div>
      </aside>

      <main className="flex-1 min-w-0 bg-slate-50">
        <header>
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-emerald-600 tracking-wider uppercase">
              {activeOrganization?.name ?? "ORGANIZATION"}
            </span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-base font-bold text-slate-900 tracking-tight">
                {activeWorkspace?.name ?? "Default Workspace"}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                ACTIVE
              </span>
              {healthQuery.isLoading ? (
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1 animate-pulse"
                  title="Connecting to cloud backend on Render.com..."
                >
                  <RefreshCw size={9} className="animate-spin text-amber-600" />
                  API CONNECTING
                </span>
              ) : healthQuery.isSuccess ? (
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1"
                  title="Cloud API backend is live and healthy"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  CLOUD API LIVE
                </span>
              ) : (
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1"
                  title="API service cold start in progress or network offline"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                  RECONNECTING
                </span>
              )}
            </div>
          </div>

          <div className="header-actions">
            {/* Workspace & Org Selector */}
            <div className="relative">
              <button
                className="workspace"
                onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
              >
                <FolderKanban size={15} className="text-emerald-600 shrink-0" />
                <span className="max-w-[160px] truncate">{activeWorkspace?.name ?? "Select workspace"}</span>
                <ChevronDown size={14} className="text-slate-400" />
              </button>

              {showWorkspaceMenu && (
                <div className="dropdown-menu">
                  <div className="px-3 py-1.5 text-xs font-semibold text-muted-foreground">
                    ORGANIZATIONS
                  </div>
                  {organizations.map((org) => (
                    <button
                      key={org.id}
                      className="dropdown-item"
                      onClick={() => {
                        void switchOrganization(org.id);
                        setShowWorkspaceMenu(false);
                      }}
                    >
                      <span className="flex-1 text-left">{org.name}</span>
                      {org.id === activeOrganization?.id && <Check size={14} className="text-emerald-600" />}
                    </button>
                  ))}

                  <div className="dropdown-divider" />
                  <div className="px-3 py-1.5 text-xs font-semibold text-muted-foreground">
                    WORKSPACES
                  </div>
                  {workspaces.map((ws) => (
                    <button
                      key={ws.id}
                      className="dropdown-item"
                      onClick={() => {
                        switchWorkspace(ws.id);
                        setShowWorkspaceMenu(false);
                      }}
                    >
                      <span className="flex-1 text-left">{ws.name}</span>
                      {ws.id === activeWorkspace?.id && <Check size={14} className="text-emerald-600" />}
                    </button>
                  ))}

                  <div className="dropdown-divider" />
                  <button
                    className="dropdown-item text-emerald-700 font-medium"
                    onClick={() => {
                      setShowWorkspaceMenu(false);
                      navigate("/onboarding");
                    }}
                  >
                    <Plus size={14} />
                    New Workspace / Org
                  </button>
                </div>
              )}
            </div>

            <button className="icon-button relative" aria-label="Notifications" title="No unread notifications">
              <Bell size={18} />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-white" />
            </button>

            {/* User Profile Menu */}
            <div className="relative">
              <button
                className="avatar cursor-pointer"
                onClick={() => setShowUserMenu(!showUserMenu)}
              >
                {userInitials}
              </button>

              {showUserMenu && (
                <div className="dropdown-menu">
                  <div className="px-3 py-2 border-b border-border">
                    <strong className="block text-sm">{user?.full_name}</strong>
                    <span className="text-xs text-muted-foreground">{user?.email}</span>
                  </div>
                  <NavLink
                    to="/team"
                    className="dropdown-item"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Users size={16} />
                    Team & Members
                  </NavLink>
                  <NavLink
                    to="/settings"
                    className="dropdown-item"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Settings size={16} />
                    Security & Sessions
                  </NavLink>
                  <div className="dropdown-divider" />
                  <button
                    className="dropdown-item text-destructive"
                    onClick={() => {
                      setShowUserMenu(false);
                      void logout();
                    }}
                  >
                    <LogOut size={16} />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <Suspense
          fallback={
            <div className="max-w-7xl mx-auto p-8 space-y-6 animate-pulse">
              <div className="h-8 bg-slate-200 rounded w-1/4" />
              <div className="h-4 bg-slate-200 rounded w-1/2" />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                <div className="h-32 bg-slate-200 rounded-xl" />
                <div className="h-32 bg-slate-200 rounded-xl" />
                <div className="h-32 bg-slate-200 rounded-xl" />
              </div>
            </div>
          }
        >
          {children}
        </Suspense>
      </main>
    </div>
  );
}

function Dashboard() {
  const version = useQuery({
    queryKey: ["version"],
    queryFn: () => apiGet<Version>("/version"),
  });
  const { activeWorkspace, activeOrganization } = useAuth();

  return (
    <Shell>
      <div className="page-container space-y-8 pb-16">
        <section className="hero">
        <div>
          <p className="eyebrow">
            {activeOrganization?.name ? `${activeOrganization.name} · ${activeWorkspace?.name ?? "WORKSPACE"}` : "ENTERPRISE PLATFORM"}
          </p>
          <h2>Governed AI Experimentation & Evaluation</h2>
          <p>
            Deterministic evaluation suites, automated PII masking, local and cloud model training, hardware pricing, and cryptographic release approvals.
          </p>
        </div>
        <div className="api-state">
          <span className={`status-dot ${version.isSuccess ? "online" : ""}`} />
          <div>
            <strong>{version.isSuccess ? "API Connected" : "Connecting..."}</strong>
            <small>
              {version.isSuccess
                ? `${version.data.name} ${version.data.version} · ${version.data.environment}`
                : "FastAPI Cloud Backend"}
            </small>
          </div>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <h2>Core Experimentation Pillars</h2>
          <p>End-to-end governed pipeline from raw business datasets to deployed AI artifacts.</p>
        </div>
      </section>

      <div className="overview-grid">
        <Foundation
          title="Workspaces & Governance"
          icon={<FolderKanban />}
          description="Isolated business scopes, role-based access control, and team permissions."
          state="Active & Governed"
          to="/workspaces"
        />
        <Foundation
          title="Business Datasets"
          icon={<Database />}
          description="Document ingestion, chunking, and automated Gate 1 PII masking verification."
          state="Data Plane Active"
          to="/datasets"
        />
        <Foundation
          title="Experimentation Lab"
          icon={<FlaskConical />}
          description="Design trial matrices, configure hyper-parameters, and evaluate models."
          state="Trials Active"
          to="/experiments"
        />
        <Foundation
          title="Model Evaluations"
          icon={<Award />}
          description="Deterministic multi-engine evaluation suites with automated pass/fail scoring."
          state="Multi-Engine Ready"
          to="/evaluation"
        />
        <Foundation
          title="Hardware & Cost Center"
          icon={<Cpu />}
          description="VRAM memory estimators, quantization benchmarks, and Gate 2 budget approvals."
          state="Deterministic Estimators"
          to="/hardware"
        />
        <Foundation
          title="Model & App Zoo"
          icon={<Boxes />}
          description="Approved model weights, adapters, and production app catalog with Gate 3 signing."
          state="Catalog Ready"
          to="/zoo/models"
        />
      </div>

      <section className="panel">
        <div>
          <h2>Three-Gate Governance Pipeline</h2>
          <p>
            Human oversight is enforced at critical boundaries before data is exposed, compute is provisioned, or releases are deployed.
          </p>
        </div>
        <ol className="gates">
          <li>
            <b>01</b>
            <span>
              <strong>Gate 1: Data Protection & Masking Approval</strong>
              <small>Ensures PII/PHI is masked and audited before documents enter training or evaluation.</small>
            </span>
          </li>
          <li>
            <b>02</b>
            <span>
              <strong>Gate 2: Hardware & Compute Spend Approval</strong>
              <small>Enforces financial budget limits and preflights resource requirements before cloud compute runs.</small>
            </span>
          </li>
          <li>
            <b>03</b>
            <span>
              <strong>Gate 3: Artifact Release & Cryptographic Signing</strong>
              <small>Ed25519 signs model weights, evaluation reports, and manifests before catalog publishing.</small>
            </span>
          </li>
        </ol>
      </section>
      </div>
    </Shell>
  );
}

function Foundation({
  title,
  description,
  state,
  icon,
  to,
}: {
  title: string;
  description: string;
  state: string;
  icon: ReactNode;
  to?: string;
}) {
  const card = (
    <article className="feature-card group cursor-pointer hover:border-emerald-500 hover:shadow-md transition-all">
      <div className="feature-icon group-hover:bg-emerald-100 transition-colors">{icon}</div>
      <h3 className="group-hover:text-emerald-700 transition-colors">{title}</h3>
      <p>{description}</p>
      <div className="mt-auto pt-3 flex items-center justify-between w-full">
        <span className="planned">{state}</span>
        {to && <ArrowRight size={14} className="text-slate-400 group-hover:text-emerald-600 group-hover:translate-x-1 transition-all" />}
      </div>
    </article>
  );

  return to ? (
    <Link to={to} className="no-underline text-inherit block">
      {card}
    </Link>
  ) : (
    card
  );
}

function FuturePage({ label }: { label: string }) {
  return (
    <Shell>
      <section className="empty">
        <div className="feature-icon">
          <Sparkles />
        </div>
        <p className="eyebrow">PLANNED MODULE</p>
        <h2>{label}</h2>
        <p>
          This area is intentionally not simulated. Its navigation, layout, and future boundary
          are ready for implementation.
        </p>
      </section>
    </Shell>
  );
}

export function App() {
  return (
    <Router>
      <AuthProvider>
        <Suspense
          fallback={
            <div className="min-h-screen bg-slate-50 flex items-center justify-center text-sm font-medium text-slate-600">
              <div className="text-center space-y-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white font-bold flex items-center justify-center mx-auto shadow-md animate-pulse">M</div>
                <p>Loading Mizan platform...</p>
              </div>
            </div>
          }
        >
          <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          {/* Public Marketing Homepage */}
          <Route path="/" element={<HomePage />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute>
                <OnboardingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/team"
            element={
              <ProtectedRoute>
                <Shell>
                  <TeamManagementPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces"
            element={
              <ProtectedRoute>
                <Shell>
                  <WorkspacesPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Shell>
                  <SettingsSecurityPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/datasets"
            element={
              <ProtectedRoute>
                <Shell>
                  <DatasetsPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/datasets/:datasetId"
            element={
              <ProtectedRoute>
                <Shell>
                  <DatasetDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/approvals"
            element={
              <ProtectedRoute>
                <Shell>
                  <DataProtectionOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/data-protection"
            element={
              <ProtectedRoute>
                <Shell>
                  <DataProtectionOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/data-protection/:runId"
            element={
              <ProtectedRoute>
                <Shell>
                  <MaskingReviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/experiments"
            element={
              <ProtectedRoute>
                <Shell>
                  <ExperimentListPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/experiments/new"
            element={
              <ProtectedRoute>
                <Shell>
                  <ExperimentWizardPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/experiments/:experimentId"
            element={
              <ProtectedRoute>
                <Shell>
                  <ExperimentDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/experiments/:experimentId/comparison"
            element={
              <ProtectedRoute>
                <Shell>
                  <ExperimentComparisonPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/hardware"
            element={
              <ProtectedRoute>
                <Shell>
                  <HardwareCentrePage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/rag"
            element={
              <ProtectedRoute>
                <Shell>
                  <RAGPlaygroundPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/evaluation"
            element={
              <ProtectedRoute>
                <Shell>
                  <EvaluationOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/evaluation/suites/:suiteId"
            element={
              <ProtectedRoute>
                <Shell>
                  <EvaluationSuiteDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/evaluation/runs/:runId"
            element={
              <ProtectedRoute>
                <Shell>
                  <EvaluationRunPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/recommendations"
            element={
              <ProtectedRoute>
                <Shell>
                  <RecommendationOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/recommendations/:runId"
            element={
              <ProtectedRoute>
                <Shell>
                  <RecommendationDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/model-building"
            element={
              <ProtectedRoute>
                <Shell>
                  <ModelBuildingOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/model-building/:runId"
            element={
              <ProtectedRoute>
                <Shell>
                  <ModelBuildingDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/model-building/:runId"
            element={
              <ProtectedRoute>
                <Shell>
                  <ModelBuildingDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/artifact-registry"
            element={
              <ProtectedRoute>
                <Shell>
                  <ArtifactRegistryOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/artifact-registry/:versionId"
            element={
              <ProtectedRoute>
                <Shell>
                  <ModelVersionDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/artifact-registry"
            element={
              <ProtectedRoute>
                <Shell>
                  <ArtifactRegistryOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/artifact-registry/:versionId"
            element={
              <ProtectedRoute>
                <Shell>
                  <ModelVersionDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />

          {/* Milestone 12: Model Zoo & App Zoo */}
          <Route
            path="/zoo/models"
            element={
              <ProtectedRoute>
                <Shell>
                  <ModelZooPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/model-zoo"
            element={<Navigate to="/zoo/models" replace />}
          />
          <Route
            path="/zoo/models/:listingId"
            element={
              <ProtectedRoute>
                <Shell>
                  <ModelDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/zoo/apps"
            element={
              <ProtectedRoute>
                <Shell>
                  <AppZooPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/zoo/apps/:listingId"
            element={
              <ProtectedRoute>
                <Shell>
                  <AppDetailPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/zoo/manage"
            element={
              <ProtectedRoute>
                <Shell>
                  <CatalogManagePage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/zoo/manage"
            element={
              <ProtectedRoute>
                <Shell>
                  <CatalogManagePage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/zoo/models"
            element={
              <ProtectedRoute>
                <Shell>
                  <ModelZooPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/zoo/apps"
            element={
              <ProtectedRoute>
                <Shell>
                  <AppZooPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/sites"
            element={
              <ProtectedRoute>
                <Shell>
                  <SitesPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/sites"
            element={
              <ProtectedRoute>
                <Shell>
                  <SitesPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/runtime"
            element={
              <ProtectedRoute>
                <Shell>
                  <RuntimeDashboardPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/runtime"
            element={
              <ProtectedRoute>
                <Shell>
                  <RuntimeDashboardPage />
                </Shell>
              </ProtectedRoute>
            }
          />

          {/* Milestone 14: Operations Centre */}
          <Route
            path="/operations"
            element={
              <ProtectedRoute>
                <Shell>
                  <OperationsOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspaces/:workspaceId/operations"
            element={
              <ProtectedRoute>
                <Shell>
                  <OperationsOverviewPage />
                </Shell>
              </ProtectedRoute>
            }
          />

          {/* Other feature tabs */}
          {nav
            .filter(
              (item) =>
                ![
                  "/",
                  "/dashboard",
                  "/team",
                  "/workspaces",
                  "/settings",
                  "/datasets",
                  "/approvals",
                  "/data-protection",
                  "/experiments",
                  "/rag",
                  "/evaluation",
                  "/recommendations",
                  "/model-building",
                  "/artifact-registry",
                  "/hardware",
                  "/zoo/models",
                  "/zoo/apps",
                  "/model-zoo",
                  "/sites",
                  "/runtime",
                  "/operations",
                ].includes(item.path)
            )
            .map((item) => (
              <Route
                key={item.path}
                path={item.path}
                element={
                  <ProtectedRoute>
                    <FuturePage label={item.label} />
                  </ProtectedRoute>
                }
              />
            ))}

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AuthProvider>
    </Router>
  );
}
