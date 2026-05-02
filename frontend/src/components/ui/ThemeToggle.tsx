import React from 'react';
import { AnimatedThemeToggler } from './animated-theme-toggler';

const ThemeToggle: React.FC = () => {
  return (
    <AnimatedThemeToggler 
      variant="circle"
      className="p-2 rounded-full transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-900 dark:text-zinc-50 flex items-center justify-center [&>svg]:w-5 [&>svg]:h-5"
    />
  );
};

export default ThemeToggle;
