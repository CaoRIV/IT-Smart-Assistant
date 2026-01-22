/**
 * Application constants.
 */

export const APP_NAME = "it_smart_assistant";
export const APP_DESCRIPTION = "My FastAPI project";

// API Routes (Next.js internal routes)
export const API_ROUTES = {
  // Auth
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  LOGOUT: "/auth/logout",
  REFRESH: "/auth/refresh",
  ME: "/auth/me",

  // Health
  HEALTH: "/health",

  // Users
  USERS: "/users",

  // Chat (AI Agent)
  CHAT: "/chat",
} as const;

// Navigation routes
export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  DASHBOARD: "/dashboard",
  CHAT: "/chat",
  PROFILE: "/profile",
  SETTINGS: "/settings",
} as const;

// WebSocket URL (for chat - this needs to be direct to backend for WS)
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
