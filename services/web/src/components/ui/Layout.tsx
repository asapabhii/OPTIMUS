import { Outlet, NavLink, useNavigate } from "react-router-dom";
import {
  MessageSquare,
  Network,
  ListChecks,
  Shield,
  Cable,
  Wrench,
  Plus,
  LogOut,
  Settings,
} from "lucide-react";
import { logout, getUsername } from "../../api/client";

const navItems = [
  {
    to: "/ask",
    label: "Ask",
    icon: MessageSquare,
    description: "Query your data",
  },
  {
    to: "/browse",
    label: "Browse",
    icon: Network,
    description: "Entity graph",
  },
  {
    to: "/decisions",
    label: "Decisions",
    icon: ListChecks,
    description: "Audit trail",
  },
  {
    to: "/canon",
    label: "Canon",
    icon: Shield,
    description: "Company knowledge",
  },
  {
    to: "/sources",
    label: "Sources",
    icon: Cable,
    description: "Manage connections",
  },
  {
    to: "/work",
    label: "Work",
    icon: Wrench,
    description: "Agent and delegation",
  },
  {
    to: "/admin",
    label: "Admin",
    icon: Shield,
    description: "Governance and config",
  },
];

export function Layout() {
  const navigate = useNavigate();

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-[240px] border-r border-border flex flex-col bg-card">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-border">
          <div className="flex items-center gap-2.5">
            <img src="/logo.svg" alt="Optimus" className="w-8 h-8 rounded-lg" />
            <div>
              <h1 className="text-[15px] font-semibold tracking-tight leading-none">
                Optimus
              </h1>
              <span className="text-[10px] text-muted-foreground font-medium tracking-widest uppercase">
                TrustLayer
              </span>
            </div>
          </div>
        </div>

        {/* Connect button */}
        <div className="px-4 pt-4 pb-2">
          <button
            onClick={() => navigate("/sources")}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-primary/30 text-primary text-sm font-medium hover:bg-primary/5 hover:border-primary/50 transition-all"
          >
            <Plus className="h-4 w-4" />
            Manage Sources
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-0.5">
          {navItems.map(({ to, label, icon: Icon, description }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                  isActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                }`
              }
            >
              <Icon className="h-[18px] w-[18px]" />
              <div className="flex flex-col">
                <span className="leading-tight">{label}</span>
                <span className="text-[10px] text-muted-foreground leading-tight">
                  {description}
                </span>
              </div>
            </NavLink>
          ))}
        </nav>

        {/* Bottom */}
        <div className="p-3 border-t border-border space-y-1">
          <div className="px-3 py-2 rounded-lg bg-accent/30">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground font-medium">
                {getUsername()}
              </span>
              <span className="flex items-center gap-1.5 text-[11px] text-green-500 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                Online
              </span>
            </div>
          </div>
          <button
            onClick={() => navigate("/settings")}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-all text-left"
          >
            <Settings className="h-4 w-4" />
            Account settings
          </button>
          <button
            onClick={() => logout()}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all text-left"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden bg-background">
        <Outlet />
      </main>
    </div>
  );
}
