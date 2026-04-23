import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * This page receives the JWT tokens from the Django backend via URL query
 * params after a successful OAuth (Google/GitHub) login, saves them to
 * localStorage, and redirects to the dashboard.
 *
 * URL: /oauth/callback?access=<access_token>&refresh=<refresh_token>
 */
const OAuthCallback = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const access = params.get('access');
    const refresh = params.get('refresh');
    const error = params.get('error');

    if (error || !access) {
      navigate('/login?error=oauth_failed');
      return;
    }

    localStorage.setItem('access_token', access);
    if (refresh) {
      localStorage.setItem('refresh_token', refresh);
    }

    navigate('/dashboard');
  }, [navigate]);

  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100 rounded-full animate-spin" />
        <p className="text-sm text-zinc-500">Completing sign-in…</p>
      </div>
    </div>
  );
};

export default OAuthCallback;
