/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                good: '#22c55e',
                satisfactory: '#84cc16',
                moderate: '#eab308',
                poor: '#f97316',
                verypoor: '#ef4444',
                severe: '#7f1d1d',
                brand: {
                    50: '#f0fdf4',
                    100: '#dcfce7',
                    400: '#4ade80',
                    500: '#22c55e',
                    600: '#16a34a',
                    900: '#14532d',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'Monaco', 'monospace'],
            },
            animation: {
                'pulse-slow': 'pulse 3s ease-in-out infinite',
                'glow': 'glow 2s ease-in-out infinite alternate',
                'slide-up': 'slideUp 0.4s ease-out',
                'fade-in': 'fadeIn 0.5s ease-out',
            },
            keyframes: {
                glow: {
                    '0%': { boxShadow: '0 0 5px rgba(34, 197, 94, 0.3)' },
                    '100%': { boxShadow: '0 0 20px rgba(34, 197, 94, 0.7)' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' },
                },
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'grid-pattern': "url(\"data:image/svg+xml,%3Csvg width='40' height='40' xmlns='http://www.w3.org/2000/svg'%3E%3Cdefs%3E%3Cpattern id='grid' width='40' height='40' patternUnits='userSpaceOnUse'%3E%3Cpath d='M 40 0 L 0 0 0 40' fill='none' stroke='rgba(34,197,94,0.06)' stroke-width='1'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='40' height='40' fill='url(%23grid)'/%3E%3C/svg%3E\")",
            },
        },
    },
    plugins: [],
}
