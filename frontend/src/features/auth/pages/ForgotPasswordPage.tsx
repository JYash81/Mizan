import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Mail } from "lucide-react";
import { apiPost, ApiError } from "../../../lib/api/client";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await apiPost("/auth/forgot-password", { email });
      setIsSubmitted(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to process request. Please try again.");
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
          <h2>Reset password</h2>
          <p>We'll send password reset instructions to your verified email</p>
        </div>

        {error && <div className="alert-error" role="alert">{error}</div>}

        {isSubmitted ? (
          <div className="text-center py-4">
            <CheckCircle2 size={48} className="text-emerald-500 mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Check your email</h3>
            <p className="text-muted-foreground mb-6">
              If an active account exists for <strong>{email}</strong>, we've sent instructions to reset
              your password.
            </p>
            <Link to="/login" className="btn-secondary inline-flex">
              <ArrowLeft size={16} />
              Return to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="email">Work Email</label>
              <div className="input-icon-wrap">
                <Mail className="input-icon" size={18} />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="input-field"
                />
              </div>
            </div>

            <button type="submit" disabled={isSubmitting} className="btn-primary">
              {isSubmitting ? "Sending link..." : "Send reset instructions"}
            </button>

            <div className="text-center mt-4">
              <Link to="/login" className="text-link text-sm inline-flex items-center gap-1">
                <ArrowLeft size={14} />
                Back to sign in
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
