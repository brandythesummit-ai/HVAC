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
      // Z-index ladder must clear Leaflet's pane stack (panes ~200,
      // markers ~600, popups ~700, controls 1000). z-sheet 1100 beats
      // them all so DetailSheet/FilterSheet/MobileDrawer render over
      // the map. Toast sits above sheets.
      zIndex:    { sheet: '1100', filter: '1100', toast: '1200' },
    },
  },
  plugins: [],
}
