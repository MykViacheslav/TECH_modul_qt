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
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.push("/");
    }
  }, [user, loading, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Wprowadź login i hasło (lub PIN).");
      return;
    }
    
    setIsSubmitting(true);
    setError("");
    
    try {
      await TechModulAPI.login(username, password);
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
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand/10 blur-[100px] rounded-full pointer-events-none" />
      
      <Card className="w-full max-w-md p-8 relative z-10 border-white/10 bg-slate-900/80 backdrop-blur-xl">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-brand/20 text-brand rounded-2xl mx-auto flex items-center justify-center mb-4 border border-brand/30 shadow-glow shadow-brand/20">
            <Lock className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight font-orbitron">TECH_modul<span className="text-brand">.OS</span></h1>
          <p className="text-slate-400 mt-2 text-sm">Zaloguj się, aby uzyskać dostęp do systemu.</p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Użytkownik</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-white outline-none focus:border-brand focus:ring-1 focus:ring-brand/50 transition-all"
                placeholder="Jan Kowalski"
                autoComplete="username"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Hasło / PIN</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-white outline-none focus:border-brand focus:ring-1 focus:ring-brand/50 transition-all"
                placeholder="••••"
                autoComplete="current-password"
              />
            </div>
          </div>

          <Button 
            type="submit" 
            disabled={isSubmitting}
            className="w-full py-2.5 mt-2 bg-brand text-white hover:bg-brand/90 font-bold tracking-wide shadow-glow shadow-brand/20"
          >
            {isSubmitting ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>Wejdź do systemu <ArrowRight className="w-4 h-4 ml-2" /></>
            )}
          </Button>
        </form>
      </Card>
    </div>
  );
}
