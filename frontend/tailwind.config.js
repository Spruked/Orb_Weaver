/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-orange': '#18CFE3',
        'brand-dark': '#061A33',
        'brand-blue': '#073B5C',
        'brand-accent': '#0E7490',
        'brand-success': '#10b981',
        'brand-warning': '#f59e0b',
        'brand-danger': '#ef4444',
        'brand-info': '#18CFE3',
        'brand-ice': '#F2FBFD'
      }
    },
  },
  plugins: [],
}
