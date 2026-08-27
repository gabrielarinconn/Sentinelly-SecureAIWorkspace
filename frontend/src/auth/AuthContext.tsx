import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, clearStoredTokens, getStoredTokens, setSessionExpiredListener, storeTokens } from "../api/client";
import type { CurrentUser } from "../api/types";

interface AuthContextValue {
  user: CurrentUser | null;
  status: "loading" | "authenticated" | "anonymous";
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");

  const loadCurrentUser = async () => {
    try {
      setUser(await api.getCurrentUser());
      setStatus("authenticated");
    } catch {
      clearStoredTokens();
      setUser(null);
      setStatus("anonymous");
    }
  };

  useEffect(() => {
    setSessionExpiredListener(() => {
      setUser(null);
      setStatus("anonymous");
    });
    if (getStoredTokens()) {
      void loadCurrentUser();
    } else {
      setStatus("anonymous");
    }
    return () => setSessionExpiredListener(null);
  }, []);

  const login = async (email: string, password: string) => {
    storeTokens(await api.login(email, password));
    await loadCurrentUser();
  };

  const logout = async () => {
    const tokens = getStoredTokens();
    if (tokens) {
      try {
        await api.logout(tokens.refresh_token);
      } catch {
        // logout es best-effort del lado del cliente — igual limpiamos el estado local
      }
    }
    clearStoredTokens();
    setUser(null);
    setStatus("anonymous");
  };

  return <AuthContext.Provider value={{ user, status, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
