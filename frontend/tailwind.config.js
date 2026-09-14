/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0A1210", // page ground — gunmetal, not slate
        panel: "#10231C", // chrome surface (cards, rail, header)
        panel2: "#152C21", // raised/hover chrome
        readout: "#071410", // recessed surface for raw evidentiary data
        line: "#24413A", // hairline seams
        line2: "#1A312B", // fainter seam, nested dividers
        brass: "#C99A3B", // signature accent — seal, primary actions, approved
        brassDim: "#8A6B2A",
        paper: "#E9E1CB", // seal face / certificate chrome
        ok: "#5FA98A", // nominal / allowed / verified lamp
        warn: "#CE7C3E", // drift / pending / caution lamp
        crit: "#C1483D", // denied / tampered / critical lamp
        fg: "#EAE6D9", // primary text
        fg2: "#8FA69C", // secondary / meta text
        fg3: "#4E655F", // tertiary / placeholder
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      borderRadius: {
        DEFAULT: "3px",
        sm: "2px",
        md: "3px",
        lg: "4px",
      },
      letterSpacing: {
        wider2: "0.09em",
      },
    },
  },
  plugins: [],
};
