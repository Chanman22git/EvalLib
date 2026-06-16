import {
  Activity,
  ClipboardCheck,
  GitCompareArrows,
  History,
  LayoutDashboard,
  ListChecks,
  MessagesSquare,
  ShieldCheck,
  Bot,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { BackendStatusBanner } from "@/components/BackendStatusBanner";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/agents", label: "Agents", icon: Bot },
  { to: "/evals", label: "Evals", icon: ListChecks },
  { to: "/conversations", label: "Conversations", icon: MessagesSquare },
  { to: "/traces", label: "Traces (turns)", icon: Activity },
  { to: "/regressions", label: "Regressions", icon: GitCompareArrows },
  { to: "/changes", label: "Change Events", icon: History },
  { to: "/governance", label: "Governance", icon: ShieldCheck },
];

export function Layout() {
  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col border-r bg-card">
        <div className="flex items-center gap-2 border-b px-5 py-4">
          <ClipboardCheck className="h-6 w-6 text-primary" />
          <div>
            <div className="text-lg font-semibold leading-none">EvalLib</div>
            <div className="text-xs text-muted-foreground">Agent Governance</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t px-5 py-3 text-xs text-muted-foreground">POC · single-tenant</div>
      </aside>
      <main className="flex flex-1 flex-col overflow-y-auto">
        <BackendStatusBanner />
        <div className="mx-auto w-full max-w-7xl p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
