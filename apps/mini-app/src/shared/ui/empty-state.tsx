interface EmptyStateProps {
  title?: string;
  description?: string;
}

export function EmptyState({
  title = "Нет данных",
  description = "Данные пока не загружены",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8">
      <div className="text-4xl">📭</div>
      <h3 className="text-base font-medium text-text-primary">{title}</h3>
      <p className="text-sm text-text-secondary">{description}</p>
    </div>
  );
}
