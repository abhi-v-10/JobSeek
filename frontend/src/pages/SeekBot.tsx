import React from 'react';
import ProtectedRoute from '../components/auth/ProtectedRoute';

const SeekBot = () => {
  return (
    <ProtectedRoute>
        <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">SeekBot</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mb-8">Your AI assistant for career growth and hiring</p>
          
          <div className="flex-1 flex items-center justify-center">
            <p className="text-zinc-500 dark:text-zinc-400">SeekBot is currently resting. Check back later!</p>
          </div>
        </div>
      </ProtectedRoute>
  );
};

export default SeekBot;
