import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Lock, Mail, RefreshCw } from "lucide-react";
import { useAuth } from "../AuthContext";
import { ApiError } from "../../../lib/api/client";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to sign in. Please verify your credentials.");
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
          <h2>Sign in to Mizan</h2>
          <p>Access your organization's AI experimentation workspace</p>
        </div>

        {error && <div className="alert-error" role="alert">{error}</div>}

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

          <div className="form-group">
            <div className="label-row">
              <label htmlFor="password">Password</label>
              <Link to="/forgot-password" className="text-link">
                Forgot password?
              </Link>
            </div>
            <div className="input-icon-wrap">
              <Lock className="input-icon" size={18} />
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="input-field"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="toggle-password"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={isSubmitting} className="btn-primary">
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <RefreshCw size={16} className="animate-spin" />
                <span>Signing in... (Waking up cloud if idle)</span>
              </span>
            ) : (
              <>
                <span>Sign in</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Don't have an account?{" "}
            <Link to="/register" className="text-link font-medium">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
