import { useState, useCallback } from 'react';

/**
 * LoginPage — Corporate Authentication Gate
 *
 * Clean, centered login form with email/password fields.
 * Supports both Sign In and Sign Up modes.
 * Uses custom backend API endpoints (/api/auth/login, /api/auth/register).
 * Stores JWT in localStorage on successful auth.
 */
export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setIsLoading(true);

    try {
      const endpoint = isSignUp ? '/api/auth/register' : '/api/auth/login';
      const body = isSignUp
        ? { email, password, full_name: fullName }
        : { email, password };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed.');
      }

      // Store JWT and user info in localStorage
      localStorage.setItem('token', data.token);
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('user_email', data.email);
      localStorage.setItem('user_name', data.full_name || '');

      // Notify parent component
      onLoginSuccess({
        token: data.token,
        user_id: data.user_id,
        email: data.email,
        full_name: data.full_name || '',
      });

    } catch (err) {
      setError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [email, password, fullName, isSignUp, onLoginSuccess]);

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Logo & Title */}
        <div className="login-card__header">
          <div className="app-header__title-icon" style={{ width: 40, height: 40, fontSize: '1.2rem' }}>⚡</div>
          <h1 className="login-card__title">FMCG Bid Intelligence</h1>
          <p className="login-card__subtitle">
            {isSignUp ? 'Create your account' : 'Sign in to your workspace'}
          </p>
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div className="login-card__alert login-card__alert--error">
            ⚠ {error}
          </div>
        )}
        {successMessage && (
          <div className="login-card__alert login-card__alert--success">
            ✓ {successMessage}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="login-card__form">
          {/* Full Name — only shown on Sign Up */}
          {isSignUp && (
            <div className="form-group">
              <label className="form-label" htmlFor="login-name">Full Name</label>
              <input
                id="login-name"
                type="text"
                className="form-input"
                placeholder="John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="login-email">Email Address</label>
            <input
              id="login-email"
              type="email"
              className="form-input"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={isSignUp ? 'new-password' : 'current-password'}
            />
          </div>

          <button
            type="submit"
            className="btn btn--primary"
            style={{ width: '100%', padding: '12px', marginTop: '8px' }}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="processing-spinner" style={{ width: 16, height: 16, borderWidth: 2, margin: 0 }} />
                {isSignUp ? 'Creating Account...' : 'Signing In...'}
              </>
            ) : (
              isSignUp ? 'Create Account' : 'Sign In'
            )}
          </button>
        </form>

        {/* Toggle Sign In / Sign Up */}
        <div className="login-card__toggle">
          <span style={{ color: 'var(--zinc-500)', fontSize: '0.82rem' }}>
            {isSignUp ? 'Already have an account?' : "Don't have an account?"}
          </span>
          <button
            type="button"
            className="btn btn--ghost"
            style={{ padding: '4px 12px', fontSize: '0.8rem' }}
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError('');
              setSuccessMessage('');
            }}
          >
            {isSignUp ? 'Sign In' : 'Sign Up'}
          </button>
        </div>
      </div>
    </div>
  );
}
