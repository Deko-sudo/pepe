export function OfflineState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div className="text-4xl">📡</div>
      <h3 className="text-base font-medium text-text-primary">Нет сети</h3>
      <p className="text-sm text-text-secondary">
        Проверьте подключение к интернету
      </p>
    </div>
  );
}
