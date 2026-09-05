import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{ts,tsx}",
    "./index.html",
  ],
  theme: {
    extend: {
      // ------------------------------------------------------------------------
      // 1. SPACE & AEROSPACE COLOR DESIGN TOKENS
      // ------------------------------------------------------------------------
      colors: {
        // Space dark backgrounds
        space: {
          950: "#050811", // Deep vacuum black
          900: "#0a0f1d", // Primary station chassis
          850: "#0f1629", // Surface panel card
          800: "#161f36", // Elevated module layer
          700: "#222f4d", // Border subtle
          600: "#36476e", // Border hover
        },
        // Telemetry primary blue
        telemetry: {
          50: "#eef6ff",
          100: "#d9ebff",
          400: "#3894ff",
          500: "#0070f3", // Primary telemetry brand
          600: "#0056cc",
          900: "#002b66",
        },
        // Flight status states
        nominal: {
          DEFAULT: "#00e676", // Green nominal operational state
          foreground: "#003314",
          dim: "rgba(0, 230, 118, 0.15)",
        },
        advisory: {
          DEFAULT: "#ffd600", // Yellow advisory
          foreground: "#332b00",
          dim: "rgba(255, 214, 0, 0.15)",
        },
        hazard: {
          DEFAULT: "#ff3d00", // Red critical / emergency
          foreground: "#ffffff",
          dim: "rgba(255, 61, 0, 0.15)",
        },
      },

      // ------------------------------------------------------------------------
      // 2. TYPOGRAPHY DESIGN TOKENS
      // ------------------------------------------------------------------------
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "Menlo", "monospace"],
      },
      fontSize: {
        "telemetry-xs": ["0.6875rem", { lineHeight: "0.875rem", letterSpacing: "0.05em" }],
        "telemetry-sm": ["0.75rem", { lineHeight: "1rem", letterSpacing: "0.025em" }],
        "telemetry-base": ["0.875rem", { lineHeight: "1.25rem" }],
        "telemetry-lg": ["1.125rem", { lineHeight: "1.5rem" }],
        "telemetry-xl": ["1.5rem", { lineHeight: "2rem" }],
      },

      // ------------------------------------------------------------------------
      // 3. ELEVATION & SHADOW TOKENS
      // ------------------------------------------------------------------------
      boxShadow: {
        panel: "0 4px 20px -2px rgba(0, 0, 0, 0.65)",
        hud: "0 0 15px rgba(0, 112, 243, 0.25)",
        glowNominal: "0 0 12px rgba(0, 230, 118, 0.4)",
        glowHazard: "0 0 15px rgba(255, 61, 0, 0.5)",
      },

      // ------------------------------------------------------------------------
      // 4. RADIUS TOKENS
      // ------------------------------------------------------------------------
      borderRadius: {
        station: "4px",
        cockpit: "8px",
        viewport: "12px",
      },

      // ------------------------------------------------------------------------
      // 5. MOTION TOKENS (Micro-interactions & Scanlines)
      // ------------------------------------------------------------------------
      animation: {
        "telemetry-pulse": "telemetryPulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "beacon-flash": "beaconFlash 1s ease-in-out infinite",
      },
      keyframes: {
        telemetryPulse: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        beaconFlash: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
