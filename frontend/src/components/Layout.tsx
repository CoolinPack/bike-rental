import React from "react";
import { NavLink, Outlet } from "react-router-dom";

interface Tab {
  to: string;
  label: string;
  icon: React.ReactNode;
}

export function Layout({ tabs }: { tabs: Tab[] }) {
  return (
    <>
      <Outlet />
      <nav className="tab-bar">
        <div className="tab-bar-inner">
          {tabs.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end
              className={({ isActive }) =>
                "tab-item" + (isActive ? " active" : "")
              }
            >
              <span className="tab-icon">{t.icon}</span>
              <span>{t.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </>
  );
}