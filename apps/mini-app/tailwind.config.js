/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#090b10",
          secondary: "#0f131d",
        },
        surface: {
          primary: "#141925",
          secondary: "#1a2030",
          elevated: "#202738",
        },
        border: {
          subtle: "rgba(255, 255, 255, 0.08)",
          active: "rgba(124, 92, 252, 0.65)",
        },
        text: {
          primary: "#f5f7fb",
          secondary: "#a4adbd",
          muted: "#70798a",
        },
        accent: {
          primary: "#7c5cfc",
          secondary: "#25c7f8",
        },
        positive: "#21c77a",
        negative: "#f05252",
        warning: "#f5a524",
      },
      borderRadius: {
        card: "16px",
      },
    },
  },
  plugins: [],
};
