"use client";

type TerminalProps = {
  type: "Lakiernia" | "Montaz";
};

export default function TouchTerminal({ type }: TerminalProps) {
  return (
    <div className="min-h-screen bg-[#050510] text-white flex items-center justify-center p-8">
      <div className="max-w-2xl w-full rounded-2xl border border-red-500/40 bg-red-500/10 p-8">
        <h1 className="text-2xl font-black uppercase tracking-widest text-red-300 mb-3">
          TouchTerminal Deprecated / Mock
        </h1>
        <p className="text-sm text-red-100 mb-2">
          Widok `{type}` w komponencie `TouchTerminal` jest nieoperacyjny i nie zapisuje danych.
        </p>
        <p className="text-sm text-red-100">
          Uzyj realnych tras produkcyjnych opartych o `ProductionTerminalPage`.
        </p>
      </div>
    </div>
  );
}
