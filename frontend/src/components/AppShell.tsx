"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Ruler,
  Layers,
  Box,
  Database,
  Wallet,
  Receipt,
  Settings,
  Home,
  Hammer,
  Cpu,
  Droplets,
  Workflow,
  LogOut,
  Maximize,
  UserCircle2,
  TriangleAlert,
  Monitor,
  Lightbulb,
  TestTube2,
  Telescope,
  CalendarClock,
  BellRing,
  ClipboardList,
  FileText,
  Scissors,
  Landmark,
  Package,
  FileArchive,
  FolderLock,
  Truck,
  ShoppingCart,
  Clock,
  ListTodo,
  ShieldCheck,
  Users,
  Factory,
  HardHat,
  MonitorCheck,
  ChevronDown,
  ChevronRight,
  Wrench,
} from "lucide-react";
import React from "react";
import clsx from "clsx";
import { TechModulAPI, type ProjectRecord } from "@/services/api";
import { useSelectedProjectId } from "@/services/project-context";
import { useCurrentUser, clearUserFromStorage } from "@/services/user-context";
import PersistentAgent from "./PersistentAgent";
import { ModuleStatusDot } from "./ModuleStatusBadge";
import { getModuleStatus, STATUS_LABEL } from "@/config/moduleStatus";
import { motion } from "framer-motion";
import { type NotificationSummary } from "@/services/api";

type NavItem = {
  href: string;
  label: string;
  icon: any;
  adminOnly?: boolean;
};

type NavGroup = {
  id: string;
  label: string;
  icon: any;
  items: NavItem[];
  adminOnly?: boolean;
};

const NAV_GROUPS: NavGroup[] = [
  {
    id: "system",
    label: "Zarządzanie",
    icon: Monitor,
    items: [
      { href: "/overview", label: "Overview", icon: Telescope },
      { href: "/dashboard", label: "Dashboard", icon: Home },
      { href: "/kri", label: "KRI", icon: TriangleAlert },
    ]
  },
  {
    id: "design",
    label: "Projektowanie",
    icon: Ruler,
    items: [
      { href: "/workspace?mode=room", label: "Ściana", icon: Ruler },
      { href: "/workspace?mode=modules", label: "Moduły", icon: Box },
      { href: "/workspace?mode=komplet", label: "Komplet", icon: Layers },
      { href: "/workspace?mode=struktura", label: "Struktura", icon: Database },
      { href: "/workspace?mode=connections", label: "Przyłącza", icon: Droplets },
    ]
  },
  {
    id: "production",
    label: "Produkcja",
    icon: Factory,
    items: [
      { href: "/orders", label: "Zlecenia", icon: FileText },
      { href: "/services", label: "Usługi", icon: Wrench },
      { href: "/workspace/production", label: "Główny Workflow", icon: Workflow },
      { href: "/stations/cnc", label: "CNC", icon: Cpu },
      { href: "/stations/oklejanie", label: "Oklejarka", icon: Layers },
      { href: "/stations/lakiernia", label: "Lakiernia", icon: Droplets },
      { href: "/stations/montaz", label: "Montaż", icon: Hammer },
      { href: "/stations/pakowanie", label: "Pakowanie", icon: Box },
      { href: "/production/handoff", label: "Warsztat / Akceptacje", icon: MonitorCheck },
      { href: "/fulfillment", label: "Wysyłka / Montaż", icon: Truck },
    ]
  },
  {
    id: "procurement",
    label: "Logistyka",
    icon: Package,
    items: [
      { href: "/procurement/availability", label: "Materiały", icon: Package },
      { href: "/procurement/readiness", label: "Gotowość", icon: ShieldCheck },
      { href: "/procurement/suggestions", label: "Potrzeby", icon: ShoppingCart },
      { href: "/procurement/execution", label: "Zakupy", icon: ListTodo },
    ]
  },
  {
    id: "finance",
    label: "Finanse",
    icon: Wallet,
    items: [
      { href: "/finance", label: "Zestawienie", icon: Wallet },
      { href: "/finance/fixed-costs", label: "Koszty Stałe", icon: Receipt },
      { href: "/cashboxes", label: "Kasy / Bank", icon: Landmark },
      { href: "/time-tracking", label: "Czas Pracy", icon: Clock },
    ]
  },
  {
    id: "admin",
    label: "Administracja",
    icon: Settings,
    adminOnly: true,
    items: [
      { href: "/database", label: "Bazy Danych", icon: Database },
      { href: "/admin/projects", label: "Projekty", icon: FolderLock },
      { href: "/admin/users", label: "Użytkownicy", icon: Users },
      { href: "/admin/backups", label: "Backupy", icon: FileArchive },
      { href: "/settings", label: "Ustawienia", icon: Settings },
    ]
  }
];

