import { create } from "zustand";
import { Me, Role } from "../types";

interface AuthState {
  me: Me | null;
  initData: string | null;
  mode: Role | "auto";
  setMe: (me: Me) => void;
  setInitData: (data: string) => void;
  setMode: (mode: Role | "auto") => void;
  clear: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  me: null,
  initData: null,
  mode: "auto",
  setMe: (me) => set({ me }),
  setInitData: (initData) => set({ initData }),
  setMode: (mode) => set({ mode }),
  clear: () => set({ me: null, initData: null, mode: "auto" }),
}));