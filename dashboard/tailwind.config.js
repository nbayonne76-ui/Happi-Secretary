/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0eeff',
          100: '#e2ddff',
          500: '#6C63FF',
          600: '#5A52E0',
          700: '#4840C0',
        },
      },
    },
  },
  plugins: [],
}
