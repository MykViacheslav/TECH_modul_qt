"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { TechModulAPI } from "@/services/api";
import { Card, Button } from "@/components/ui";
import { AlertCircle, ArrowRight, Lock, User } from "lucide-react";
import { useCurrentUser } from "@/services/user-context";

type Technician = {
  id: number;
  name: string;
  role: string;
  avatar_color?: string;
  is_active?: number;
};

const TEMP_PIN = "1";

export default function LoginPage() {
  const router = useRouter();
  const [user, , loading] = useCurrentUser();
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedName, setSelectedName] = useState("");
  const [manualName, setManualName] = useState("");
  const [manualPin, setManualPin] = useState(TEMP_PIN);

  useEffect(() => {
    if (!loading && user) {
      router.push("/");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (loading || user) return;
    TechModulAPI.getTechnicians()
      .then((items) => {
        const active = items.filter((item: Technician) => item.is_active !== 0);
        setTechnicians(active);
      })
      .catch((err: any) => setError(err.message || "Nie udalo sie pobrac uzytkownikow."));
  }, [loading, user]);

  const handleLogin = async (tech: Technician) => {
    setIsSubmitting(true);
    setSelectedName(tech.name);
    setError("");

    try {
      await TechModulAPI.login(tech.name, TEMP_PIN);
      window.location.href = "/";
    } catch (err: any) {
      setError(err.message || "Nieprawidlowe dane logowania.");
      setIsSubmitting(false);
      setSelectedName("");
    }
  };

  const handleManualLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    const name = manualName.trim();
    const pin = manualPin.trim() || TEMP_PIN;
    if (!name) {
      setError("Wpisz nazwe uzytkownika.");
      return;
    }

    setIsSubmitting(true);
    setSelectedName(name);
    setError("");

    try {
      await TechModulAPI.login(name, pin);
      window.location.href = "/";
    } catch (err: any) {
      setError(err.message || "Nieprawidlowe dane logowania.");
      setIsSubmitting(false);
      setSelectedName("");
    }
  };

  if (loading || user) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-pulse text-slate-500 font-mono tracking-widest uppercase text-sm">
          Wczytywanie modulu...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand/10 blur-[100px] rounded-full pointer-events-none" />

      <Card className="w-full max-w-lg p-8 relative z-10 border-white/10 bg-slate-900/80 backdrop-blur-xl">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-brand/20 text-brand rounded-2xl mx-auto flex items-center justify-center mb-4 border border-brand/30 shadow-glow shadow-brand/20">
            <Lock className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight font-orbitron">
            TECH_modul<span className="text-brand">.OS</span>
          </h1>
          <p className="text-slate-400 mt-2 text-sm">Wybierz uzytkownika, aby wejsc do systemu.</p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <div className="grid gap-3">
          {technicians.map((tech) => (
            <Button
              key={tech.id}
              type="button"
              disabled={isSubmitting}
              onClick={() => handleLogin(tech)}
              className="w-full justify-between py-4 bg-black/30 border border-white/10 text-white hover:bg-brand/20 hover:border-brand/50"
            >
              <span className="flex items-center gap-3 min-w-0">
                <span
                  className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ backgroundColor: tech.avatar_color || "#1e3a5f" }}
                >
                  <User className="w-4 h-4 text-white" />
                </span>
                <span className="text-left min-w-0">
                  <span className="block font-bold truncate">{tech.name}</span>
                  <span className="block text-xs text-slate-400 uppercase tracking-wide">{tech.role}</span>
                </span>
              </span>
              {isSubmitting && selectedName === tech.name ? (
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin shrink-0" />
              ) : (
                <ArrowRight className="w-4 h-4 shrink-0" />
              )}
            </Button>
          ))}
        </div>

        <form onSubmit={handleManualLogin} className="mt-6 grid gap-3 border-t border-white/10 pt-5">
          <div className="grid gap-2 sm:grid-cols-[1fr_120px]">
            <input
              type="text"
              value={manualName}
              onChange={(event) => setManualName(event.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-white outline-none focus:border-brand focus:ring-1 focus:ring-brand/50 transition-all"
              placeholder="Nazwa uzytkownika"
              autoComplete="username"
            />
            <input
              type="password"
              value={manualPin}
              onChange={(event) => setManualPin(event.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-white outline-none focus:border-brand focus:ring-1 focus:ring-brand/50 transition-all"
              placeholder="PIN"
              autoComplete="current-password"
            />
          </div>
          <Button type="submit" disabled={isSubmitting} className="w-full py-2.5 bg-brand text-white hover:bg-brand/90 font-bold">
            Wejdz recznie
          </Button>
        </form>
      </Card>
    </div>
  );
}
