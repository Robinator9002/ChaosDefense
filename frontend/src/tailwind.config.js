/** @type {import('tailwindcss').Config} */
export default {
    content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
    theme: {
        extend: {
            // Define the color palette based on the Pygame UI theme.
            // This allows us to use semantic names like `bg-background` or `text-accent-yellow`
            // for consistent styling across the entire application.
            colors: {
                background: '#0f1419', // The darkest background color
                'panel-primary': '#191e28', // Primary panel background
                'panel-secondary': '#28323c', // Lighter panel/interactive element background
                'border-primary': '#4b5563', // Standard border color (gray-600)
                'border-interactive': '#96b4c8', // Hover/selected border color
                'text-primary': '#e5e7eb', // Main text color (gray-200)
                'text-secondary': '#9ca3af', // Dimmer text color (gray-400)
                'text-disabled': '#6b7280', // Text for disabled elements (gray-500)
                'accent-yellow': '#facc15', // Gold, highlights (yellow-400)
                'accent-red': '#f87171', // HP, errors (red-400)
                'accent-blue': '#60a5fa', // Mana, info, primary action (blue-400)
            },
            // Define a custom font family to match the game's aesthetic.
            // We can easily change this later or add more fonts.
            fontFamily: {
                // Sets 'Roboto Mono' as the default monospaced font.
                mono: ['Roboto Mono', 'monospace'],
            },
            // Custom box-shadow for a "top shadow" effect on the build bar.
            boxShadow: {
                top: '0 -4px 6px -1px rgb(0 0 0 / 0.1), 0 -2px 4px -2px rgb(0 0 0 / 0.1)',
            },
        },
    },
    plugins: [],
};
