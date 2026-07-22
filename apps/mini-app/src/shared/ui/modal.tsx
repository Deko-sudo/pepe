import React, { useEffect, useCallback } from "react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/60" onClick={onClose} />
      <div className="relative z-10 mx-4 w-full max-w-sm rounded-[20px] bg-surface-elevated p-6">
        {title && (
          <h2 className="mb-4 text-lg font-semibold text-text-primary">
            {title}
          </h2>
        )}
        {children}
        <button
          onClick={onClose}
          className="mt-4 w-full rounded-xl bg-accent-primary py-3 text-sm font-medium text-white touch-target"
        >
          Понятно
        </button>
      </div>
    </div>
  );
}
