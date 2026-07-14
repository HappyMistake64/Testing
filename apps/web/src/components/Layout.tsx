import { NavLink, Outlet } from "react-router-dom";
import "./Layout.css";

export function Layout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span>FADE</span> Platform
        </div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Portfolio
          </NavLink>
          <NavLink to="/projects/new" className={({ isActive }) => (isActive ? "active" : "")}>
            Add Project
          </NavLink>
          <NavLink to="/system" className={({ isActive }) => (isActive ? "active" : "")}>
            System Status
          </NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
