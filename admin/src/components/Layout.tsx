import { NavLink, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { setToken } from "../api";

const navCls = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
    isActive
      ? "bg-cyan-500/15 text-cyan-300 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.25)]"
      : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
  }`;

export function Layout({ children }: { children?: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 border-r border-white/10 bg-orbit-900/70 p-6 md:flex md:flex-col">
        <div className="mb-10">
          <p className="font-display text-lg font-semibold uppercase tracking-[0.2em] text-cyan-400">
            Command
          </p>
          <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">
            Asteroid Dodger ops
          </p>
        </div>
        <nav className="flex flex-col gap-1">
          <NavLink to="/" end className={navCls}>
            <span aria-hidden>◆</span> Overview
          </NavLink>
          <NavLink to="/players" className={navCls}>
            <span aria-hidden>◎</span> Players
          </NavLink>
          <NavLink to="/messages" className={navCls}>
            <span aria-hidden>✉</span> Campaigns
          </NavLink>
        </nav>
        <div className="mt-auto pt-10">
          <button
            type="button"
            className="btn-ghost w-full justify-center text-xs text-slate-500 hover:text-orange-300"
            onClick={() => {
              setToken(null);
              window.location.assign("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6 md:p-10">
        {children ?? <Outlet />}
      </main>
      <MobileBar />
    </div>
  );
}

function MobileBar() {
  const item = `${navCls({ isActive: false })} flex-1 justify-center text-center text-xs`;
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-white/10 bg-orbit-900/95 p-1 backdrop-blur md:hidden">
      <NavLink to="/" end className={({ isActive }) => `${item} ${isActive ? "bg-cyan-500/15 text-cyan-300" : ""}`}>
        Home
      </NavLink>
      <NavLink
        to="/players"
        className={({ isActive }) => `${item} ${isActive ? "bg-cyan-500/15 text-cyan-300" : ""}`}
      >
        Users
      </NavLink>
      <NavLink
        to="/messages"
        className={({ isActive }) => `${item} ${isActive ? "bg-cyan-500/15 text-cyan-300" : ""}`}
      >
        Send
      </NavLink>
    </nav>
  );
}
