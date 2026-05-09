export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
        display: ['"Orbitron"', "sans-serif"],
      },
      colors: {
        orbit: {
          950: "#030712",
          900: "#071018",
          800: "#0c1822",
          accent: "#22d3ee",
          warn: "#f97316",
        },
      },
      boxShadow: {
        panel: "0 0 0 1px rgb(34 211 238 / 0.12), 0 18px 48px rgb(0 0 0 / 0.55)",
      },
    },
  },
  plugins: [],
}

