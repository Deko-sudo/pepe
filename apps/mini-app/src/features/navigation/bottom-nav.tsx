import { Link, NavLink } from "react-router-dom";
import { Activity, BarChart3, FileText, Home, Settings } from "lucide-react";

const navItems = [
  { to: "/", icon: Home, label: "Главная" },
  { to: "/markets", icon: BarChart3, label: "Рынки" },
  { to: "/#session-card", icon: Activity, label: "Сессия", anchor: true },
  { to: "/reports", icon: FileText, label: "Сводки" },
  { to: "/settings", icon: Settings, label: "Настройки" },
];

export function BottomNav() {
  return (
    <nav className="bottom-nav-shell safe-area-bottom" aria-label="Основная навигация">
      <div className="bottom-nav-inner">
        {navItems.map((item, index) => item.anchor ? (
          <Link key={item.to} to={item.to} className="bottom-nav-item bottom-nav-primary">
            <span className="bottom-nav-icon"><item.icon size={19} strokeWidth={1.7} /></span>
            <span>{item.label}</span>
          </Link>
        ) : (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => `bottom-nav-item ${isActive ? "is-active" : ""} ${index === 2 ? "bottom-nav-primary" : ""}`}
          >
            <span className="bottom-nav-icon"><item.icon size={19} strokeWidth={1.7} /></span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
