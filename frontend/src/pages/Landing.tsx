import React from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center relative overflow-hidden">
      {/* Abstract background blobs for aesthetics */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 dark:bg-blue-500/5 rounded-full blur-3xl mix-blend-multiply dark:mix-blend-lighten animate-blob"></div>
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-purple-500/10 dark:bg-purple-500/5 rounded-full blur-3xl mix-blend-multiply dark:mix-blend-lighten animate-blob animation-delay-2000"></div>
      <div className="absolute bottom-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-pink-500/10 dark:bg-pink-500/5 rounded-full blur-3xl mix-blend-multiply dark:mix-blend-lighten animate-blob animation-delay-4000"></div>

      <div className="relative z-10 max-w-3xl mx-auto space-y-8 animate-fade-in-up">
        <h1 className="text-6xl md:text-8xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-zinc-900 to-zinc-500 dark:from-zinc-100 dark:to-zinc-500 pb-2">
          JobSeek
        </h1>
        <p className="text-xl md:text-2xl text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          Discover your next career opportunity or find the perfect candidate for your team with our intelligent matching platform.
        </p>
        <div className="pt-8 flex justify-center">
          <div className="w-full max-w-xs">
            <Button 
              onClick={() => {
                const isLoggedIn = !!localStorage.getItem('access_token');
                navigate(isLoggedIn ? '/jobs' : '/register');
              }}
              className="py-4 text-lg font-bold shadow-xl shadow-zinc-900/10 dark:shadow-zinc-100/10 hover:scale-105 transition-transform"
            >
              Start now !!
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Landing;
