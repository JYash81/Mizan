import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Building, FolderKanban } from "lucide-react";
import { apiPost, ApiError } from "../../../lib/api/client";
import { useAuth } from "../../auth/AuthContext";
import type { OrganizationSummary, WorkspaceSummary } from "../../auth/types";

export function OnboardingPage() {
  const [step, setStep] = useState<1 | 2>(1);
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [wsName, setWsName] = useState("Default Workspace");
  const [wsSlug, setWsSlug] = useState("default");
  const [createdOrg, setCreatedOrg] = useState<OrganizationSummary | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { refreshProfile } = useAuth();
  const navigate = useNavigate();

  const handleOrgNameChange = (name: string) => {
    setOrgName(name);
    if (!orgSlug || orgSlug === generateSlug(orgName)) {
      setOrgSlug(generateSlug(name));
    }
  };

  const handleWsNameChange = (name: string) => {
    setWsName(name);
    if (!wsSlug || wsSlug === generateSlug(wsName)) {
      setWsSlug(generateSlug(name));
    }
  };

  const generateSlug = (text: string) => {
    return text
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  };

  const handleCreateOrg = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const org = await apiPost<OrganizationSummary>("/organizations/", {
        name: orgName,
        slug: orgSlug,
      });
      setCreatedOrg(org);
      setStep(2);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to create organization. Please verify the slug is unique.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateWorkspace = async (e: FormEvent) => {
    e.preventDefault();
    if (!createdOrg) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await apiPost<WorkspaceSummary>(`/organizations/${createdOrg.id}/workspaces`, {
        name: wsName,
        slug: wsSlug,
      });
      await refreshProfile();
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to create workspace.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card max-w-lg">
        <div className="auth-header">
          <div className="auth-logo">M</div>
          <h2>Welcome to Mizan</h2>
          <p>
            {step === 1
              ? "Step 1 of 2: Create your company or organization profile"
              : "Step 2 of 2: Create your first experimentation workspace"}
          </p>
        </div>

        {error && <div className="alert-error" role="alert">{error}</div>}

        {step === 1 ? (
          <form onSubmit={handleCreateOrg} className="auth-form">
            <div className="form-group">
              <label htmlFor="orgName">Organization Name</label>
              <div className="input-icon-wrap">
                <Building className="input-icon" size={18} />
                <input
                  id="orgName"
                  type="text"
                  required
                  value={orgName}
                  onChange={(e) => handleOrgNameChange(e.target.value)}
                  placeholder="e.g. Acme Health Corp"
                  className="input-field"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="orgSlug">Organization URL Slug</label>
              <input
                id="orgSlug"
                type="text"
                required
                value={orgSlug}
                onChange={(e) => setOrgSlug(generateSlug(e.target.value))}
                placeholder="acme-health"
                className="input-field"
              />
              <small className="text-muted-foreground text-xs mt-1 block">
                Lowercase letters, numbers, and hyphens only
              </small>
            </div>

            <button type="submit" disabled={isSubmitting} className="btn-primary">
              {isSubmitting ? "Creating organization..." : "Continue to Workspace"}
              <ArrowRight size={16} />
            </button>
          </form>
        ) : (
          <form onSubmit={handleCreateWorkspace} className="auth-form">
            <div className="form-group">
              <label htmlFor="wsName">First Workspace Name</label>
              <div className="input-icon-wrap">
                <FolderKanban className="input-icon" size={18} />
                <input
                  id="wsName"
                  type="text"
                  required
                  value={wsName}
                  onChange={(e) => handleWsNameChange(e.target.value)}
                  placeholder="e.g. Card Triage AI"
                  className="input-field"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="wsSlug">Workspace Slug</label>
              <input
                id="wsSlug"
                type="text"
                required
                value={wsSlug}
                onChange={(e) => setWsSlug(generateSlug(e.target.value))}
                placeholder="card-triage"
                className="input-field"
              />
            </div>

            <button type="submit" disabled={isSubmitting} className="btn-primary">
              {isSubmitting ? "Finalizing setup..." : "Go to Mizan Console"}
              <ArrowRight size={16} />
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
