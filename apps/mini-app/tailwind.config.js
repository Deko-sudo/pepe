/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#05070a",
          secondary: "#090d13",
        },
        surface: {
          primary: "#0d121a",
          secondary: "#111823",
          elevated: "#182130",
        },
        border: {
          subtle: "rgba(255, 255, 255, 0.08)",
          active: "rgba(57, 139, 255, 0.72)",
        },
        text: {
          primary: "#f5f7fb",
          secondary: "#a4adbd",
          muted: "#70798a",
        },
        accent: {
          primary: "#398bff",
          secondary: "#65a7ff",
        },
        positive: "#35df8d",
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
