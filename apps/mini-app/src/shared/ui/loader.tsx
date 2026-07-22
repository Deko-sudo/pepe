interface LoaderProps {
  text?: string;
}

export function Loader({ text = "Загрузка..." }: LoaderProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-primary border-t-transparent" />
      <span className="text-sm text-text-secondary">{text}</span>
    </div>
  );
}
