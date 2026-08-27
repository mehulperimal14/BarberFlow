/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Restrained, premium SaaS palette
        brand: {
          50: '#f6f6f7',
          100: '#e1e3e5',
          200: '#c3c7cb',
          300: '#9fa4ab',
          400: '#757c85',
          500: '#3c434c', // Primary gray
          600: '#2c3139',
          700: '#1d2127',
          800: '#121418',
          900: '#090a0c',
        },
        accent: {
          gold: '#C5A880', // Premium barber accent gold
          goldHover: '#B0936B',
        }
      }
    },
  },
  plugins: [],
}
