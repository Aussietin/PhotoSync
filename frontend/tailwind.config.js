/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'sans-serif',
        ],
      },
      colors: {
        // Primary brand ramp (sky/indigo blend)
        brand: {
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
        // Accent for gradients / highlights
        accent: {
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
        },
        // Deep, slightly blue-tinted neutrals for surfaces
        ink: {
          950: '#080b14',
          900: '#0d1220',
          850: '#121829',
          800: '#1a2236',
          700: '#273049',
          600: '#3a4663',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(59,130,246,0.25), 0 8px 30px -6px rgba(59,130,246,0.45)',
        'glow-accent':
          '0 0 0 1px rgba(168,85,247,0.25), 0 8px 30px -6px rgba(168,85,247,0.45)',
        soft: '0 4px 24px -8px rgba(0,0,0,0.5)',
        card: '0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.6)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #a855f7 100%)',
        'brand-gradient-soft':
          'linear-gradient(135deg, rgba(59,130,246,0.18) 0%, rgba(168,85,247,0.18) 100%)',
        'app-radial':
          'radial-gradient(1200px 600px at 80% -10%, rgba(99,102,241,0.18), transparent 60%), radial-gradient(900px 500px at -10% 10%, rgba(168,85,247,0.12), transparent 55%)',
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.9)', opacity: '0.7' },
          '100%': { transform: 'scale(1.6)', opacity: '0' },
        },
        'bar-stripe': {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '40px 0' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.6s infinite',
        'fade-in': 'fade-in 0.3s ease both',
        'fade-up': 'fade-up 0.35s ease both',
        'scale-in': 'scale-in 0.2s ease both',
        float: 'float 3s ease-in-out infinite',
        'pulse-ring': 'pulse-ring 1.4s ease-out infinite',
        'bar-stripe': 'bar-stripe 1s linear infinite',
      },
    },
  },
  plugins: [],
}
