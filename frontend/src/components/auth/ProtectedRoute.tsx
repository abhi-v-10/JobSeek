import React from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../ui/Button';
import { Lock } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const navigate = useNavigate();
  const isLoggedIn = !!localStorage.getItem('access_token');

  if (!isLoggedIn) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 bg-zinc-100 dark:bg-zinc-900 rounded-full flex items-center justify-center mb-6">
          <Lock size={32} className="text-zinc-400" />
        </div>
        <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Authentication Required</h2>
        <p className="text-zinc-500 dark:text-zinc-400 mb-8 max-w-sm">
          Please sign in to your account first to access this page.
        </p>
        <div className="w-full max-w-xs">
          <Button onClick={() => navigate('/login')}>Sign in to continue</Button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;
