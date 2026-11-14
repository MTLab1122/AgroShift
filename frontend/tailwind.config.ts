import { type Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          50: "#f0f7f3",
          100: "#dcf0e3",
          200: "#bae1ca",
          300: "#8eccaa",
          400: "#5db185",
          500: "#3a9565",
          600: "#2a7850",
          700: "#226041",
          800: "#1d4c35",
          900: "#183f2d",
          950: "#0c2319",
        },
        agrigreen: {
          50: "#f4fbf4",
          100: "#e5f7e5",
          200: "#cbedcc",
          300: "#a3dea5",
          400: "#71c574",
          500: "#48a94c",
          600: "#368a3a",
          700: "#2d6d30",
          800: "#27572a",
          900: "#214824",
          950: "#0d2710",
        },
        earth: {
          50: "#fbf9f5",
          100: "#f5f0e6",
          200: "#ebdeca",
          300: "#ddc6a6",
          400: "#cca87d",
          500: "#bf915f",
          600: "#b17e52",
          700: "#946445",
          800: "#77513b",
          900: "#614332",
        },
      },
    },
  },
  plugins: [],
};
export default config;
