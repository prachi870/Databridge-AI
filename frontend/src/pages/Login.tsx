import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ACCESS_TOKEN_KEY, API_BASE_URL } from '../lib/api';

interface AuthResponse {
  access_token: string;
  user: { id: number; email: string };
}

export default function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [registerMode, setRegisterMode] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    if (registerMode && password.length < 12) {
      setError('Choose a password with at least 12 characters.');
      return;
    }
    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/${registerMode ? 'register' : 'login'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = data?.detail;
        throw new Error(typeof detail === 'string' ? detail : `Sign-in request failed (HTTP ${response.status})`);
      }
      const authResponse = data as AuthResponse;
      localStorage.setItem(ACCESS_TOKEN_KEY, authResponse.access_token);
      onAuthenticated();
      navigate('/playground', { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not sign in. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page mx-auto grid min-h-[calc(100vh-5rem)] max-w-7xl items-center gap-12 px-6 py-12 lg:grid-cols-[1fr_0.82fr]">
      <section className="hidden space-y-7 lg:block">
        <p className="landing-eyebrow-text text-xs font-semibold uppercase tracking-[0.2em]">Your data, your questions</p>
        <h1 className="max-w-xl text-5xl font-bold leading-tight text-white xl:text-6xl">
          Ask in plain language.
          <span className="landing-headline block">See the SQL behind it.</span>
        </h1>
        <p className="max-w-lg text-lg leading-8 text-slate-300">
          Upload datasets, ask questions in natural language, inspect the generated SQL, and follow how
          the model router handles each request.
        </p>
        <div className="login-feature-list space-y-3 text-sm text-slate-300">
          <p><span>✓</span> Query SQLite and uploaded CSV datasets</p>
          <p><span>✓</span> Review queries before read-only execution</p>
          <p><span>✓</span> See routing decisions and benchmark analytics</p>
        </div>
      </section>

      <section className="login-card glass relative mx-auto w-full max-w-md overflow-hidden rounded-3xl p-6 sm:p-9">
        <div className="login-card-orb" aria-hidden="true" />
        <div className="relative">
          <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white">
            <span aria-hidden="true">←</span> Back to project
          </Link>
          <div className="mt-8">
            <p className="landing-eyebrow-text text-xs font-semibold uppercase tracking-[0.2em]">SQL Router account</p>
            <h2 className="mt-2 text-3xl font-bold text-white">{registerMode ? 'Create your account' : 'Welcome back'}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              {registerMode ? 'Create an account to enter the project workspace.' : 'Sign in to continue to your data workspace.'}
            </p>
          </div>

          <form className="mt-7 space-y-5" onSubmit={submit}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-200">Email address</span>
              <input
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                className="input-field"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-200">Password</span>
              <input
                type="password"
                autoComplete={registerMode ? 'new-password' : 'current-password'}
                required
                minLength={registerMode ? 12 : 1}
                maxLength={128}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={registerMode ? 'At least 12 characters' : 'Enter your password'}
                className="input-field"
              />
              {registerMode && <span className="block text-xs text-slate-500">Use 12 or more characters.</span>}
            </label>
            {error && <p role="alert" className="rounded-xl border border-rose-300/20 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting ? 'Please wait…' : registerMode ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-400">
            {registerMode ? 'Already registered?' : 'New to SQL Router?'}{' '}
            <button
              type="button"
              onClick={() => {
                setRegisterMode(!registerMode);
                setError('');
              }}
              className="font-semibold text-violet-200 underline decoration-violet-400/40 underline-offset-4 hover:text-white"
            >
              {registerMode ? 'Sign in' : 'Create an account'}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}
