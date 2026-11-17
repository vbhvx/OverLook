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
        background: '#02050b',
        panel: '#050b16',
        'panel-border': '#0e2438',
        'panel-hover': '#112d45',
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#34d399',
          500: '#00ff9d',
          600: '#059669',
          700: '#047857'
        },
        cyber: {
          green: '#00ff9d',
          cyan: '#00e5ff',
          amber: '#fbbf24',
          red: '#ff3366',
          void: '#02050b',
          surface: '#050b16',
          border: '#0e2438',
          wire: '#13384e'
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Share Tech Mono"', 'monospace'],
        hud: ['"Share Tech Mono"', '"JetBrains Mono"', 'monospace'],
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glow-green': '0 0 16px rgba(0, 255, 157, 0.25)',
        'glow-cyan': '0 0 16px rgba(0, 229, 255, 0.25)',
        'glow-amber': '0 0 16px rgba(251, 191, 36, 0.25)',
      }
    },
  },
  plugins: [],
}

