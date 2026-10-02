/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0B4A2B',
          foreground: '#FFFFFF',
          hover: '#073A21',
        },
        accent: {
          DEFAULT: '#D1FAE5',
          foreground: '#064E3B',
        },
        warm: {
          50: '#FAFAF8',
          100: '#F4F3EF',
          200: '#E7E5DF',
          500: '#73736E',
          700: '#44443F',
          900: '#20211E',
        },
        warning: '#FBBF24',
        danger: '#EF4444',
      },
      fontFamily: {
        heading: ['Poppins', 'ui-sans-serif', 'system-ui'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
      },
      fontSize: {
        xs: ['0.875rem', '1.35rem'],
        base: ['1rem', '1.6rem'],
        lg: ['1.25rem', '1.75rem'],
        '2xl': ['1.75rem', '2.2rem'],
        '4xl': ['2.5rem', '3rem'],
      },
      borderRadius: {
        xl: '0.75rem',
        '2xl': '1rem',
      },
      boxShadow: {
        soft: '0 10px 30px rgba(20, 45, 31, 0.08)',
      },
    },
  },
  plugins: [],
}
