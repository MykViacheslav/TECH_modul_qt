"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { TechModulAPI } from "@/services/api";
import { Card, Button } from "@/components/ui";
import { Lock, User, AlertCircle, ArrowRight } from "lucide-react";
import clsx from "clsx";
import { useCurrentUser } from "@/services/user-context";

export default function LoginPage() {
  const router = useRouter();
  const [user, , loading] = useCurrentUser();
  
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [technicians, setTechnicians] = useState<any[]>([]);
  const [fetchingTechs, setFetchingTechs] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.push("/");
    }
  }, [user, loading, router]);

  useEffect(() => {
    loadTechnicians();
  }, []);

  const loadTechnicians = async () => {
    setFetchingTechs(true);
    try {
      const data = await TechModulAPI.getTechnicians();
      setTechnicians(data.filter((item: any) => item.is_active !== 0));
    } catch (e) {
      console.error("Failed to load technicians", e);
    } finally {
      setFetchingTechs(false);
    }
  };

  const handleLogin = async (e?: React.FormEvent, selectedName?: string) => {
    if (e) e.preventDefault();
    const nameToLogin = selectedName || username;
    
    if (!nameToLogin) {
      setError("Wybierz lub wpisz użytkownika.");
      return;
    }
    
    setIsSubmitting(true);
    setError("");
    
    try {
      await TechModulAPI.login(nameToLogin, "1");
      window.location.href = "/";
    } catch (err: any) {
      setError(err.message || "Nieprawidłowe dane logowania.");
      setIsSubmitting(false);
    }
  };

  if (loading || user) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-pulse text-slate-500 font-mono tracking-widest uppercase text-sm">
          Wczytywanie modułu...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand/10 blur-[100px] rounded-full pointer-events-none" />
      
      <Card className="w-full max-w-lg p-8 relative z-10 border-white/10 bg-slate-900/80 backdrop-blur-xl">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-brand/20 text-brand rounded-2xl mx-auto flex items-center justify-center mb-4 border border-brand/30 shadow-glow shadow-brand/20">
            <User className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight font-orbitron uppercase italic">TECH_modul<span className="text-brand">.OS</span></h1>
          <p className="text-slate-400 mt-2 text-sm italic uppercase font-bold tracking-widest text-[10px]">Autoryzacja uproszczona</p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <div className="space-y-6">
          {/* Quick Selection */}
          <div className="space-y-3">
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] block">Szybki wybór pracownika</label>
            <div className="grid grid-cols-2 gap-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
              {fetchingTechs ? (
                <div className="col-span-2 py-4 text-center text-xs text-slate-600 italic">Ładowanie listy...</div>
              ) : technicians.length === 0 ? (
                <div className="col-span-2 py-4 text-center text-xs text-slate-600 italic">Brak zdefiniowanych pracowników</div>
              ) : (
                technicians.map(t => (
                  <button
                    key={t.id}
                    onClick={() => handleLogin(undefined, t.name)}
                    className="p-3 rounded-xl bg-white/5 border border-white/5 text-left hover:border-brand/50 hover:bg-brand/5 transition-all group"
                  >
                    <div className="text-[9px] font-black uppercase text-slate-500 group-hover:text-brand-hover mb-0.5">{t.role}</div>
                    <div className="text-xs font-bold text-white group-hover:text-brand-hover">{t.name}</div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <div className="w-full border-t border-white/5"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="px-2 bg-slate-900/0 text-[10px] font-black uppercase tracking-widest text-slate-600">lub wpisz ręcznie</span>
            </div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1.5">
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-white outline-none focus:border-brand focus:ring-1 focus:ring-brand/50 transition-all"
                  placeholder="Nazwa użytkownika"
                  autoComplete="username"
                />
              </div>
            </div>

            <Button 
              type="submit" 
              disabled={isSubmitting}
              className="w-full py-3 bg-brand text-white hover:bg-brand/90 font-black uppercase tracking-widest text-xs shadow-glow shadow-brand/20 rounded-xl"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Wejdź do systemu <ArrowRight className="w-4 h-4 ml-2" /></>
              )}
            </Button>
          </form>
        </div>
      </Card>

      <div className="mt-8 text-center">
        <p className="text-[10px] text-slate-600 font-bold uppercase tracking-[0.2em]">
          Tech Modul Professional v2.4 &middot; Industrial OS
        </p>
      </div>
    </div>
  );
}
