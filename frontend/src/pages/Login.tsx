import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import GoogleButton from '../components/auth/GoogleButton';
import GithubButton from '../components/auth/GithubButton';
import ForgotPasswordModal from '../components/auth/ForgotPasswordModal';
import api from '../lib/axios';

const Login = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.email || !formData.password) {
      setError('Please fill in all fields.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.post('/users/login/', formData);
      if (response.data?.tokens?.access) {
        localStorage.setItem('access_token', response.data.tokens.access);
        if (response.data.tokens.refresh) {
          localStorage.setItem('refresh_token', response.data.tokens.refresh);
        }
        navigate('/dashboard');
      } else {
        setError('Login failed. No token received.');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || 'Invalid email or password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 shadow-sm">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Welcome back</h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Log in to your account to continue</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              name="email"
              placeholder="you@example.com"
              value={formData.email}
              onChange={handleChange}
              required
            />
            
            <div className="space-y-1">
              <Input
                label="Password"
                type="password"
                name="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                required
              />
              <div className="flex justify-end">
                <button 
                  type="button" 
                  onClick={() => setIsForgotModalOpen(true)}
                  className="text-xs font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300 transition-colors"
                >
                  Forgot Password?
                </button>
              </div>
            </div>

            {error && <p className="text-sm text-red-500 text-center">{error}</p>}

            <div className="pt-2">
              <Button type="submit" isLoading={isLoading}>
                Sign In
              </Button>
            </div>
          </form>

          <div className="mt-6 flex items-center justify-center gap-4">
            <div className="h-px bg-zinc-200 dark:bg-zinc-800 flex-1"></div>
            <span className="text-xs text-zinc-500 dark:text-zinc-400 font-medium uppercase tracking-wider">Or continue with</span>
            <div className="h-px bg-zinc-200 dark:bg-zinc-800 flex-1"></div>
          </div>

          <div className="mt-6 space-y-3">
            <GoogleButton />
            <GithubButton />
          </div>

          <p className="mt-8 text-center text-sm text-zinc-600 dark:text-zinc-400">
            Don't have an account?{' '}
            <Link to="/register" className="font-medium text-zinc-900 dark:text-zinc-50 hover:underline">
              Sign up
            </Link>
          </p>
        </div>

        <ForgotPasswordModal 
          isOpen={isForgotModalOpen} 
          onClose={() => setIsForgotModalOpen(false)} 
        />
      </div>
    );
  };

export default Login;
