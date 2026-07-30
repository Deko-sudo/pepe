import { Link, useLocation } from "react-router-dom";
import { Activity, BarChart3, FileText, Home, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
  /** Tab whose active state depends on the URL hash, not just the pathname. */
  hashTab?: boolean;
}

const SESSION_HASH = "#session-card";

const navItems: NavItem[] = [
  { to: "/", icon: Home, label: "Главная" },
  { to: "/markets", icon: BarChart3, label: "Рынки" },
  { to: `/${SESSION_HASH}`, icon: Activity, label: "Сессия", hashTab: true },
  { to: "/reports", icon: FileText, label: "Сводки" },
  { to: "/settings", icon: Settings, label: "Настройки" },
];

export function BottomNav() {
  const location = useLocation();

  const isItemActive = (item: NavItem): boolean => {
    // The Session tab lives on the home pathname but is only active when its
    // hash is present; React Router path matching cannot distinguish it from
    // Home, so we resolve both the pathname and the hash explicitly.
    if (item.hashTab) {
      return location.pathname === "/" && location.hash === SESSION_HASH;
    }
    if (item.to === "/") {
      return location.pathname === "/" && location.hash !== SESSION_HASH;
    }
    return location.pathname === item.to;
  };

  return (
    <nav className="bottom-nav-shell safe-area-bottom" aria-label="Основная навигация">
      <div className="bottom-nav-inner">
        {navItems.map((item, index) => {
          const active = isItemActive(item);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`bottom-nav-item ${active ? "is-active" : ""} ${
                index === 2 ? "bottom-nav-primary" : ""
              }`}
              aria-current={active ? "page" : undefined}
            >
              <span className="bottom-nav-icon">
                <item.icon size={19} strokeWidth={1.7} />
              </span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
