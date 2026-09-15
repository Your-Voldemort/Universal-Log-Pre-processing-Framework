/** @type {import('tailwindcss').Config} */

// Every color is a theme token defined in app/globals.css as OKLCH channels, so
// light and dark share one vocabulary and opacity modifiers (bg-warn/10) still work.
const TOKENS = [
  "canvas", "surface", "raised", "sunken", "scrim",
  "line", "line-strong", "control",
  "ink", "ink-2", "ink-3",
  "accent", "accent-hover", "accent-ink", "accent-soft", "on-accent",
  "ok", "ok-soft", "warn", "warn-soft", "bad", "bad-soft",
];

module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      ...Object.fromEntries(TOKENS.map((name) => [name, `oklch(var(--${name}) / <alpha-value>)`])),
    },
    fontFamily: {
      sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
    },
    // fixed product scale, ~1.15 ratio: 11 / 12 / 13 / 14 / 16 / 20 / 24 px
    fontSize: {
      "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      xs: ["0.75rem", { lineHeight: "1.125rem" }],
      sm: ["0.8125rem", { lineHeight: "1.25rem" }],
      base: ["0.875rem", { lineHeight: "1.375rem" }],
      lg: ["1rem", { lineHeight: "1.5rem" }],
      xl: ["1.25rem", { lineHeight: "1.75rem" }],
      "2xl": ["1.5rem", { lineHeight: "2rem" }],
    },
    borderRadius: {
      none: "0",
      sm: "3px",
      DEFAULT: "4px",
      md: "6px",
      full: "9999px",
    },
    zIndex: {
      0: "0",
      sticky: "20",
      scrim: "30",
      drawer: "40",
    },
  },
  plugins: [],
};
