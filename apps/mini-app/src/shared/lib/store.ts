import { create } from "zustand";

interface ModalState {
  aiSupportOpen: boolean;
  openAiSupport: () => void;
  closeAiSupport: () => void;
}

export const useModalStore = create<ModalState>((set) => ({
  aiSupportOpen: false,
  openAiSupport: () => set({ aiSupportOpen: true }),
  closeAiSupport: () => set({ aiSupportOpen: false }),
}));
