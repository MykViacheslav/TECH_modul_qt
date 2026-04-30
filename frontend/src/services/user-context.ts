"use client";

import { useState, useCallback, useEffect, createContext, useContext } from "react";
import { TechModulAPI, type SelectedUser } from "./api";

// We keep makeSelectedUser backward compatible if anything imports it directly,
// though we'll primarily rely on backend auth now.
export function makeSelectedUser(raw: {
  id: number;
  name: string;
  role: string;
  avatar_color?: string;
}): SelectedUser {
  return {
    id: raw.id,
    name: raw.name,
    role: raw.role,
    avatar_color: raw.avatar_color ?? "#1e3a5f",
    initials: raw.name
      .split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2),
  };
}

export function useCurrentUser() {
  const [user, setUserState] = useState<SelectedUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Initialize from backend session on mount
  useEffect(() => {
    let mounted = true;
    TechModulAPI.getMe()
      .then((data) => {
        if (mounted) {
          if (data && data.name) {
            setUserState(makeSelectedUser(data));
          } else {
            setUserState(null);
          }
        }
      })
      .catch(() => {
        if (mounted) setUserState(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
      
    return () => { mounted = false; };
  }, []);

  const setUser = useCallback((u: SelectedUser | null) => {
    setUserState(u);
  }, []);

  const logout = useCallback(async () => {
    try {
      await TechModulAPI.logout();
    } catch (e) {
      console.error("Logout error", e);
    }
    setUserState(null);
    window.location.href = "/login";
  }, []);

  return [user, setUser, loading, logout] as const;
}

// Backward compatibility (noop)
export function saveUserToStorage() {}
export function clearUserFromStorage() {}
export function parseUserFromStorage() { return null; }
