"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI } from "@/services/api";
import { 
  FolderLock, 
  Trash2, 
  RefreshCw, 
  Search,
  Calendar,
  User,
  Tag,
  AlertTriangle
} from "lucide-react";

export default function ProjectsManagementPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [includeDeleted, setIncludeDeleted] = useState(false);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await TechModulAPI.getProjects({ include_deleted: includeDeleted });
      setProjects(res || []);
    } catch (e: any) {
      setError(e?.message || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, [includeDeleted]);

  const handleDelete = async (id: number, title: string) => {
    if (!window.confirm(`Czy na pewno chcesz przenieść projekt "${title}" do kosza? (Soft Delete)`)) {
      return;
    }
    try {
      await TechModulAPI.deleteProject(id);
      loadProjects();
    } catch (e: any) {
      alert(e?.message || "Błąd podczas usuwania projektu");
    }
  };

  const handleRestore = async (id: number, title: string) => {
    if (!window.confirm(`Przywrócić projekt "${title}"?`)) {
      return;
    }
    try {
      await TechModulAPI.restoreProject(id);
      loadProjects();
    } catch (e: any) {
      alert(e?.message || "Błąd podczas przywracania projektu");
    }
  };

  const filtered = projects.filter(p => 
    p.title.toLowerCase().includes(search.toLowerCase()) || 
    p.client_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AppShell>
      <PageHeader
        eyebrow="Admin Panel"
        title="Zarządzanie Projektami"
        subtitle="Lista aktywnych projektów w systemie. Usunięte projekty są ukrywane w bazie (Soft Delete)."
        actions={
          <Button onClick={loadProjects}>
            <RefreshCw className="w-4 h-4 mr-2" /> Odśwież
          </Button>
        }
      />

      <div className="max-w-6xl mx-auto space-y-6 pb-20">
        <div className="flex gap-4 items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
            <input
              type="text"
              placeholder="Szukaj projektu lub klienta..."
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white outline-none focus:border-brand/50 transition-all"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl">
             <input 
               type="checkbox" 
               id="show-deleted" 
               checked={includeDeleted} 
               onChange={(e) => setIncludeDeleted(e.target.checked)}
               className="rounded border-slate-700 bg-slate-900 text-brand focus:ring-brand"
             />
             <label htmlFor="show-deleted" className="text-xs text-slate-400 cursor-pointer select-none">
               Pokaż usunięte
             </label>
          </div>
        </div>

        <Card padded={false}>
          {loading ? (
            <div className="p-20 text-center">
              <RefreshCw className="w-8 h-8 text-brand animate-spin mx-auto mb-4" />
              <p className="text-slate-500 font-mono text-xs uppercase tracking-widest">Loading_Project_Registry...</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-20 text-center text-slate-500">
              <FolderLock className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>Brak projektów spełniających kryteria.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-white/5 text-slate-500 uppercase font-bold text-[10px]">
                  <tr>
                    <th className="px-6 py-4">Tytuł Projektu</th>
                    <th className="px-6 py-4">Klient</th>
                    <th className="px-6 py-4">Data Utworzenia</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">Akcje</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filtered.map((p) => (
                    <tr key={p.id} className={`hover:bg-white/5 transition-colors group ${p.is_deleted ? 'opacity-60 bg-red-500/5' : ''}`}>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${p.is_deleted ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'}`}>
                            {p.id}
                          </div>
                          <span className={`font-bold ${p.is_deleted ? 'text-slate-400 line-through' : 'text-slate-200'}`}>{p.title}</span>
                          {p.is_deleted && (
                            <span className="text-[8px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 uppercase font-black">DELETED</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-400 italic">
                        {p.client_name || "---"}
                      </td>
                      <td className="px-6 py-4 text-slate-500 text-xs font-mono">
                        {p.created_at?.split(' ')[0]}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-tighter border ${p.is_deleted ? 'bg-slate-900 text-slate-600 border-slate-800' : 'bg-slate-800 text-slate-400 border-white/5'}`}>
                          {p.status || "WYCENA"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {p.is_deleted ? (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="text-green-500 hover:text-green-400 hover:bg-green-500/10"
                            onClick={() => handleRestore(p.id, p.title)}
                          >
                            <RefreshCw className="w-4 h-4 mr-1" /> Przywróć
                          </Button>
                        ) : (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="text-slate-500 hover:text-red-400"
                            onClick={() => handleDelete(p.id, p.title)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="p-4 bg-red-500/5 border border-red-500/10 rounded-xl flex gap-4 items-start">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div className="text-xs">
            <h4 className="font-bold text-red-400 mb-1 tracking-tight">Destructive Action Guard</h4>
            <p className="text-slate-500 leading-relaxed">
              Pamiętaj, że usunięcie projektu w tym widoku jest **odwracalne** (Soft Delete). Projekt zniknie z głównej listy, ale jego dane pozostaną w bazie SQLite. Całkowite usunięcie (Hard Delete) na produkcji wymaga ustawienia flagi <code className="bg-red-500/10 text-red-300 px-1 rounded">TECH_MODUL_PROD_CONFIRM</code>.
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
