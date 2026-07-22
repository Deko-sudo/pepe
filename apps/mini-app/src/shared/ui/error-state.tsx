interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Ошибка",
  message = "Что-то пошло не так",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div className="text-4xl">⚠️</div>
      <h3 className="text-base font-medium text-text-primary">{title}</h3>
      <p className="text-sm text-text-secondary">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white"
        >
          Повторить
        </button>
      )}
    </div>
  );
}
