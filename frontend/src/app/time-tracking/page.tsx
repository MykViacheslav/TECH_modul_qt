"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import {
  Clock,
  Calendar,
  User,
  ChevronRight,
  Plus,
  Save,
  Trash2,
  CheckCircle2,
  AlertCircle,
  QrCode,
  Edit3,
  ExternalLink,
  Search
} from "lucide-react";
import { useState, useEffect, useMemo } from "react";
import { TechModulAPI, type WorkerMonthSheet, type WorkTimeEntry } from "@/services/api";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

export default function TimeTrackingPage() {
  const [sheets, setSheets] = useState<WorkerMonthSheet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSheet, setSelectedSheet] = useState<WorkerMonthSheet | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSheets();
  }, []);

  const loadSheets = async () => {
    setLoading(true);
    try {
      const data = await TechModulAPI.getWorkSheets();
      setSheets(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredSheets = useMemo(() => {
    if (!searchQuery) return sheets;
    const q = searchQuery.toLowerCase();
    return sheets.filter(s =>
      s.worker_name.toLowerCase().includes(q) ||
      `${s.year}-${s.month}`.includes(q)
    );
  }, [sheets, searchQuery]);

  const handleSaveSheet = async () => {
    if (!selectedSheet) return;
    setSaving(true);
    try {
      await TechModulAPI.saveWorkSheet(selectedSheet);
      await loadSheets();
      setSelectedSheet(null);
    } catch (e: any) {
      alert("Bad zapisu: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const addEntry = () => {
    if (!selectedSheet) return;
    const today = new Date();
    const newEntry: WorkTimeEntry = {
      entry_id: Math.random().toString(36).substr(2, 8).toUpperCase(),
      day: today.getDate(),
      date_iso: today.toISOString().split("T")[0],
      work_type: "Produkcja",
      start_time: "08:00",
      end_time: "16:16",
      hours: 8,
      overtime_hours: 0,
      extra_pay: 0,
      project_code: "",
      note: "Wpis manualny"
    };
    setSelectedSheet({
      ...selectedSheet,
      entries: [...selectedSheet.entries, newEntry].sort((a,b) => a.day - b.day)
    });
  };

  const removeEntry = (id: string) => {
    if (!selectedSheet) return;
    setSelectedSheet({
      ...selectedSheet,
      entries: selectedSheet.entries.filter(e => e.entry_id !== id)
    });
  };

  const updateEntry = (id: string, field: keyof WorkTimeEntry, value: any) => {
    if (!selectedSheet) return;
    setSelectedSheet({
      ...selectedSheet,
      entries: selectedSheet.entries.map(e => {
        if (e.entry_id !== id) return e;
        return { ...e, [field]: value };
      })
    });
  };

  return (
    <AppShell>
      <PageHeader
        title={<>Rejestracja <span className="text-brand-hover">Czasu Pracy</span></>}
        subtitle="Zarzadzaj listami obecnosci, delegacjami i robotogodzinami."
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => window.open(window.location.origin + "/time-tracking/scan", "_blank")}>
              <QrCode className="w-4 h-4 mr-2" /> Otworz Skaner RCP
            </Button>
            <Button onClick={() => window.location.reload()}>Odswiez</Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lewa kolumna: Lista arkuszy */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <div className="mb-4 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Szukaj pracownika lub daty..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-base !pl-10"
              />
            </div>

            <div className="space-y-2">
              <h3 className="eyebrow-brand mb-3">Arkusze miesieczne</h3>
              {loading ? (
                <div className="py-12 text-center text-slate-500 text-xs italic">adowanie danych...</div>
              ) : filteredSheets.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs italic">Brak arkuszy czasu pracy.</div>
              ) : (
                filteredSheets.map(s => (
                  <button
                    key={s.sheet_id || `${s.worker_name}-${s.year}-${s.month}`}
                    onClick={() => setSelectedSheet(s)}
                    className={clsx(
                      "w-full p-4 rounded-2xl border text-left transition-all group",
                      selectedSheet?.sheet_id === s.sheet_id
                        ? "bg-brand/10 border-brand/50 shadow-brand-glow"
                        : "bg-panel-solid/20 border-white/5 hover:border-white/20 hover:bg-white/5"
                    )}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-sm font-black text-white group-hover:text-brand-hover transition-colors">{s.worker_name}</div>
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">
                          {s.year}-{String(s.month).padStart(2, "0")}
                        </div>
                      </div>
                      <ChevronRight className={clsx("w-4 h-4 transition-transform", selectedSheet?.sheet_id === s.sheet_id ? "translate-x-1 text-brand-hover" : "text-slate-600")} />
                    </div>
                    <div className="mt-3 flex items-center gap-4">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span className="text-[10px] font-mono text-slate-300">
                          {s.entries.reduce((acc, e) => acc + (e.hours || 0), 0).toFixed(1)} h
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3 h-3 text-slate-500" />
                        <span className="text-[10px] font-mono text-slate-300">{s.entries.length} dni</span>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Prawa kolumna: Detale i edycja */}
        <div className="lg:col-span-2">
          <AnimatePresence mode="wait">
            {!selectedSheet ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full flex flex-col items-center justify-center p-12 text-center"
              >
                <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-6">
                  <User size={32} className="text-slate-600" />
                </div>
                <h3 className="text-lg font-bold text-slate-400">Wybierz arkusz z listy</h3>
                <p className="text-sm text-slate-500 mt-2 max-w-xs">Wybierz pracownika po lewej stronie, aby edytowac godziny, wpisy delegacji lub skorygowac bledne logowania.</p>
              </motion.div>
            ) : (
              <motion.div
                key={selectedSheet.sheet_id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-2xl font-black italic tracking-tighter uppercase">
                      Arkusz: <span className="text-brand-hover">{selectedSheet.worker_name}</span>
                    </h2>
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">
                      Szczegoowy wykaz godzin dla okresu {selectedSheet.year}-{String(selectedSheet.month).padStart(2, "0")}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={addEntry}>
                      <Plus className="w-4 h-4 mr-2" /> Dodaj wpis
                    </Button>
                    <Button onClick={handleSaveSheet} disabled={saving}>
                      {saving ? <Plus className="animate-spin" /> : <Save className="w-4 h-4 mr-2" />} Zapisz zmiany
                    </Button>
                  </div>
                </div>

                <Card className="overflow-hidden border-brand-ring/20">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[800px]">
                      <thead>
                        <tr className="bg-white/[0.02] border-b border-white/5">
                          <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest w-16 text-center">Dzien</th>
                          <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest w-40">Typ pracy</th>
                          <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest w-24">Start</th>
                          <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest w-24">Koniec</th>
                          <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest w-20">H</th>
                          <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">Notatka / Projekt</th>
                          <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest w-12"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {selectedSheet.entries.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="px-4 py-12 text-center text-slate-600 text-[10px] font-bold uppercase italic">Brak wpisow w tym miesiacu</td>
                          </tr>
                        ) : (
                          selectedSheet.entries.map(e => (
                            <tr key={e.entry_id} className="hover:bg-brand/5 transition-colors group">
                              <td className="px-4 py-2 text-center text-xs font-black text-white">{e.day}</td>
                              <td className="px-4 py-2">
                                <select
                                  value={e.work_type}
                                  onChange={(evt) => updateEntry(e.entry_id, "work_type", evt.target.value)}
                                  className="w-full bg-canvas-deep border border-subtle rounded-lg px-2 py-1 text-[10px] uppercase font-bold text-slate-300 outline-none focus:border-brand-hover"
                                >
                                  <option value="Produkcja">Produkcja</option>
                                  <option value="Montaz">Montaz</option>
                                  <option value="Pomiar">Pomiar</option>
                                  <option value="Biuro">Biuro</option>
                                  <option value="Delegacja">Delegacja</option>
                                  <option value="Urlop">Urlop</option>
                                </select>
                              </td>
                              <td className="px-4 py-2">
                                <input
                                  type="time"
                                  value={e.start_time}
                                  onChange={(evt) => updateEntry(e.entry_id, "start_time", evt.target.value)}
                                  className="w-full bg-canvas-deep border border-subtle rounded-lg px-2 py-1 text-xs text-white outline-none focus:border-brand-hover"
                                />
                              </td>
                              <td className="px-4 py-2">
                                <input
                                  type="time"
                                  value={e.end_time}
                                  onChange={(evt) => updateEntry(e.entry_id, "end_time", evt.target.value)}
                                  className="w-full bg-canvas-deep border border-subtle rounded-lg px-2 py-1 text-xs text-white outline-none focus:border-brand-hover"
                                />
                              </td>
                              <td className="px-4 py-2">
                                <input
                                  type="number"
                                  step="0.5"
                                  value={e.hours}
                                  onChange={(evt) => updateEntry(e.entry_id, "hours", parseFloat(evt.target.value) || 0)}
                                  className="w-full bg-canvas-deep border border-subtle rounded-lg px-2 py-1 text-xs text-brand-hover font-bold outline-none focus:border-brand-hover text-center"
                                />
                              </td>
                              <td className="px-4 py-2">
                                <input
                                  type="text"
                                  value={e.note}
                                  placeholder="Notatka..."
                                  onChange={(evt) => updateEntry(e.entry_id, "note", evt.target.value)}
                                  className="w-full bg-canvas-deep border border-subtle rounded-lg px-2 py-1 text-[10px] text-slate-400 outline-none focus:border-brand-hover"
                                />
                              </td>
                              <td className="px-4 py-2 text-right">
                                <button
                                  onClick={() => removeEntry(e.entry_id)}
                                  className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100"
                                >
                                  <Trash2 size={14} />
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                  <div className="p-4 bg-white/[0.01] border-t border-white/5 flex items-center justify-between">
                    <div className="flex gap-4">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Suma godzin:</span>
                        <span className="text-sm font-black text-brand-hover">{selectedSheet.entries.reduce((acc, e) => acc + (e.hours || 0), 0).toFixed(1)} h</span>
                      </div>
                    </div>
                    <span className="text-[9px] text-slate-600 font-bold uppercase tracking-widest italic flex items-center gap-2">
                      <Edit3 size={10} /> Auto-save inactive. Click "Zapisz zmiany" to finalize.
                    </span>
                  </div>
                </Card>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="bg-brand/5 border-brand/20">
                    <div className="flex items-start gap-4">
                      <div className="p-3 rounded-2xl bg-brand/10 border border-brand/20 text-brand-hover">
                        <CheckCircle2 size={24} />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-white">Weryfikacja kompletnosci</h4>
                        <p className="text-xs text-slate-400 mt-1">Arkusz zawiera wpisy dla {selectedSheet.entries.length} dni. Srednia dobowe: {(selectedSheet.entries.reduce((acc, e) => acc + (e.hours || 0), 0) / (selectedSheet.entries.length || 1)).toFixed(1)} h.</p>
                      </div>
                    </div>
                  </Card>
                  <Card className="bg-amber-500/5 border-amber-500/20">
                     <div className="flex items-start gap-4">
                        <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-500">
                          <AlertCircle size={24} />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-white">Delegacje i nadgodziny</h4>
                          <p className="text-xs text-slate-400 mt-1">Pamietaj o wpisaniu kodu projektu w notatce, aby godziny zostaly przypisane do konkretnego zlecenia w module FINANSE.</p>
                        </div>
                     </div>
                  </Card>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </AppShell>
  );
}
