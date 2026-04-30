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
        canvas: "#020617",
        "canvas-deep": "#010413",
        panel: "rgba(15, 23, 42, 0.55)",
        "panel-solid": "#0f172a",
        "panel-raised": "#111827",
        brand: {
          DEFAULT: "#2563eb",
          hover: "#3b82f6",
          soft: "rgba(37, 99, 235, 0.12)",
          ring: "rgba(37, 99, 235, 0.35)",
        },
        subtle: "rgba(255, 255, 255, 0.06)",
        "subtle-strong": "rgba(255, 255, 255, 0.10)",
      },
      fontSize: {
        micro: ["10px", { lineHeight: "14px", letterSpacing: "0.12em" }],
        mini: ["11px", { lineHeight: "16px" }],
      },
      borderRadius: {
        card: "1.25rem",
        panel: "1.75rem",
        hero: "2.5rem",
      },
      boxShadow: {
        "brand-glow": "0 0 40px rgba(37, 99, 235, 0.25)",
        "panel-lift": "0 10px 40px -10px rgba(0, 0, 0, 0.6)",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
      fontFamily: {
        display: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
