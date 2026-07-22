export function Settings() {
  return (
    <div className="flex flex-col gap-4 p-4">
      <header className="safe-area-top">
        <h1 className="text-2xl font-bold text-text-primary">Настройки</h1>
      </header>

      <section className="card">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-primary">Тёмная тема</span>
            <div className="h-6 w-11 rounded-full bg-accent-primary p-0.5">
              <div className="h-5 w-5 rounded-full bg-white translate-x-5" />
            </div>
          </div>

          <div className="border-t border-border-subtle" />

          <div className="flex items-center justify-between">
            <span className="text-sm text-text-primary">Уведомления</span>
            <div className="h-6 w-11 rounded-full bg-accent-primary p-0.5">
              <div className="h-5 w-5 rounded-full bg-white translate-x-5" />
            </div>
          </div>

          <div className="border-t border-border-subtle" />

          <div className="flex items-center justify-between">
            <span className="text-sm text-text-primary">Валюта</span>
            <span className="text-sm text-text-secondary">USD</span>
          </div>

          <div className="border-t border-border-subtle" />

          <div className="flex items-center justify-between">
            <span className="text-sm text-text-primary">Версия</span>
            <span className="text-sm text-text-secondary">0.1.0</span>
          </div>
        </div>
      </section>
    </div>
  );
}
