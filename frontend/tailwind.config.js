/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        clinical: {
          50: "#f0f9f8",
          100: "#d9f0ee",
          200: "#b7e2de",
          500: "#2a9d8f",
          600: "#238b7f",
          700: "#1d7268",
          900: "#134e48",
        },
        story: {
          warm: "#f4a261",
          calm: "#e9c46a",
          trust: "#264653",
        },
      },
      fontFamily: {
        sans: ["'Source Sans 3'", "system-ui", "sans-serif"],
        display: ["'Fraunces'", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
