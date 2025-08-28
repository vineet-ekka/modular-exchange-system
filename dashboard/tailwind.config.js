/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // Light theme colors matching the reference image
        light: {
          bg: '#FFFFFF',       // White background
          'bg-secondary': '#F9FAFB', // Light gray background
          card: '#FFFFFF',     // White card backgrounds
          hover: '#F3F4F6',    // Light hover states
          border: '#E5E7EB',   // Light borders
        },
        dark: {
          bg: '#1a1a1a',      // Keep dark variants as fallback
          card: '#2a2a2a',    
          hover: '#3a3a3a',   
          border: '#404040',  
        },
        gray: {
          850: '#1a1d2e',
          950: '#0f1117'
        },
        // Text colors for light theme
        text: {
          primary: '#111827',   // Almost black for main text
          secondary: '#6B7280', // Gray for secondary text
          muted: '#9CA3AF',     // Light gray for muted text
        },
        // Data visualization colors (keep consistent)
        funding: {
          positive: '#10B981', // Green for positive rates
          negative: '#EF4444', // Red for negative rates
          neutral: '#6B7280',  // Gray for neutral/zero
        },
        chart: {
          line: '#FFA726',     // Orange for chart lines (matching image)
          orange: '#FF9800',   // Darker orange variant
        },
        // Accent colors
        accent: {
          green: '#10B981',
          red: '#EF4444',
          orange: '#FFA726',
          blue: '#3B82F6',
          purple: '#8B5CF6',
          indigo: '#6366F1',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}