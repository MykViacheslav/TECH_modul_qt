"use client";

import { useState, useEffect, useRef } from "react";
import { TechModulAPI, type KioskResult } from "@/services/api";
import {
  QrCode,
  User,
  Clock,
  Play,
  Square,
  Coffee,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  XCircle,
  Camera,
  RefreshCw,
  Search,
  AlertCircle,
  Zap,
  RefreshCcw,
  Smartphone
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import Link from "next/link";

export default function ScanTimePage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<KioskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scannerActive, setScannerActive] = useState(false);
  const [clock, setClock] = useState("");
  const [manualId, setManualId] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const [workers, setWorkers] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [projectCode, setProjectCode] = useState("");
  const [orderId, setOrderId] = useState("");
  const [workstation, setWorkstation] = useState("");

  useEffect(() => {
    const timer = setInterval(() => {
      setClock(new Date().toLocaleTimeString("pl-PL", { hour12: false }));
    }, 1000);
    loadWorkers();
    return () => clearInterval(timer);
  }, []);

  const loadWorkers = async () => {
    try {
      const data = await TechModulAPI.getKioskWorkers();
      setWorkers(data);
    } catch (e) {}
  };

  const handleAction = async (action: string, workerId?: string) => {
    const id = workerId || result?.worker?.worker_id;
    if (!id) return;

    setLoading(true);
    try {
      const res = await TechModulAPI.performKioskAction(id, action, "Produkcja", {
        project_code: projectCode,
        order_id: orderId,
        workstation,
      });
      if (res.ok) {
        setResult(res);
        setError(null);
        loadWorkers();
      } else {
        setError(res.message);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (id: string) => {
    setLoading(true);
    try {
      const res = await TechModulAPI.resolveKioskScan(id);
      if (res.ok) {
        setResult(res);
        setError(null);
      } else {
        setError(res.message);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
      setManualId("");
    }
  };

  // Simplified BarcodeDetector scanning loop
  useEffect(() => {
    let active = true;
    let detector: any = null;

    const scan = async () => {
      if (!scannerActive || !videoRef.current || !active) return;

      try {
        // @ts-ignore
        if (window.BarcodeDetector) {
          if (!detector) {
            // @ts-ignore
            detector = new window.BarcodeDetector({ formats: ["qr_code"] });
          }
          const codes = await detector.detect(videoRef.current);
          if (codes.length > 0 && active) {
            const text = codes[0].rawValue;
            setScannerActive(false);
            handleResolve(text);
          }
        }
      } catch (e) {}

      if (active && scannerActive) {
        requestAnimationFrame(scan);
      }
    };

    if (scannerActive) {
      navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: 1280, height: 720 }
      }).then(stream => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
          scan();
        }
      }).catch(e => {
        setError("Bad kamery: " + e.message);
        setScannerActive(false);
      });
    }

    return () => {
      active = false;
      if (videoRef.current?.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [scannerActive]);

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-white flex flex-col font-sans selection:bg-brand/30">
      {/* Immersive background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden opacity-20">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-brand/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-500/10 blur-[120px] rounded-full" />
      </div>

      {/* Header */}
      <header className="relative z-10 px-6 py-8 flex items-center justify-between border-b border-white/5 bg-white/[0.02] backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <Link href="/time-tracking" className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-xl font-black italic tracking-tighter uppercase leading-none">
              TECH<span className="text-brand-hover">_kiosk</span>
            </h1>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Rejestracja czasu pracy</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-black font-mono tracking-wider tabular-nums">{clock || "--:--:--"}</div>
          <div className="text-[9px] text-brand-hover font-bold uppercase tracking-widest">System Live</div>
        </div>
      </header>

      <main className="relative z-10 flex-1 flex flex-col p-6 max-w-lg mx-auto w-full gap-6">
        {/* Scanner Area */}
        <div className="relative aspect-square w-full rounded-[40px] overflow-hidden border-2 border-white/10 bg-black/40 shadow-2xl group">
          {scannerActive ? (
            <video
              ref={videoRef}
              className="w-full h-full object-cover"
              playsInline
              muted
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center gap-6 p-8 text-center">
              <div className="w-24 h-24 rounded-3xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand-hover shadow-brand-glow animate-pulse">
                <QrCode size={48} />
              </div>
              <div className="space-y-2">
                <h2 className="text-xl font-bold">Zeskanuj karte</h2>
                <p className="text-sm text-slate-500">Zbliz swoj kod QR do kamery, aby rozpoczac sesje pracy.</p>
              </div>
              <button
                onClick={() => setScannerActive(true)}
                className="px-8 py-4 rounded-2xl bg-brand text-white font-black uppercase tracking-widest text-xs shadow-lg shadow-brand/20 hover:scale-105 transition-transform active:scale-95"
              >
                Uruchom skaner
              </button>
            </div>
          )}

          {scannerActive && (
            <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
              <div className="w-64 h-64 border-2 border-brand/50 rounded-3xl relative">
                <div className="absolute inset-0 border-4 border-brand rounded-3xl animate-pulse" />
                <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-brand/50 shadow-[0_0_15px_rgba(110,231,255,1)] animate-[scan_2s_infinite]" />
              </div>
              <button
                onClick={() => setScannerActive(false)}
                className="pointer-events-auto absolute bottom-8 px-6 py-2 rounded-xl bg-black/60 backdrop-blur-md border border-white/20 text-[10px] font-black uppercase tracking-widest"
              >
                Anuluj
              </button>
            </div>
          )}
        </div>

        {/* Manual Input / Search */}
        <div className="grid grid-cols-1 gap-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Szukaj pracownika lub wpisz ID..."
              value={manualId}
              onChange={(e) => setManualId(e.target.value)}
              className="input-base !pl-12 !py-4 shadow-xl"
              onKeyDown={(e) => e.key === "Enter" && manualId && handleResolve(manualId)}
            />
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            <button
              onClick={() => manualId && handleResolve(manualId)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-xl bg-brand/20 text-brand-hover hover:bg-brand/30 transition-colors"
            >
              <RefreshCw size={18} />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <input
              type="text"
              placeholder="Project code (opcjonalnie)"
              value={projectCode}
              onChange={(e) => setProjectCode(e.target.value)}
              className="input-base !py-3 text-xs"
            />
            <input
              type="text"
              placeholder="Order ID (opcjonalnie)"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              className="input-base !py-3 text-xs"
            />
            <input
              type="text"
              placeholder="Workstation (opcjonalnie)"
              value={workstation}
              onChange={(e) => setWorkstation(e.target.value)}
              className="input-base !py-3 text-xs"
            />
          </div>
        </div>

        <AnimatePresence mode="wait">
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-3"
            >
              <XCircle size={18} /> {error}
            </motion.div>
          )}

          {loading ? (
             <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="py-12 flex flex-col items-center justify-center gap-4 text-brand-hover"
            >
              <Loader2 className="w-10 h-10 animate-spin" />
              <span className="text-[10px] font-black uppercase tracking-widest">Przetwarzanie danych...</span>
            </motion.div>
          ) : result?.worker ? (
            <motion.div
              key="result"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-4"
            >
              <div className="p-6 rounded-[32px] bg-brand/5 border border-brand/20">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-2xl font-black text-white">{result.worker.name}</h3>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">{result.worker.role || "Pracownik"}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <div className={clsx(
                      "px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest",
                      result.session ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-slate-800 text-slate-500 border border-white/5"
                    )}>
                      {result.session ? "W PRACY" : "POZA PRACA"}
                    </div>
                    <button
                      onClick={() => { setResult(null); setManualId(""); }}
                      className="text-[9px] text-brand-hover font-bold uppercase tracking-widest hover:underline"
                    >
                      Wroc do wyboru
                    </button>
                  </div>
                </div>

                {result.session && (
                  <div className="p-4 rounded-2xl bg-black/40 border border-white/5 space-y-2 mt-4">
                    <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest text-slate-500">
                      <span>Rozpoczecie</span>
                      <span>Przerwa</span>
                    </div>
                    <div className="flex justify-between text-sm font-black text-white">
                      <span>{new Date(result.session.started_at_iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      <span>{Math.round(result.session.break_total_minutes || 0)} min</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                {!result.session ? (
                  <button
                    onClick={() => handleAction("start")}
                    className="col-span-2 py-6 rounded-[24px] bg-brand text-white flex flex-col items-center gap-2 shadow-brand-glow hover:scale-[1.02] transition-transform active:scale-95"
                  >
                    <Play fill="currentColor" size={24} />
                    <span className="text-[10px] font-black uppercase tracking-widest">Rozpocznij prace</span>
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => handleAction(result.session.break_started_at_iso ? "break_end" : "break_start")}
                      className={clsx(
                        "py-6 rounded-[24px] flex flex-col items-center gap-2 transition-all active:scale-95",
                        result.session.break_started_at_iso
                          ? "bg-brand text-white shadow-brand-glow"
                          : "bg-panel-solid/40 border border-white/10 text-slate-300"
                      )}
                    >
                      <Coffee size={24} />
                      <span className="text-[10px] font-black uppercase tracking-widest">
                        {result.session.break_started_at_iso ? "Zakoncz przerwe" : "Przerwa"}
                      </span>
                    </button>
                    <button
                      onClick={() => handleAction("finish")}
                      className="py-6 rounded-[24px] bg-red-500/10 border border-red-500/20 text-red-400 flex flex-col items-center gap-2 hover:bg-red-500/20 transition-all active:scale-95"
                    >
                      <Square fill="currentColor" size={20} />
                      <span className="text-[10px] font-black uppercase tracking-widest">Zakoncz prace</span>
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          ) : (
            <div className="grid grid-cols-2 gap-3 mt-2 max-h-[320px] overflow-y-auto pr-2 custom-scrollbar">
               {workers
                 .filter(w => !manualId || w.name.toLowerCase().includes(manualId.toLowerCase()) || w.worker_id.toLowerCase().includes(manualId.toLowerCase()))
                 .map(w => (
                 <button
                   key={w.worker_id}
                   onClick={() => selectWorker(w)}
                   className="p-4 rounded-2xl bg-panel-solid/40 border border-white/5 text-left group hover:border-brand/40 transition-all hover:bg-brand/5"
                 >
                    <div className="flex justify-between items-start mb-1">
                      <div className="text-[9px] font-black uppercase text-slate-500 group-hover:text-brand-hover">{w.role}</div>
                      {w.active && <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />}
                    </div>
                    <div className="text-xs font-bold text-white truncate">{w.name}</div>
                 </button>
               ))}
            </div>
          )}
        </AnimatePresence>
      </main>

      <footer className="p-8 text-center text-[9px] text-slate-600 font-bold uppercase tracking-[0.2em]">
        Tech Modul Professional v2.4 &middot; Industrial RTC System
      </footer>

      <style jsx global>{`
        @keyframes scan {
          0%, 100% { transform: translateY(-32px); }
          50% { transform: translateY(160px); }
        }
      `}</style>
    </div>
  );

  function selectWorker(worker: any) {
    setResult({
      ok: true,
      message: "Wybrano recznie",
      worker: worker,
      session: worker.session,
      entry: null
    });
  }
}
