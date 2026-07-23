export type DataState = "loading" | "success" | "empty" | "stale" | "offline" | "error";

export interface DataStateWrapperProps {
  state: DataState;
  children: React.ReactNode;
  onRetry?: () => void;
}
