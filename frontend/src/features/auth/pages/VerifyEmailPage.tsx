import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, CheckCircle2, XCircle } from "lucide-react";
import { apiPost, ApiError } from "../../../lib/api/client";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const tokenParam = searchParams.get("token") ?? "";

  const [token, setToken] = useState(tokenParam);
  const [resendEmail, setResendEmail] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resendSuccess, setResendSuccess] = useState<string | null>(null);

  const handleVerify = async (tokenToVerify: string) => {
    if (!tokenToVerify) return;
    setIsVerifying(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await apiPost<{ message: string }>("/auth/verify-email", { token: tokenToVerify });
      setSuccess(res.message ?? "Email verified successfully!");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Verification failed. The token may be expired or invalid.");
      }
    } finally {
      setIsVerifying(false);
    }
  };

  useEffect(() => {
    if (tokenParam) {
      void handleVerify(tokenParam);
    }
  }, [tokenParam]);

  const handleResend = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await apiPost<{ message: string }>("/auth/resend-verification", {
        email: resendEmail,
      });
      setResendSuccess(res.message);
    } catch {
      setResendSuccess("If an unverified account exists, a new verification email was sent.");
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">M</div>
          <h2>Verify your email</h2>
          <p>Activate your account to start experimenting on Mizan</p>
        </div>

        {success ? (
          <div className="text-center py-4">
            <CheckCircle2 size={48} className="text-emerald-500 mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Account Verified</h3>
            <p className="text-muted-foreground mb-6">{success}</p>
            <Link to="/login" className="btn-primary inline-flex">
              Sign in now
              <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <div>
            {error && (
              <div className="alert-error flex items-start gap-2" role="alert">
                <XCircle size={18} className="shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {!tokenParam && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void handleVerify(token);
                }}
                className="auth-form mb-6"
              >
                <div className="form-group">
                  <label htmlFor="token">Verification Code / Token</label>
                  <input
                    id="token"
                    type="text"
                    required
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="Paste token from verification email"
                    className="input-field"
                  />
                </div>
                <button type="submit" disabled={isVerifying} className="btn-primary">
                  {isVerifying ? "Verifying..." : "Verify account"}
                </button>
              </form>
            )}

            <div className="border-t border-border pt-6 mt-6">
              <h4 className="text-sm font-medium mb-2">Need a new link?</h4>
              {resendSuccess ? (
                <p className="text-sm text-emerald-600 font-medium">{resendSuccess}</p>
              ) : (
                <form onSubmit={handleResend} className="flex gap-2">
                  <input
                    type="email"
                    required
                    value={resendEmail}
                    onChange={(e) => setResendEmail(e.target.value)}
                    placeholder="Enter your email"
                    className="input-field text-sm"
                  />
                  <button type="submit" className="btn-secondary text-sm whitespace-nowrap">
                    Resend email
                  </button>
                </form>
              )}
            </div>
          </div>
        )}

        <div className="auth-footer">
          <Link to="/login" className="text-link text-sm">
            Back to sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
