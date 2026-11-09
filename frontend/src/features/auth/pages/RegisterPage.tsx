import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Lock, Mail, User } from "lucide-react";
import { apiPost, ApiError } from "../../../lib/api/client";

export function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 12) {
      setError("Password must contain at least 12 characters.");
      return;
    }
    if (!termsAccepted) {
      setError("You must accept the terms of service.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiPost("/auth/register", {
        full_name: fullName,
        email,
        password,
        password_confirm: passwordConfirm,
        terms_accepted: termsAccepted,
      });
      setIsSuccess(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Registration failed. Please check your inputs.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="auth-container">
        <div className="auth-card text-center">
          <div className="success-icon-wrap">
            <CheckCircle2 size={48} className="text-emerald-500" />
          </div>
          <h2>Check your inbox</h2>
          <p>
            We have sent a verification link to <strong>{email}</strong>. Please click the link to
            verify your account before logging in.
          </p>
          <div className="mt-6">
            <Link to="/login" className="btn-primary inline-flex">
              Return to sign in
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">M</div>
          <h2>Create your Mizan account</h2>
          <p>Enterprise AI experimentation, evaluation and model publishing</p>
        </div>

        {error && <div className="alert-error" role="alert">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="fullName">Full Name</label>
            <div className="input-icon-wrap">
              <User className="input-icon" size={18} />
              <input
                id="fullName"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Frank Reynolds"
                className="input-field"
              />
            </div>
          </div>

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

          <div className="form-group">
            <label htmlFor="password">Password (Minimum 12 characters)</label>
            <div className="input-icon-wrap">
              <Lock className="input-icon" size={18} />
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="input-field"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="passwordConfirm">Confirm Password</label>
            <div className="input-icon-wrap">
              <Lock className="input-icon" size={18} />
              <input
                id="passwordConfirm"
                type="password"
                required
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="••••••••••••"
                className="input-field"
              />
            </div>
          </div>

          <div className="checkbox-wrap">
            <input
              id="terms"
              type="checkbox"
              checked={termsAccepted}
              onChange={(e) => setTermsAccepted(e.target.checked)}
              required
            />
            <label htmlFor="terms">
              I agree to the <span className="text-link">Terms of Service</span> and{" "}
              <span className="text-link">Privacy Policy</span>
            </label>
          </div>

          <button type="submit" disabled={isSubmitting} className="btn-primary">
            {isSubmitting ? "Creating account..." : "Create account"}
            <ArrowRight size={16} />
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Already have an account?{" "}
            <Link to="/login" className="text-link font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
