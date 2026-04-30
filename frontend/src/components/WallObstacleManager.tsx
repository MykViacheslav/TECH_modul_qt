"use client";

import React from "react";
import { X, Plus, AppWindow as WindowIcon, DoorOpen, Zap, Drill as Pipe } from "lucide-react";
import { Button, Card } from "./ui";
import clsx from "clsx";

export type ObstacleType = 'window' | 'door' | 'socket' | 'pipe';

export interface Obstacle {
  id: string;
  type: ObstacleType;
  x: number;
  y: number;
  width: number;
  height: number;
  depth?: number;
}

interface WallObstacleManagerProps {
  obstacles: Obstacle[];
  onChange: (obstacles: Obstacle[]) => void;
}

const OBSTACLE_DEFAULTS: Record<ObstacleType, Partial<Obstacle>> = {
  window: { width: 1200, height: 1400, y: 900 },
  door: { width: 900, height: 2100, y: 0 },
  socket: { width: 60, height: 60, y: 300 },
  pipe: { width: 40, height: 2400, y: 0 }
};

const OBSTACLE_LABELS: Record<ObstacleType, string> = {
  window: 'Okno',
  door: 'Drzwi',
  socket: 'Gniazdko/Wacznik',
  pipe: 'Rura/Instalacja'
};

const OBSTACLE_ICONS: Record<ObstacleType, React.ReactNode> = {
  window: <WindowIcon className="w-4 h-4" />,
  door: <DoorOpen className="w-4 h-4" />,
  socket: <Zap className="w-4 h-4" />,
  pipe: <Pipe className="w-4 h-4" />
};

export default function WallObstacleManager({ obstacles, onChange }: WallObstacleManagerProps) {
  const addObstacle = (type: ObstacleType) => {
    const newObstacle: Obstacle = {
      id: Math.random().toString(36).substr(2, 9),
      type,
      x: 1000,
      width: 100,
      height: 100,
      y: 0,
      ...OBSTACLE_DEFAULTS[type]
    };
    onChange([...obstacles, newObstacle]);
  };

  const removeObstacle = (id: string) => {
    onChange(obstacles.filter(o => o.id !== id));
  };

  const updateObstacle = (id: string, field: keyof Obstacle, value: any) => {
    onChange(obstacles.map(o => o.id === id ? { ...o, [field]: value } : o));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">Przeszkody na scianie</h3>
        <div className="flex gap-2">
           {(Object.keys(OBSTACLE_LABELS) as ObstacleType[]).map(type => (
             <Button
                key={type}
                variant="ghost"
                size="sm"
                onClick={() => addObstacle(type)}
                className="text-[10px] font-black uppercase tracking-widest gap-2 bg-white/5 hover:bg-brand/20 transition-all"
             >
                {OBSTACLE_ICONS[type]} {OBSTACLE_LABELS[type]}
             </Button>
           ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {obstacles.length === 0 ? (
          <div className="col-span-full p-12 border-2 border-dashed border-white/5 rounded-[2rem] flex flex-col items-center justify-center text-center bg-white/[0.02]">
            <div className="w-16 h-16 rounded-3xl bg-white/5 flex items-center justify-center mb-4">
               <Plus className="w-8 h-8 text-slate-600" />
            </div>
            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Brak zdefiniowanych przeszkod</p>
            <p className="text-[10px] text-slate-700 mt-2">Dodaj okna, drzwi lub gniazdka, aby uniknac kolizji z meblami</p>
          </div>
        ) : (
          obstacles.map((obs) => (
            <Card key={obs.id} className="bg-panel-solid/40 border-white/10 p-5 group relative overflow-hidden transition-all hover:border-brand/40">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-brand/10 flex items-center justify-center text-brand">
                    {OBSTACLE_ICONS[obs.type]}
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-white">{OBSTACLE_LABELS[obs.type]}</span>
                </div>
                <button
                  onClick={() => removeObstacle(obs.id)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-full hover:bg-red-500/20 text-red-500"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                <div className="space-y-1">
                  <label className="text-[9px] text-slate-500 font-black uppercase">Pozycja X (mm)</label>
                  <input
                    type="number"
                    value={obs.x}
                    onChange={(e) => updateObstacle(obs.id, 'x', parseInt(e.target.value))}
                    className="input-base h-8 text-xs font-bold text-center"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] text-slate-500 font-black uppercase">Pozycja Y (mm)</label>
                  <input
                    type="number"
                    value={obs.y}
                    onChange={(e) => updateObstacle(obs.id, 'y', parseInt(e.target.value))}
                    className="input-base h-8 text-xs font-bold text-center"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] text-slate-500 font-black uppercase">Szerokosc (mm)</label>
                  <input
                    type="number"
                    value={obs.width}
                    onChange={(e) => updateObstacle(obs.id, 'width', parseInt(e.target.value))}
                    className="input-base h-8 text-xs font-bold text-center"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] text-slate-500 font-black uppercase">Wysokosc (mm)</label>
                  <input
                    type="number"
                    value={obs.height}
                    onChange={(e) => updateObstacle(obs.id, 'height', parseInt(e.target.value))}
                    className="input-base h-8 text-xs font-bold text-center"
                  />
                </div>
              </div>

              {/* Decorative side accent */}
              <div className="absolute top-0 bottom-0 left-0 w-1 bg-brand-hover/40" />
            </Card>
          ))
        )}
      </div>

      {/* Mini Visualizer Preview */}
      {obstacles.length > 0 && (
         <div className="mt-8 p-6 rounded-[2rem] bg-black/40 border border-white/5 relative overflow-hidden h-48 flex items-end">
            <div className="absolute inset-0 opacity-5" style={{ backgroundImage: 'radial-gradient(#fff 0.5px, transparent 0.5px)', backgroundSize: '20px 20px' }} />
            <div className="relative w-full h-full flex items-end gap-1">
               {obstacles.map(obs => (
                  <div
                    key={obs.id}
                    className={clsx(
                      "absolute border-2 transition-all flex items-center justify-center text-[8px] font-black uppercase text-center p-1",
                      obs.type === 'window' ? "border-blue-500/50 bg-blue-500/20" :
                      obs.type === 'door' ? "border-amber-500/50 bg-amber-500/20" :
                      obs.type === 'socket' ? "border-brand-hover/50 bg-brand-hover/20" :
                      "border-slate-500/50 bg-slate-500/20"
                    )}
                    style={{
                      left: `${(obs.x / 5000) * 100}%`,
                      bottom: `${(obs.y / 3000) * 100}%`,
                      width: `${(obs.width / 5000) * 100}%`,
                      height: `${(obs.height / 3000) * 100}%`
                    }}
                  >
                    {OBSTACLE_LABELS[obs.type]}
                  </div>
               ))}
               <div className="absolute bottom-0 left-0 right-0 h-px bg-white/20" />
            </div>
         </div>
      )}
    </div>
  );
}
