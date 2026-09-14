import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        surface: "var(--surface)",
        border: "var(--border)",
        navy: {
          950: "#050e1f",
          900: "#0a1830",
          800: "#0f2440",
          700: "#16345a",
          600: "#1e4676",
        },
        risk: {
          low: "#1a7f4f",
          moderate: "#c98a12",
          elevated: "#d9701e",
          high: "#c33f2e",
          critical: "#821f2e",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
