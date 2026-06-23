import { useState, FormEvent } from 'react';
import { useAuthStore } from '../store/useAuthStore';

export default function LoginPage() {
  const { login, register, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isSignUp) await register(email, password, fullName);
    else await login(email, password);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__header">
          <div className="app-header__title-icon" style={{ width: 40, height: 40, fontSize: '1.2rem' }}>⚡</div>
          <h1 className="login-card__title">FMCG Bid Intelligence</h1>
          <p className="login-card__subtitle">{isSignUp ? 'Create your account' : 'Sign in to your workspace'}</p>
        </div>
        {error && <div className="login-card__alert login-card__alert--error">⚠ {error}</div>}
        <form onSubmit={handleSubmit} className="login-card__form">
          {isSignUp && (
            <div className="form-group">
              <label className="form-label" htmlFor="login-name">Full Name</label>
              <input id="login-name" type="text" className="form-input" placeholder="John Doe" value={fullName} onChange={e => setFullName(e.target.value)} autoComplete="name" />
            </div>
          )}
          <div className="form-group">
            <label className="form-label" htmlFor="login-email">Email Address</label>
            <input id="login-email" type="email" className="form-input" placeholder="you@company.com" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="login-password">Password</label>
            <input id="login-password" type="password" className="form-input" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} autoComplete={isSignUp ? 'new-password' : 'current-password'} />
          </div>
          <button type="submit" className="btn btn--primary" style={{ width: '100%', padding: '12px', marginTop: '8px' }} disabled={isLoading}>
            {isLoading ? (<><span className="processing-spinner" style={{ width: 16, height: 16, borderWidth: 2, margin: 0 }} />{isSignUp ? 'Creating Account...' : 'Signing In...'}</>) : (isSignUp ? 'Create Account' : 'Sign In')}
          </button>
        </form>
        <div className="login-card__toggle">
          <span style={{ color: 'var(--zinc-500)', fontSize: '0.82rem' }}>{isSignUp ? 'Already have an account?' : "Don't have an account?"}</span>
          <button type="button" className="btn btn--ghost" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => { setIsSignUp(!isSignUp); clearError(); }}>{isSignUp ? 'Sign In' : 'Sign Up'}</button>
        </div>
      </div>
    </div>
  );
}
