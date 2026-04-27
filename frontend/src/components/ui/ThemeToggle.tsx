import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-full transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800"
      aria-label="Toggle theme"
    >
      {theme === 'light' ? (
        <Moon className="w-5 h-5 text-zinc-900" />
      ) : (
        <Sun className="w-5 h-5 text-zinc-50" />
      )}
    </button>
  );
};

export default ThemeToggle;
