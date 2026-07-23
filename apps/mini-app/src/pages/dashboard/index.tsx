import { useModalStore } from "@/shared/lib/store";
import { Modal } from "@/shared/ui";

export function Dashboard() {
  const { aiSupportOpen, closeAiSupport, openAiSupport } = useModalStore();

  return (
    <div className="flex flex-col gap-4 p-4">
      <header className="safe-area-top">
        <h1 className="text-2xl font-bold gradient-text">Pepe</h1>
      </header>

      <section className="card">
        <h2 className="text-sm text-text-secondary">Bitcoin за 24 часа</h2>
        <div className="mt-2">
          <p className="text-2xl font-bold text-text-primary">$118,420.50</p>
          <p className="text-sm text-positive">+2.74% за 24 часа</p>
        </div>
        <div className="mt-3 flex gap-4">
          <div>
            <p className="text-xs text-text-muted">High</p>
            <p className="text-sm font-medium text-text-primary">$119,370</p>
          </div>
          <div>
            <p className="text-xs text-text-muted">Low</p>
            <p className="text-sm font-medium text-text-primary">$114,820</p>
          </div>
        </div>
        <p className="mt-3 text-xs text-text-muted">Демонстрационные данные</p>
      </section>

      <section className="card">
        <h2 className="text-sm text-text-secondary">Общий фон рынка</h2>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xl">🟢</span>
          <span className="text-sm font-medium text-positive">Умеренный рост</span>
        </div>
        <p className="mt-3 text-xs text-text-muted">Демонстрационные данные</p>
      </section>

      <section className="card">
        <h2 className="text-sm text-text-secondary">Отслеживаемые активы</h2>
        <div className="mt-3 space-y-2">
          {[
            { symbol: "BTC", name: "Bitcoin", change: "+2.74%" },
            { symbol: "ETH", name: "Ethereum", change: "+1.82%" },
            { symbol: "XAU", name: "Золото", change: "+0.45%" },
          ].map((asset) => (
            <div key={asset.symbol} className="flex items-center justify-between rounded-xl bg-surface-secondary p-3">
              <div>
                <p className="text-sm font-medium text-text-primary">{asset.symbol}</p>
                <p className="text-xs text-text-muted">{asset.name}</p>
              </div>
              <span className="text-sm text-positive">{asset.change}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-text-muted">Демонстрационные данные</p>
      </section>

      <section className="card">
        <h2 className="text-sm text-text-secondary">Текущая торговая сессия</h2>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xl">🌙</span>
          <div>
            <p className="text-sm font-medium text-text-primary">Азиатская сессия</p>
            <p className="text-xs text-text-muted">03:00 — 12:00 MSK</p>
          </div>
        </div>
        <p className="mt-3 text-xs text-text-muted">Демонстрационные данные</p>
      </section>

      <section className="card">
        <h2 className="text-sm text-text-secondary">Последняя сводка</h2>
        <div className="mt-2">
          <p className="text-sm text-text-primary">Рынок показывает умеренную положительную динамику. Bitcoin укрепился выше $118,000.</p>
        </div>
        <p className="mt-3 text-xs text-text-muted">Демонстрационные данные</p>
      </section>

      <button
        onClick={openAiSupport}
        className="card flex items-center gap-3"
      >
        <span className="text-xl">🤖</span>
        <div className="text-left">
          <p className="text-sm font-medium text-text-primary">AI Support</p>
          <p className="text-xs text-text-muted">Beta</p>
        </div>
        <span className="ml-auto text-text-muted">›</span>
      </button>

      <section className="card border-border-subtle">
        <p className="text-xs leading-relaxed text-text-muted">
          Демонстрационный интерфейс. Все данные на этом экране являются
          моковыми и не отражают реальную рыночную информацию. Торговые
          решения на основе этой информации приниматься не должны.
        </p>
      </section>

      <Modal isOpen={aiSupportOpen} onClose={closeAiSupport} title="AI Support">
        <p className="text-sm text-text-secondary">
          Ожидайте, функция находится в разработке.
        </p>
      </Modal>
    </div>
  );
}
