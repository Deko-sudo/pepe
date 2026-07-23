import { NavLink } from "react-router-dom";
import { Home, BarChart3, FileText, Settings } from "lucide-react";

const navItems = [
  { to: "/", icon: Home, label: "Главная" },
  { to: "/markets", icon: BarChart3, label: "Рынки" },
  { to: "/reports", icon: FileText, label: "Сводки" },
  { to: "/settings", icon: Settings, label: "Настройки" },
];

export function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 safe-area-bottom border-t border-border-subtle bg-bg-secondary">
      <div className="mx-auto flex max-w-[430px] justify-around py-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex min-h-[44px] min-w-[44px] flex-col items-center gap-1 rounded-lg px-3 py-1 transition-colors ${
                isActive ? "text-accent-primary" : "text-text-muted"
              }`
            }
          >
            <item.icon size={22} />
            <span className="text-[10px]">{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
