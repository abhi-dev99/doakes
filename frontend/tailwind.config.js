/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Dark theme - Deep blue/teal accent (unique, not generic purple)
        argus: {
          darker: '#0a0f1a',
          dark: '#0f172a',
          card: '#1e293b',
          border: '#334155',
          accent: '#06b6d4',      // Cyan accent
          'accent-dark': '#0891b2',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
        },
        // Light theme
        'argus-light': {
          bg: '#f8fafc',
          card: '#ffffff',
          border: '#e2e8f0',
          text: '#0f172a',
          muted: '#64748b',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgb(6, 182, 212, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgb(6, 182, 212, 0.8)' },
        }
      }
    },
  },
  plugins: [],
}
