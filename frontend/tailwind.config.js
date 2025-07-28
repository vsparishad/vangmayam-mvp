/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // Sanskrit/Vedic inspired color palette
        saffron: {
          50: '#fefdf8',
          100: '#fef9e7',
          200: '#fef0c7',
          300: '#fde68a',
          400: '#fcd34d',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        vermillion: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
        sandalwood: {
          50: '#faf9f7',
          100: '#f4f1eb',
          200: '#e8e0d1',
          300: '#d6c7b0',
          400: '#c0a888',
          500: '#a68b5b',
          600: '#8b6914',
          700: '#6b5010',
          800: '#4a3a0e',
          900: '#2d240a',
        }
      },
      fontFamily: {
        'devanagari': ['Noto Sans Devanagari', 'serif'],
        'sanskrit': ['Siddhanta', 'Noto Sans Devanagari', 'serif'],
        'tamil': ['Noto Sans Tamil', 'serif'],
      },
      typography: {
        DEFAULT: {
          css: {
            'max-width': 'none',
            color: '#374151',
            '[class~="lead"]': {
              color: '#4b5563',
            },
            a: {
              color: '#d97706',
              textDecoration: 'underline',
              fontWeight: '500',
            },
            strong: {
              color: '#111827',
              fontWeight: '600',
            },
            'ol[type="A"]': {
              '--list-counter-style': 'upper-alpha',
            },
            'ol[type="a"]': {
              '--list-counter-style': 'lower-alpha',
            },
            'ol[type="A" s]': {
              '--list-counter-style': 'upper-alpha',
            },
            'ol[type="a" s]': {
              '--list-counter-style': 'lower-alpha',
            },
            'ol[type="I"]': {
              '--list-counter-style': 'upper-roman',
            },
            'ol[type="i"]': {
              '--list-counter-style': 'lower-roman',
            },
            'ol[type="I" s]': {
              '--list-counter-style': 'upper-roman',
            },
            'ol[type="i" s]': {
              '--list-counter-style': 'lower-roman',
            },
            'ol[type="1"]': {
              '--list-counter-style': 'decimal',
            },
          },
        },
        lg: {
          css: {
            fontSize: '1.125rem',
            lineHeight: '1.7777778',
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
