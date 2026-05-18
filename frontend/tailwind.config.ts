import animate from 'tailwindcss-animate'
import type { Config } from 'tailwindcss'

const config: Config = {
  // One [data-theme] attribute drives both the design tokens and the
  // shadcn HSL tokens (see src/index.css).
  darkMode: ['selector', 'html[data-theme="dark"]'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // --- shadcn semantic tokens (HSL) ---
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          // shadcn's "accent" = muted hover surface (NOT the brand green)
          DEFAULT: 'hsl(var(--accent-ui))',
          foreground: 'hsl(var(--accent-ui-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },

        // --- design raw tokens (verbatim from the Phase 7 package) ---
        paper: {
          DEFAULT: 'var(--bg)',
          sunk: 'var(--bg-sunk)',
        },
        surface: {
          DEFAULT: 'var(--surface)',
          2: 'var(--surface-2)',
        },
        line: {
          DEFAULT: 'var(--line)',
          strong: 'var(--line-strong)',
        },
        ink: {
          DEFAULT: 'var(--ink)',
          2: 'var(--ink-2)',
          3: 'var(--ink-3)',
          4: 'var(--ink-4)',
        },
        // brand green lives under `brand.*` because the bare `accent`
        // key is reserved by shadcn above.
        brand: {
          green: 'var(--accent)',
          'green-2': 'var(--accent-2)',
          'green-soft': 'var(--accent-soft)',
          'green-tint': 'var(--accent-tint)',
          orange: 'var(--brand-orange)',
          ink: 'var(--brand-ink)',
        },
        warn: {
          DEFAULT: 'var(--warn)',
          soft: 'var(--warn-soft)',
        },
        info: {
          DEFAULT: 'var(--info)',
          soft: 'var(--info-soft)',
        },
      },
      fontFamily: {
        sans: ['Inter Tight', '-apple-system', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        serif: ['Fraunces', 'Georgia', 'serif'],
        brand: ['Archivo', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        // --radius is 10px, so shadcn lg=10 / md=8 / sm=6 (matches the
        // design's 10/6 scale); xl = the design's large radius (16px).
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        xl: 'var(--radius-lg)',
      },
      boxShadow: {
        // Warm, layered design shadows — shadcn Card uses `shadow-sm`,
        // so reskinning these reskins existing primitives too.
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'subtle-bounce': {
          '0%': { transform: 'scale(1)' },
          '40%': { transform: 'scale(1.08)' },
          '70%': { transform: 'scale(0.97)' },
          '100%': { transform: 'scale(1)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '0.35' },
          '50%': { opacity: '1' },
        },
        'ring-fill': {
          from: { strokeDashoffset: 'var(--from)' },
          to: { strokeDashoffset: 'var(--to)' },
        },
        spin: {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.5s ease both',
        shimmer: 'shimmer 1.6s linear infinite',
        'subtle-bounce': 'subtle-bounce 0.7s cubic-bezier(0.4, 1.4, 0.6, 1)',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        spin: 'spin 1s linear infinite',
      },
    },
  },
  plugins: [animate],
}

export default config
