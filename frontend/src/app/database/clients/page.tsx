"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import {
  Users,
  Search,
  MapPin,
  History,
  Star,
  Plus,
  Building2,
  Loader2,
  ArrowLeft,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { TechModulAPI, type ClientRecord } from "@/services/api";

type ClientStatus = "active" | "vip" | "archived";
type ClientType = "person" | "b2b";

const FILTERS = [
  { id: "all", label: "Wszyscy" },
  { id: "active", label: "Aktywni" },
  { id: "vip", label: "VIP" },
  { id: "archived", label: "Archiwum" },
] as const;

function statusLabel(status: ClientStatus): string {
  if (status === "vip") return "VIP";
  if (status === "archived") return "Archiwum";
  return "Aktywny";
}

function initialsFromName(name: string): string {
  const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "--";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export default function ClientsDatabase() {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    location: "",
    type: "person" as ClientType,
    status: "active" as ClientStatus,
  });

  const loadClients = async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await TechModulAPI.getClients();
      setClients(rows);
    } catch (e: any) {
      setError(e?.message ?? "Blad pobierania kontrahentow");
      setClients([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, []);

  const filtered = useMemo(() => {
    return clients.filter((c) => {
      if (filter !== "all" && c.status !== filter) return false;
      if (q && !c.name.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [clients, filter, q]);

  const createClient = async () => {
    if (!createForm.name.trim() || saving) return;
    setSaving(true);
    setError(null);
    try {
      await TechModulAPI.createClient({
        name: createForm.name.trim(),
        location: createForm.location.trim(),
        type: createForm.type,
        status: createForm.status,
      });
      setCreateForm({ name: "", location: "", type: "person", status: "active" });
      setShowCreate(false);
      await loadClients();
    } catch (e: any) {
      setError(e?.message ?? "Blad zapisu kontrahenta");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow={
          <Link
            href="/database"
            className="flex items-center gap-1 hover:text-brand transition-colors group"
          >
            <ArrowLeft size={12} className="group-hover:-translate-x-0.5 transition-transform" />
            Powrot do Centrum Baz
          </Link>
        }
        title={<>Klienci i <span className="text-brand-hover">kontrahenci</span></>}
        subtitle="Baza klientow indywidualnych i partnerow B2B z backend/SQLite."
        actions={
          <Button onClick={() => setShowCreate((v) => !v)}>
            <Plus className="w-4 h-4" /> Dodaj kontrahenta
          </Button>
        }
      />

      {showCreate ? (
        <Card className="mb-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input
              className="input-base"
              placeholder="Nazwa kontrahenta"
              value={createForm.name}
              onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
            />
            <input
              className="input-base"
              placeholder="Lokalizacja / opis"
              value={createForm.location}
              onChange={(e) => setCreateForm((f) => ({ ...f, location: e.target.value }))}
            />
            <select
              className="input-base"
              value={createForm.type}
              onChange={(e) => setCreateForm((f) => ({ ...f, type: e.target.value as ClientType }))}
            >
              <option value="person">Osoba</option>
              <option value="b2b">B2B</option>
            </select>
            <div className="flex gap-2">
              <select
                className="input-base"
                value={createForm.status}
                onChange={(e) => setCreateForm((f) => ({ ...f, status: e.target.value as ClientStatus }))}
              >
                <option value="active">Aktywny</option>
                <option value="vip">VIP</option>
                <option value="archived">Archiwum</option>
              </select>
              <Button onClick={createClient} disabled={saving || !createForm.name.trim()}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Zapisz"}
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      {error ? (
        <Card className="mb-4 border-red-500/20 bg-red-500/5">
          <p className="text-sm text-red-300">{error}</p>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
        <div className="space-y-3">
          <div className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Szukaj kontrahenta..."
              className="input-base pl-10"
            />
          </div>

          {loading ? (
            <Card>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                Ladowanie kontrahentow...
              </div>
            </Card>
          ) : null}

          {!loading && filtered.map((c) => (
            <Card
              key={c.id}
              className={clsx(
                "flex items-center justify-between hover:border-brand-ring transition-colors cursor-pointer",
                c.status === "archived" && "opacity-60"
              )}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-panel-raised border border-subtle flex items-center justify-center font-bold text-sm text-brand-hover">
                  {initialsFromName(c.name)}
                </div>
                <div>
                  <h3 className="text-base font-semibold">{c.name}</h3>
                  <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-1">
                    {c.type === "b2b" ? <Building2 className="w-3 h-3" /> : <MapPin className="w-3 h-3" />}
                    {c.location || (c.type === "b2b" ? "Partner B2B" : "Brak lokalizacji")}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <StatusBadge status={c.status} label={statusLabel(c.status)} />
                {c.status === "vip" ? (
                  <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                ) : (
                  <History className="w-4 h-4 text-slate-600" />
                )}
              </div>
            </Card>
          ))}

          {!loading && filtered.length === 0 ? (
            <p className="text-sm text-slate-600 text-center py-10">Brak kontrahentow pasujacych do kryteriow.</p>
          ) : null}
        </div>

        <div>
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Users className="w-4 h-4 text-brand-hover" />
              <h3 className="eyebrow">Filtr</h3>
            </div>
            <div className="space-y-1.5">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFilter(f.id)}
                  className={clsx(
                    "w-full text-left px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    filter === f.id
                      ? "bg-brand-soft text-brand-hover"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

function StatusBadge({
  status,
  label,
}: {
  status: ClientRecord["status"];
  label: string;
}) {
  const cls =
    status === "active"
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      : status === "vip"
      ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
      : "bg-slate-500/10 text-slate-400 border-slate-500/20";
  return (
    <span
      className={clsx(
        "px-2.5 py-1 rounded-md border text-[10px] font-bold uppercase tracking-wider",
        cls
      )}
    >
      {label}
    </span>
  );
}
