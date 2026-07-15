/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        orb: {
          bg: '#0a0a0f',
          panel: '#12121a',
          border: '#1e1e2e',
          accent: '#6366f1',
          'accent-glow': '#818cf8',
          text: '#e2e8f0',
          'text-dim': '#94a3b8',
          success: '#22c55e',
          warning: '#f59e0b',
          error: '#ef4444',
          hume: '#3b82f6',
          kant: '#8b5cf6',
          locke: '#10b981',
          spinoza: '#f59e0b',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}
