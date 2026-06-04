/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-orange': '#FF6B35',
        'brand-dark': '#1a1a2e',
        'brand-blue': '#16213e',
        'brand-accent': '#0f3460',
        'brand-success': '#10b981',
        'brand-warning': '#f59e0b',
        'brand-danger': '#ef4444',
        'brand-info': '#3b82f6'
      }
    },
  },
  plugins: [],
}
