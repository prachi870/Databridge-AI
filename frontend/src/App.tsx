import { useState } from 'react';
import { Routes, Route, Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { ThemeToggle } from './components/ThemeToggle';
import Playground from './pages/Playground';
import Results from './pages/Results';
import Browse from './pages/Browse';
import Method from './pages/Method';
import Analytics from './pages/Analytics';
import Landing from './pages/Landing';
import Login from './pages/Login';
import { ACCESS_TOKEN_KEY, authenticatedFetch } from './lib/api';

function Nav({ authenticated, onLogout }: { authenticated: boolean; onLogout: () => void }) {
  const location = useLocation();
  
  const links = [
    { to: '/playground', label: 'Playground', icon: '🎮' },
    { to: '/results', label: 'Results', icon: '📊' },
    { to: '/analytics', label: 'Analytics', icon: '📈' },
    { to: '/browse', label: 'Browse', icon: '🗂️' },
    { to: '/method', label: 'Method', icon: '🧠' },
  ];
  
  return (
    <nav className="app-nav fixed top-0 left-0 right-0 z-50 border-b">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="flex flex-col gap-3 py-3 md:h-20 md:flex-row md:items-center md:justify-between md:gap-4 md:py-0">
          {/* Logo */}
          <Link to="/" className="app-brand flex min-w-0 items-center gap-2.5 group">
            <div className="relative shrink-0">
              <div className="absolute inset-0 bg-gradient-to-r from-violet-600 to-purple-600 rounded-lg blur-lg opacity-50 group-hover:opacity-75 transition-opacity"></div>
              <div className="relative bg-gradient-to-br from-violet-600 to-indigo-600 p-2 rounded-xl">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-bold leading-tight gradient-text sm:text-xl">SQL Router</h1>
              <p className="hidden text-xs text-gray-400 sm:block">AI-powered Text-to-SQL</p>
            </div>
          </Link>
          
          {/* Navigation Links */}
          <div className="app-nav-links flex min-w-0 items-center gap-1 overflow-x-auto pb-0.5 md:justify-end">
            {authenticated && links.map((link) => {
              const isActive = location.pathname === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  title={link.label}
                  className={`
                    relative shrink-0 rounded-xl px-3 py-2 font-medium transition-all duration-200 sm:px-3.5
                    ${isActive 
                      ? 'app-nav-active text-white' 
                      : 'app-nav-inactive text-gray-300 hover:text-white'
                    }
                  `}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-base">{link.icon}</span>
                    <span className="hidden lg:inline">{link.label}</span>
                  </span>
                </Link>
              );
            })}
            
            {/* Theme Toggle */}
            {!authenticated && (
              <Link to="/login" className="btn-primary ml-1 shrink-0 px-3 py-2 text-sm sm:px-4">
                Sign in
              </Link>
            )}
            {authenticated && (
              <button type="button" onClick={onLogout} className="btn-secondary ml-1 shrink-0 px-3 py-2 text-sm sm:px-4">
                <span className="hidden sm:inline">Sign out</span>
                <span className="sm:hidden" aria-label="Sign out">↗</span>
              </button>
            )}
            <div className="ml-1 shrink-0 border-l border-white/10 pl-2">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

function RequireAuthentication({ authenticated, children }: { authenticated: boolean; children: JSX.Element }) {
  return authenticated ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem(ACCESS_TOKEN_KEY)));
  const navigate = useNavigate();

  const signOut = async () => {
    try {
      if (localStorage.getItem(ACCESS_TOKEN_KEY)) await authenticatedFetch('/api/auth/logout', { method: 'POST' });
    } finally {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      setAuthenticated(false);
      navigate('/', { replace: true });
    }
  };

  return (
    <ThemeProvider>
      <div className="min-h-screen pt-32 md:pt-20">
        <Nav authenticated={authenticated} onLogout={signOut} />
        
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login onAuthenticated={() => setAuthenticated(true)} />} />
          <Route path="/playground" element={<RequireAuthentication authenticated={authenticated}><Playground /></RequireAuthentication>} />
          <Route path="/results" element={<RequireAuthentication authenticated={authenticated}><Results /></RequireAuthentication>} />
          <Route path="/analytics" element={<RequireAuthentication authenticated={authenticated}><Analytics /></RequireAuthentication>} />
          <Route path="/browse" element={<RequireAuthentication authenticated={authenticated}><Browse /></RequireAuthentication>} />
          <Route path="/method" element={<RequireAuthentication authenticated={authenticated}><Method /></RequireAuthentication>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </ThemeProvider>
  );
}
