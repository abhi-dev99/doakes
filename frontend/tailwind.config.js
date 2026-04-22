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
        // Sophisticated, neutral 'Apple' palette
        apple: {
          blue: '#0071e3', // Standard iOS blue
          blueHover: '#0077ED',
          gray: '#F5F5F7', // Standard Apple background off-white
          grayDark: '#1D1D1F', // Standard Apple dark text
          grayBorder: '#D2D2D7', // Subtle borders
          red: '#FF3B30',
          orange: '#FF9500',
          green: '#34C759',
          glass: 'rgba(255, 255, 255, 0.72)', // Frosted glass
          glassDark: 'rgba(29, 29, 31, 0.72)'
        },
        argus: {
          darker: '#000000',
          dark: '#1C1C1E',
          card: '#2C2C2E',
          border: '#3A3A3C',
          accent: '#0A84FF',
          'accent-dark': '#0071E3',
          success: '#30D158',
          warning: '#FF9F0A',
          danger: '#FF453A',
        },
        'argus-light': {
          bg: '#F5F5F7',
          card: '#FFFFFF',
          border: '#E5E5EA',
          text: '#1D1D1F',
          muted: '#86868B',
        }
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system', 
          'BlinkMacSystemFont', 
          '"SF Pro Display"', 
          '"SF Pro Text"', 
          '"Helvetica Neue"', 
          'Helvetica', 
          'Arial', 
          'sans-serif'
        ],
        mono: [
          'JetBrains Mono',
          'SFMono-Regular',
          'Consolas',
          'Liberation Mono',
          'Menlo',
          'monospace'
        ],
      },
      boxShadow: {
        'apple-soft': '0 4px 24px rgba(0, 0, 0, 0.04)',
        'apple-float': '0 10px 40px rgba(0, 0, 0, 0.08)',
        'apple-dark': '0 4px 24px rgba(0, 0, 0, 0.4)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out forwards',
        'slide-up': 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        }
      }
    },
  },
  plugins: [],
}
