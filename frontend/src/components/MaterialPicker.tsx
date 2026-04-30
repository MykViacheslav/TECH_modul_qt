"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Card, Button } from "./ui";
import { Search, Filter, Database, Box, Check, Loader2, ChevronRight, X, Factory, Info } from "lucide-react";
import { TechModulAPI } from "@/services/api";
import clsx from "clsx";

interface MaterialPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (material: any) => void;
  title?: string;
  categoryHint?: string;
}

export default function MaterialPicker({
  isOpen,
  onClose,
  onSelect,
  title = "Wybierz Materia",
  categoryHint
}: MaterialPickerProps) {
  const [items, setItems] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [manufacturers, setManufacturers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCat, setSelectedCat] = useState<number | null>(null);
  const [selectedMan, setSelectedMan] = useState<number | null>(null);

  useEffect(() => {
    async function load() {
      if (!isOpen) return;
      setLoading(true);
      try {
        const [cats, mans, allItems] = await Promise.all([
          TechModulAPI.getCatalogCategories(),
          TechModulAPI.getManufacturers(),
          TechModulAPI.getCatalogItems()
        ]);
        setCategories(cats);
        setManufacturers(mans);
        setItems(allItems);

        // If category hint is provided, try to pre-select it
        if (categoryHint) {
           const hint = cats.find(c => c.name.toLowerCase().includes(categoryHint.toLowerCase()) || c.name_pl.toLowerCase().includes(categoryHint.toLowerCase()));
           if (hint) setSelectedCat(hint.id);
        }
      } catch (err) {
        console.error("Failed to load picker data", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [isOpen, categoryHint]);

  const filteredItems = useMemo(() => {
    return items.filter(item => {
      const matchesSearch = !search ||
        item.name.toLowerCase().includes(search.toLowerCase()) ||
        (item.producer_code && item.producer_code.toLowerCase().includes(search.toLowerCase()));
      const matchesCat = !selectedCat || item.category_id === selectedCat;
      const matchesMan = !selectedMan || item.manufacturer_id === selectedMan;
      return matchesSearch && matchesCat && matchesMan;
    });
  }, [items, search, selectedCat, selectedMan]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* OVERLAY */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-md" onClick={onClose} />

      {/* MODAL CONTAINER */}
      <Card
        className="relative w-full max-w-5xl h-[80vh] flex flex-col overflow-hidden border-slate-700 shadow-2xl bg-canvas shadow-brand/10 p-0"
        padded={false}
      >
        {/* HEADER */}
        <header className="shrink-0 p-4 border-b border-subtle flex items-center justify-between bg-panel-raised/50">
          <div className="flex items-center gap-3">
             <div className="p-2 bg-brand/10 text-brand rounded-lg">
                <Database size={20} />
             </div>
             <div>
                <h2 className="text-lg font-bold text-white leading-tight">{title}</h2>
                <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase font-bold tracking-widest">
                   <span>MSI CENTRAL REGISTRY</span>
                   <span className="w-1 h-1 rounded-full bg-slate-700" />
                   <span>{items.length} POZYCJI W BAZIE</span>
                </div>
             </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full text-slate-500 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </header>

        <div className="flex-1 flex overflow-hidden">
          {/* SIDEBAR FILTERS */}
          <aside className="w-64 border-r border-subtle bg-panel-solid/30 flex flex-col overflow-y-auto custom-scrollbar">
            <div className="p-4 space-y-6">
              <div className="space-y-3">
                <h3 className="eyebrow flex items-center gap-2 text-slate-400">
                  <Filter size={12} /> Kategorie
                </h3>
                <div className="space-y-1">
                  <button
                    onClick={() => setSelectedCat(null)}
                    className={clsx(
                      "w-full text-left px-3 py-2 rounded-lg text-[11px] font-bold uppercase transition-all",
                      !selectedCat ? 'bg-brand/10 text-brand' : 'text-slate-500 hover:text-slate-300'
                    )}
                  >
                    Wszystkie
                  </button>
                  {categories.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => setSelectedCat(cat.id)}
                      className={clsx(
                        "w-full text-left px-3 py-2 rounded-lg text-[11px] font-bold uppercase transition-all flex justify-between items-center group",
                        selectedCat === cat.id ? 'bg-brand/10 text-brand' : 'text-slate-500 hover:text-slate-300'
                      )}
                    >
                      {cat.name_pl}
                      <span className="text-[9px] opacity-0 group-hover:opacity-100 transition-opacity">{items.filter(i => i.category_id === cat.id).length}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="eyebrow flex items-center gap-2 text-slate-400">
                  <Factory size={12} /> Producenci
                </h3>
                <div className="space-y-1">
                  <button
                    onClick={() => setSelectedMan(null)}
                    className={clsx(
                      "w-full text-left px-3 py-2 rounded-lg text-[11px] font-bold uppercase transition-all",
                      !selectedMan ? 'bg-brand/10 text-brand' : 'text-slate-500 hover:text-slate-300'
                    )}
                  >
                    Wszyscy
                  </button>
                  {manufacturers.map(man => (
                    <button
                      key={man.id}
                      onClick={() => setSelectedMan(man.id)}
                      className={clsx(
                        "w-full text-left px-3 py-2 rounded-lg text-[11px] font-bold uppercase transition-all",
                        selectedMan === man.id ? 'bg-brand/10 text-brand' : 'text-slate-500 hover:text-slate-300'
                      )}
                    >
                      {man.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </aside>

          {/* MAIN GRID */}
          <main className="flex-1 flex flex-col bg-panel-solid/10 overflow-hidden">
            <div className="p-4 border-b border-subtle shrink-0">
               <div className="relative">
                 <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
                 <input
                   type="text"
                   value={search}
                   onChange={e => setSearch(e.target.value)}
                   placeholder="Wpisz nazwe, kod koloru lub producenta..."
                   className="w-full bg-canvas-deep border border-subtle rounded-xl pl-10 pr-4 py-2 text-sm focus:border-brand/50 outline-none transition-colors"
                   autoFocus
                 />
               </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              {loading ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-4">
                  <Loader2 className="w-8 h-8 animate-spin text-brand" />
                  <p className="eyebrow">Pobieranie zasobow...</p>
                </div>
              ) : filteredItems.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2 opacity-50 py-20">
                  <Box size={48} strokeWidth={1} />
                  <p className="font-bold">Brak wynikow</p>
                  <p className="text-[10px] uppercase">Zmien filtry lub fraze wyszukiwania</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {filteredItems.map(item => (
                    <div
                      key={item.id}
                      onClick={() => onSelect(item)}
                      className="group cursor-pointer bg-panel-raised border border-subtle rounded-xl overflow-hidden hover:border-brand/50 transition-all hover:shadow-lg hover:shadow-brand/5"
                    >
                      <div className="aspect-[3/2] bg-slate-900 border-b border-subtle relative">
                         {item.texture_path ? (
                           <img src={item.texture_path} alt="" className="w-full h-full object-cover" />
                         ) : (
                           <div className="w-full h-full flex items-center justify-center opacity-20">
                              <Box size={32} />
                           </div>
                         )}
                         <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <span className="bg-brand text-white text-[10px] uppercase font-black px-3 py-1 rounded-full shadow-lg">Wybierz</span>
                         </div>
                      </div>
                      <div className="p-3">
                         <h4 className="text-[11px] font-bold text-slate-200 line-clamp-1 group-hover:text-brand transition-colors">{item.name}</h4>
                         <div className="flex items-center justify-between mt-2">
                           <span className="text-[9px] font-mono text-slate-500 uppercase">{item.producer_code || '---'}</span>
                           <span className="text-[9px] font-bold text-slate-400 bg-white/5 px-1.5 rounded">{item.default_thickness_mm}mm</span>
                         </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </main>
        </div>

        {/* FOOTER */}
        <footer className="p-3 border-t border-subtle bg-panel-raised/50 flex items-center justify-between">
           <div className="flex items-center gap-2 text-[10px] text-slate-500">
             <Info size={12} className="text-blue-400" />
             <span>Wybierz materia, aby automatycznie zaktualizowac model 3D i wycene.</span>
           </div>
           <Button variant="secondary" size="sm" onClick={onClose}>Anuluj</Button>
        </footer>
      </Card>
    </div>
  );
}
