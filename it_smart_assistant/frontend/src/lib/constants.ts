/**
 * Application constants.
 */

export const APP_NAME = "IT - Smart - UTC";
export const APP_DESCRIPTION = "Trợ lý tư vấn thông minh dành cho sinh viên UTC";

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
  KNOWLEDGE_ADMIN: "/knowledge-admin",
  PROFILE: "/profile",
  SETTINGS: "/settings",
} as const;

// WebSocket URL (for chat - this needs to be direct to backend for WS)
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
