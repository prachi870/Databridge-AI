import { useTheme } from '../contexts/ThemeContext';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="btn-secondary flex items-center gap-2 relative overflow-hidden group"
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      <div className="relative w-5 h-5">
        {/* Sun icon */}
        <span
          className={`absolute inset-0 flex items-center justify-center transition-all duration-300 ${
            theme === 'light' ? 'opacity-100 rotate-0' : 'opacity-0 rotate-180'
          }`}
        >
          ☀️
        </span>
        {/* Moon icon */}
        <span
          className={`absolute inset-0 flex items-center justify-center transition-all duration-300 ${
            theme === 'dark' ? 'opacity-100 rotate-0' : 'opacity-0 -rotate-180'
          }`}
        >
          🌙
        </span>
      </div>
      <span className="text-sm font-medium">
        {theme === 'dark' ? 'Dark' : 'Light'}
      </span>
    </button>
  );
}
