/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        tier: {
          hot:  '#e11d48',
          warm: '#f59e0b',
          cool: '#0ea5e9',
          cold: '#475569',
        },
      },
      minHeight: { touch: '44px' },
      minWidth:  { touch: '44px' },
      boxShadow: { sheet: '0 -8px 24px -8px rgb(0 0 0 / 0.15)' },
      zIndex:    { sheet: '40', filter: '50', toast: '60' },
    },
  },
  plugins: [],
}