const QUICK_NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dash", icon: Home },
  { href: "/biuro", label: "BIURO", icon: Monitor },
  { href: "/orders/new", label: "Zlecenia", icon: FileText },
  { href: "/stations/cnc", label: "CNC", icon: Cpu },
  { href: "/stations/oklejanie", label: "Oklej.", icon: Layers },
  { href: "/stations/lakiernia", label: "Lakier.", icon: Droplets },
  { href: "/stations/montaz", label: "Montaż", icon: Hammer },
  { href: "/stations/pakowanie", label: "Pak.", icon: Box },
  { href: "/notifications", label: "Alerty", icon: BellRing },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [projects, setProjects] = React.useState<ProjectRecord[]>([]);
  const [projectsError, setProjectsError] = React.useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useSelectedProjectId(1);
  const [currentUser, , , logout] = useCurrentUser();
  const [notifSummary, setNotifSummary] = React.useState<NotificationSummary | null>(null);
  const [expandedGroup, setExpandedGroup] = React.useState<string>("system");

  React.useEffect(() => {
    let active = true;
    const loadProjects = async () => {
      try {
        const list = await TechModulAPI.getProjects();
        if (!active) return;
        setProjects(list ?? []);
        if ((list ?? []).length > 0 && !(list ?? []).some((p) => Number(p.id) === selectedProjectId)) {
          setSelectedProjectId(Number(list[0].id));
        }
      } catch (e: any) {
        if (!active) return;
        setProjectsError(e?.message ?? "Bad pobierania projektow");
      }
    };
    loadProjects();
    return () => {
      active = false;
    };
  }, [selectedProjectId, setSelectedProjectId]);

  React.useEffect(() => {
    const loadNotifs = async () => {
      try {
        const sum = await TechModulAPI.getNotificationSummary();
        setNotifSummary(sum);
      } catch (e) {
        console.error("Failed to load notifications", e);
      }
    };
    loadNotifs();
    const interval = setInterval(loadNotifs, 60000);
    return () => clearInterval(interval);
  }, []);

  const selectedProject = projects.find((p) => Number(p.id) === selectedProjectId) ?? null;
  const visibleGroups = NAV_GROUPS.filter((group) =>
    currentUser?.role !== "admin" ? !group.adminOnly : true
  );
  const isItemActive = (href: string) => {
    const [basePath, query] = href.split("?");
    if (query) return pathname === basePath;
    return pathname === href || (href !== "/" && pathname.startsWith(`${href}/`));
  };
  const activeGroupId = visibleGroups.find((group) =>
    group.items.some((item) => isItemActive(item.href))
  )?.id;

  React.useEffect(() => {
    if (activeGroupId) setExpandedGroup(activeGroupId);
  }, [activeGroupId]);

  return (
    <div className="h-screen w-screen bg-[#070708] flex flex-col overflow-hidden relative">
      {/* Decorative 'Desktop' UI Element */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#fff 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
      <div className="absolute top-4 right-10 text-[10px] text-slate-700 font-mono select-none">SYSTEM_STATUS: PROD_DEV_ACTIVE // WS_LIGNUM_WEB</div>
      {/* DEVELOPMENT WINDOW WRAPPER - FULL SCREEN UI */}
      <div className="relative flex flex-col w-full h-full bg-[#1e1e1e] text-slate-100 font-sans overflow-hidden">

        {/* Fake OS Window Title Bar (Dense) */}
        <div className="h-6 bg-[#121214] border-b border-[#222] flex items-center justify-center px-4 relative shrink-0">
          <div className="absolute left-4 flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
          </div>
          <span className="text-[9px] text-slate-500 font-medium tracking-widest">TECH MODU 2.0 (CAD DEVELOPMENT MODE)</span>
        </div>

        {/* TOP MENU BAR (CAD Style) */}
        <header className="h-10 shrink-0 bg-[#2d2d2d] border-b border-[#111] flex items-center justify-between px-4 text-[11px] select-none z-20 relative">
          <div className="flex min-w-0 items-center gap-3">
            <div className="font-bold text-blue-500 tracking-widest uppercase mr-4">TechModul CAD</div>
            <button className="hover:bg-[#3e3e42] px-2 py-1 rounded-sm transition-colors text-slate-300">Plik</button>
            <button className="hover:bg-[#3e3e42] px-2 py-1 rounded-sm transition-colors text-slate-300">Edycja</button>
            <button className="hover:bg-[#3e3e42] px-2 py-1 rounded-sm transition-colors text-slate-300">Widok</button>
            <button className="hover:bg-[#3e3e42] px-2 py-1 rounded-sm transition-colors text-slate-300">Wstaw</button>
            <button className="hover:bg-[#3e3e42] px-2 py-1 rounded-sm transition-colors text-slate-300">Narzedzia</button>
            <div className="ml-2 flex min-w-0 items-center gap-1 border-l border-white/10 pl-3">
              {QUICK_NAV_ITEMS.slice(1, 8).map((item) => {
                const isActive = isItemActive(item.href);
                const ItemIcon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "flex h-7 items-center gap-1.5 rounded-sm border px-2 text-[10px] font-semibold transition-colors",
                      isActive
                        ? "border-blue-500/40 bg-blue-500/15 text-blue-300"
                        : "border-[#3e3e42] bg-[#242424] text-slate-400 hover:border-blue-500/30 hover:text-slate-100"
                    )}
                  >
                    <ItemIcon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.6} />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Project Selector embedded in Top Bar */}
          <div className="flex items-center gap-3">
            <span className="text-slate-400">Aktywny projekt:</span>
            <select
              value={String(selectedProjectId)}
              onChange={(e) => setSelectedProjectId(Number(e.target.value))}
              className="bg-[#1e1e1e] border border-[#3e3e42] rounded-sm px-2 py-1 text-slate-200 outline-none focus:border-blue-500 min-w-[200px]"
              disabled={projects.length === 0}
            >
              {projects.length === 0 ? (
                <option value={String(selectedProjectId)}>Projekt #{selectedProjectId}</option>
              ) : (
                projects.map((project) => (
                  <option key={project.id} value={String(project.id)}>
                    [{project.id}] {project.title} - {project.client_name || "Brak Klienta"}
                  </option>
                ))
              )}
            </select>
            {projectsError && <span className="text-red-400 font-bold">{projectsError}</span>}

            <button
              onClick={() => {
                if (document.fullscreenElement) {
                  document.exitFullscreen();
                } else {
                  document.documentElement.requestFullscreen();
                }
              }}
              className="hover:bg-[#3e3e42] p-1.5 rounded-sm ml-2"
              title="Peny Ekran"
            >
              <Maximize className="w-3.5 h-3.5" />
            </button>

            {/* Notification Badge */}
            <Link 
              href="/notifications"
              className={clsx(
                "ml-2 flex items-center gap-2 px-3 py-1.5 rounded-sm transition-all relative overflow-hidden group",
                notifSummary && notifSummary.total_urgent > 0 
                  ? "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30" 
                  : "hover:bg-[#3e3e42] text-slate-400"
              )}
              title={`${notifSummary?.total_urgent ?? 0} items require attention`}
            >
              <BellRing className={clsx("w-3.5 h-3.5", notifSummary && notifSummary.total_urgent > 0 && "animate-pulse")} />
              {notifSummary && notifSummary.total_urgent > 0 && (
                <span className="text-[10px] font-black">{notifSummary.total_urgent}</span>
              )}
              {notifSummary && notifSummary.total_urgent > 0 && (
                <motion.div 
                  className="absolute inset-0 bg-red-500/10 pointer-events-none"
                  initial={{ x: "-100%" }}
                  animate={{ x: "200%" }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                />
              )}
            </Link>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden">
          {/* LEFT TOOLBAR (quick access + compact groups) */}
          <aside className="w-52 shrink-0 bg-[#252526] border-r border-[#111] flex flex-col py-2 z-10">
            <nav className="flex-1 flex flex-col gap-1 w-full overflow-y-auto custom-scrollbar px-2">
              {visibleGroups.map((group) => {
                const isAnyActive = group.items.some((item) => isItemActive(item.href));
                const GroupIcon = group.icon;
                const isExpanded = expandedGroup === group.id;

                return (
                  <section key={group.id} className="border-b border-white/5 pb-1 last:border-b-0">
                    <button
                      type="button"
                      onClick={() => setExpandedGroup((prev) => (prev === group.id ? "" : group.id))}
                      className={clsx(
                        "mb-1 flex h-7 w-full items-center gap-2 rounded-sm px-2 text-[10px] font-black uppercase tracking-[0.16em]",
                        isAnyActive ? "bg-[#303038] text-blue-300" : "text-slate-500"
                      )}
                    >
                      <GroupIcon className="h-4 w-4" strokeWidth={1.5} />
                      <span className="min-w-0 flex-1 truncate text-left">{group.label}</span>
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 shrink-0" strokeWidth={1.8} />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 shrink-0" strokeWidth={1.8} />
                      )}
                    </button>
                    {isExpanded ? (
                      <div className="space-y-0.5">
                        {group.items.map((item) => {
                          const isActive = isItemActive(item.href);
                          const ItemIcon = item.icon;
                          return (
                            <Link
                              key={item.href}
                              href={item.href}
                              className={clsx(
                                "flex h-7 items-center gap-2 rounded-sm px-2 pl-3 text-[11px] transition-colors",
                                isActive
                                  ? "bg-blue-500/15 text-blue-300 shadow-[inset_3px_0_0_rgba(59,130,246,0.95)]"
                                  : "text-slate-400 hover:bg-[#303033] hover:text-slate-100"
                              )}
                            >
                              <ItemIcon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.5} />
                              <span className="truncate">{item.label}</span>
                            </Link>
                          );
                        })}
                      </div>
                    ) : null}
                  </section>
                );
              })}
            </nav>

            <div className="mt-auto flex items-center gap-2 w-full px-2 pt-2 mb-2 border-t border-white/5">
              <button
                onClick={() => {
                  if (window.confirm("Czy na pewno chcesz się wylogować?")) {
                    logout();
                  }
                }}
                title={currentUser ? `${currentUser.name} - Wyloguj` : "Zaloguj"}
                className="h-9 w-9 rounded-full bg-[#1e1e1e] border border-[#3e3e42] flex items-center justify-center text-[10px] font-bold ring-1 ring-transparent hover:ring-red-500 transition-all overflow-hidden"
                style={currentUser ? { color: currentUser.avatar_color, borderColor: currentUser.avatar_color } : {}}
              >
                {currentUser ? currentUser.initials : <UserCircle2 className="w-4 h-4" />}
              </button>

              <button
                onClick={async () => {
                  if (window.confirm("Zakonczyc prace systemu?")) {
                    try { await fetch("http://localhost:8000/system/shutdown", { method: "POST" }); } catch (e) { }
                    setTimeout(() => { window.close(); window.location.href = "about:blank"; }, 500);
                  }
                }}
                className="h-9 flex-1 rounded-sm flex items-center justify-center gap-2 text-red-400 hover:bg-red-500 hover:text-white transition-colors text-[12px]"
                title="Zamknij"
              >
                <LogOut className="w-5 h-5" strokeWidth={1.5} />
                Zamknij
              </button>
            </div>
          </aside>

          {/* WORKSPACE AREA */}
          <main className="flex-1 bg-[#1e1e1e] overflow-auto custom-scrollbar relative">
            <div className="absolute inset-0 p-2 md:p-4">
              {children}
            </div>
          </main>
        </div>

        <PersistentAgent />
      </div>
    </div>
  );
}
