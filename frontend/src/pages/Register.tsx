import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import CountryCodeSelect from '../components/ui/CountryCodeSelect';
import GoogleButton from '../components/auth/GoogleButton';
import GithubButton from '../components/auth/GithubButton';
import api from '../lib/axios';

const Register = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    full_name: '',
    username: '',
    phone_code: '+1',
    phone_number: '',
    email: '',
    password: '',
    user_type: 'seeker'
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handlePhoneCodeChange = (code: string) => {
    setFormData({ ...formData, phone_code: code });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const payload = {
        full_name: formData.full_name,
        username: formData.username,
        mobile_number: `${formData.phone_code}${formData.phone_number}`,
        email: formData.email,
        password: formData.password,
        user_type: formData.user_type
      };

      await api.post('/users/register/', payload);
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6 py-12">
        <div className="w-full max-w-md bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 shadow-sm">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Create an account</h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Join JobSeek to find or post jobs</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Full Name"
              name="full_name"
              placeholder="John Doe"
              value={formData.full_name}
              onChange={handleChange}
              required
            />
            
            <Input
              label="Username"
              name="username"
              placeholder="johndoe"
              value={formData.username}
              onChange={handleChange}
              required
            />

            <div className="flex gap-2 items-start">
              <div className="w-1/3">
                <CountryCodeSelect 
                  value={formData.phone_code} 
                  onChange={handlePhoneCodeChange} 
                />
              </div>
              <div className="w-2/3">
                <Input
                  label="Phone Number"
                  name="phone_number"
                  placeholder="1234567890"
                  value={formData.phone_number}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <Input
              label="Email"
              type="email"
              name="email"
              placeholder="you@example.com"
              value={formData.email}
              onChange={handleChange}
              required
            />
            
            <Input
              label="Password"
              type="password"
              name="password"
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
              required
              minLength={8}
            />

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Account Type</label>
              <div className="grid grid-cols-2 gap-2">
                <label className={`border rounded-lg p-3 cursor-pointer transition-all flex items-center justify-center text-sm font-medium
                  ${formData.user_type === 'seeker' 
                    ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900' 
                    : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50'}`}>
                  <input 
                    type="radio" 
                    name="user_type" 
                    value="seeker" 
                    checked={formData.user_type === 'seeker'}
                    onChange={handleChange}
                    className="sr-only" 
                  />
                  Job Seeker
                </label>
                <label className={`border rounded-lg p-3 cursor-pointer transition-all flex items-center justify-center text-sm font-medium
                  ${formData.user_type === 'poster' 
                    ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900' 
                    : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50'}`}>
                  <input 
                    type="radio" 
                    name="user_type" 
                    value="poster" 
                    checked={formData.user_type === 'poster'}
                    onChange={handleChange}
                    className="sr-only" 
                  />
                  Job Poster
                </label>
              </div>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                Seekers can search and apply for jobs. Posters can create vacancies and hire. You can change this later in your profile settings.
              </p>
            </div>

            {error && <p className="text-sm text-red-500 text-center">{error}</p>}

            <div className="pt-2">
              <Button type="submit" isLoading={isLoading}>
                Create Account
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
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-zinc-900 dark:text-zinc-50 hover:underline">
              Log in
            </Link>
          </p>
        </div>
      </div>
    );
  };

export default Register;
