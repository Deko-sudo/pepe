import React, { useCallback, useEffect, useId, useLayoutEffect, useRef } from "react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  returnFocusRef?: React.RefObject<HTMLElement | null>;
}

export function Modal({ isOpen, onClose, title, children, returnFocusRef }: ModalProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const restorePreviousFocus = useCallback(() => {
    const previousFocus = previousFocusRef.current;
    const focusTarget = previousFocus?.isConnected
      ? previousFocus
      : previousFocus?.id
        ? document.getElementById(previousFocus.id)
        : null;
    focusTarget?.focus();
  }, []);

  const close = useCallback(() => {
    onClose();
    window.requestAnimationFrame(restorePreviousFocus);
  }, [onClose, restorePreviousFocus]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    },
    [close]
  );

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleKeyDown]);

  useLayoutEffect(() => {
    if (!isOpen) return;
    previousFocusRef.current = returnFocusRef?.current
      ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    closeButtonRef.current?.focus();
  }, [isOpen, returnFocusRef]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/60" onClick={close} aria-hidden="true" />
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        className="relative z-10 mx-4 w-full max-w-sm rounded-[20px] bg-surface-elevated p-6"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
      >
        {title && (
          <h2 id={titleId} className="mb-4 text-lg font-semibold text-text-primary">
            {title}
          </h2>
        )}
        {children}
        <button
          ref={closeButtonRef}
          onClick={close}
          className="mt-4 w-full rounded-xl bg-accent-primary py-3 text-sm font-medium text-white touch-target"
        >
          Понятно
        </button>
      </div>
    </div>
  );
}
