import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, CheckCircle2, Lock } from "lucide-react";
import { apiPost, ApiError } from "../../../lib/api/client";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const tokenParam = searchParams.get("token") ?? "";

  const [token, setToken] = useState(tokenParam);
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== newPasswordConfirm) {
      setError("Passwords do not match.");
      return;
    }
    if (newPassword.length < 12) {
      setError("Password must contain at least 12 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiPost("/auth/reset-password", {
        token,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      });
      setIsSuccess(true);
      setTimeout(() => navigate("/login"), 3000);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Password reset failed. The link may be expired.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">M</div>
          <h2>Create new password</h2>
          <p>Choose a secure password with at least 12 characters</p>
        </div>

        {error && <div className="alert-error" role="alert">{error}</div>}

        {isSuccess ? (
          <div className="text-center py-4">
            <CheckCircle2 size={48} className="text-emerald-500 mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Password Reset Complete</h3>
            <p className="text-muted-foreground mb-6">
              Your password has been successfully updated. Redirecting you to sign in...
            </p>
            <Link to="/login" className="btn-primary inline-flex">
              Sign in now
              <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            {!tokenParam && (
              <div className="form-group">
                <label htmlFor="token">Reset Token</label>
                <input
                  id="token"
                  type="text"
                  required
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste token from reset email"
                  className="input-field"
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor="newPassword">New Password</label>
              <div className="input-icon-wrap">
                <Lock className="input-icon" size={18} />
                <input
                  id="newPassword"
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="input-field"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="newPasswordConfirm">Confirm New Password</label>
              <div className="input-icon-wrap">
                <Lock className="input-icon" size={18} />
                <input
                  id="newPasswordConfirm"
                  type="password"
                  required
                  value={newPasswordConfirm}
                  onChange={(e) => setNewPasswordConfirm(e.target.value)}
                  placeholder="••••••••••••"
                  className="input-field"
                />
              </div>
            </div>

            <button type="submit" disabled={isSubmitting} className="btn-primary">
              {isSubmitting ? "Resetting password..." : "Set new password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
