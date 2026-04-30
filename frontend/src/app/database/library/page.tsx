"use client";

import React, { useState, useEffect } from "react";
import { TechModulAPI } from "@/services/api";
import { Button, Card } from "@/components/ui";
import { Search, Filter, Database, Tag, Factory, Info, FileText, ChevronRight, ArrowLeft, Trash2, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function MaterialsLibraryPage() {
  const [categories, setCategories] = useState<any[]>([]);
  const [manufacturers, setManufacturers] = useState<any[]>([]);
  const [items, setItems] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [selectedItem, setSelectedItem] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [includeDeleted, setIncludeDeleted] = useState(false);

  useEffect(() => {
    async function loadInitial() {
      try {
        const [catData, manData] = await Promise.all([
          TechModulAPI.getCatalogCategories(),
          TechModulAPI.getManufacturers()
        ]);
        setCategories(catData);
        setManufacturers(manData);

        const itemsData = await TechModulAPI.getCatalogItems({ include_deleted: includeDeleted });
        setItems(itemsData);
      } catch (err) {
        console.error("Failed to load catalog data", err);
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, [includeDeleted]);

  const filteredItems = React.useMemo(() => {
    return items.filter(item => {
      if (selectedCategory && item.category_id !== selectedCategory) return false;
      return true;
    });
  }, [items, selectedCategory]);

  return (
    <div className="flex h-[calc(100vh-140px)] gap-6 overflow-hidden">
      {/* LEFT COLUMN: NAVIGATION & FILTERS */}
      <aside className="w-72 flex flex-col gap-4">
        <Card className="flex-1 overflow-y-auto" padded={false}>
          <div className="p-4 border-b border-subtle">
            <Link
              href="/database"
              className="inline-flex items-center gap-2 text-[10px] text-slate-500 hover:text-brand font-black uppercase tracking-widest mb-3 group transition-colors"
            >
              <ArrowLeft size={10} className="group-hover:-translate-x-1 transition-transform" />
              Powrot do Centrum
            </Link>
            <h3 className="eyebrow flex items-center gap-2">
              <Database size={14} /> Kategorie
            </h3>
          </div>
          <div className="p-2">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${!selectedCategory ? 'bg-brand/20 text-brand outline outline-1 outline-brand/30' : 'hover:bg-white/5 text-slate-400'}`}
            >
              Wszystkie materiay
            </button>
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors mt-1 flex items-center justify-between ${selectedCategory === cat.id ? 'bg-brand/20 text-brand outline outline-1 outline-brand/30' : 'hover:bg-white/5 text-slate-400'}`}
              >
                {cat.name_pl}
                <ChevronRight size={14} className={selectedCategory === cat.id ? 'opacity-100' : 'opacity-0'} />
              </button>
            ))}
          </div>

          <div className="p-4 border-t border-subtle mt-4">
            <h3 className="eyebrow flex items-center gap-2">
              <Factory size={14} /> Producenci
            </h3>
          </div>
          <div className="p-2">
            {manufacturers.map(man => (
              <label key={man.id} className="flex items-center gap-3 px-3 py-2 hover:bg-white/5 rounded-lg cursor-pointer group">
                <input type="checkbox" className="w-4 h-4 rounded border-subtle bg-panel-solid accent-brand" />
                <span className="text-sm text-slate-400 group-hover:text-slate-200">{man.name}</span>
              </label>
            ))}
          </div>
        </Card>
      </aside>

      {/* CENTER PANEL: MATERIAL GRID */}
      <main className="flex-1 flex flex-col gap-4 overflow-hidden">
        <header className="flex items-center justify-between gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input
              type="text"
              placeholder="Szukaj w bibliotece (nazwa, kod, kolekcja)..."
              className="w-full bg-panel-solid/60 border border-subtle rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-brand/50 transition-colors"
            />
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-2 bg-panel-solid/40 border border-subtle rounded-xl mr-2">
               <input 
                 type="checkbox" 
                 id="show-deleted-lib" 
                 checked={includeDeleted} 
                 onChange={(e) => setIncludeDeleted(e.target.checked)}
                 className="rounded border-slate-700 bg-slate-900 text-brand focus:ring-brand"
               />
               <label htmlFor="show-deleted-lib" className="text-[10px] text-slate-500 uppercase font-black cursor-pointer select-none">
                 Pokaż usunięte
               </label>
            </div>
            <Button variant="secondary"><Filter size={16} /> Filtry</Button>
            <Button variant="primary">Dodaj materiał</Button>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredItems.map(item => (
              <Card
                key={item.id}
                className={`group cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98] ${selectedItem?.id === item.id ? 'outline outline-2 outline-brand shadow-brand-glow bg-brand/5' : 'hover:border-slate-600'} ${item.is_deleted ? 'opacity-60 grayscale-[0.5] border-red-500/30 bg-red-500/5' : ''}`}
                padded={false}
                onClick={() => setSelectedItem(item)}
              >
                <div className="aspect-[4/3] bg-panel-raised rounded-t-panel overflow-hidden relative">
                  {item.thumbnail_path ? (
                    <img src={item.thumbnail_path} alt={item.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900 overflow-hidden">
                      <div className="absolute inset-0 opacity-10 bg-[url('/blueprint_bg.png')] bg-center bg-no-repeat bg-[length:150%]" />
                      <Database className="text-slate-700 relative z-10" size={48} />
                    </div>
                  )}
                  <div className="absolute top-2 right-2 flex gap-1">
                     <span className={`bg-black/60 backdrop-blur-md text-[10px] uppercase font-bold px-2 py-1 rounded ${item.is_deleted ? 'text-red-400 border border-red-500/30' : 'text-slate-300'}`}>
                       {item.is_deleted ? 'DELETED' : (item.item_type || 'BOARD')}
                     </span>
                  </div>
                </div>
                <div className="p-4">
                  <h4 className={`font-semibold truncate group-hover:text-brand transition-colors ${item.is_deleted ? 'text-slate-500 line-through' : 'text-slate-100'}`}>{item.name}</h4>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-slate-500 font-mono">{item.producer_code || 'NO-CODE'}</span>
                    <span className="text-sm font-bold text-slate-300">{item.default_thickness_mm ? `${item.default_thickness_mm}mm` : '--'}</span>
                  </div>
                </div>
              </Card>
            ))}

            {items.length === 0 && !loading && (
              <div className="col-span-full flex flex-col items-center justify-center py-20 text-center opacity-50">
                <Database size={64} strokeWidth={1} className="mb-4" />
                <p className="text-lg font-medium">Brak materiaow w tej kategorii</p>
                <p className="text-sm">Zmien filtry lub dodaj nowy materia do bazy.</p>
              </div>
            )}
          </div>
        </section>
      </main>

      {/* RIGHT PANEL: DETAILS */}
      <aside className={`w-80 flex flex-col gap-4 transition-transform duration-300 ${selectedItem ? 'translate-x-0' : 'translate-x-[110%]'}`}>
        {selectedItem && (
          <Card className="flex-1 flex flex-col h-full overflow-hidden" padded={false}>
            <div className="relative aspect-video bg-panel-raised">
               {selectedItem.texture_path ? (
                 <img src={selectedItem.texture_path} className="w-full h-full object-cover" />
               ) : (
                 <div className="w-full h-full flex items-center justify-center bg-slate-900 shadow-inner">
                    <div className="absolute inset-0 opacity-10 bg-[url('/blueprint_bg.png')] bg-center" />
                    <Database size={48} className="text-slate-800" />
                 </div>
               )}
               <button
                 onClick={() => setSelectedItem(null)}
                 className="absolute top-3 right-3 w-8 h-8 flex items-center justify-center bg-black/40 backdrop-blur-md rounded-full hover:bg-black/60 transition-colors"
                >
                  &times;
               </button>
            </div>

            <div className="p-5 flex-1 overflow-y-auto">
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-1">
                  <span className="eyebrow text-brand">SZCZEGOY</span>
                  <div className="h-px flex-1 bg-subtle" />
                </div>
                <h2 className="text-xl font-bold text-white mb-1">{selectedItem.name}</h2>
                <p className="text-sm text-slate-500">{selectedItem.description || 'Brak opisu technicznego.'}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-3 bg-panel-raised rounded-xl border border-subtle">
                  <span className="text-[10px] text-slate-500 uppercase block mb-1">Producent</span>
                  <span className="text-sm font-semibold">{manufacturers.find(m => m.id === selectedItem.manufacturer_id)?.name || '--'}</span>
                </div>
                <div className="p-3 bg-panel-raised rounded-xl border border-subtle">
                  <span className="text-[10px] text-slate-500 uppercase block mb-1">Grubosc</span>
                  <span className="text-sm font-semibold">{selectedItem.default_thickness_mm} mm</span>
                </div>
                <div className="p-3 bg-panel-raised rounded-xl border border-subtle">
                  <span className="text-[10px] text-slate-500 uppercase block mb-1">Kod Prod.</span>
                  <span className="text-sm font-mono font-semibold">{selectedItem.producer_code}</span>
                </div>
                <div className="p-3 bg-panel-raised rounded-xl border border-subtle">
                  <span className="text-[10px] text-slate-500 uppercase block mb-1">Format</span>
                  <span className="text-sm font-semibold">2800 x 2070</span>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="eyebrow">DOKUMENTACJA</span>
                  <div className="h-px flex-1 bg-subtle" />
                </div>
                <button className="w-full flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 rounded-xl transition-colors border border-dashed border-slate-700">
                  <div className="flex items-center gap-3">
                    <FileText size={18} className="text-red-400" />
                    <div className="text-left">
                       <p className="text-sm font-medium">Karta Techniczna.pdf</p>
                       <p className="text-[10px] text-slate-500">Specyfikacja producenta  1.2 MB</p>
                    </div>
                  </div>
                  <ChevronRight size={16} className="text-slate-600" />
                </button>
                <button className="w-full flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 rounded-xl transition-colors border border-dashed border-slate-700">
                  <div className="flex items-center gap-3">
                    <Info size={18} className="text-blue-400" />
                    <div className="text-left">
                       <p className="text-sm font-medium">Zasady Obrobki</p>
                       <p className="text-[10px] text-slate-500">Wskazowki CNC i okleinowania</p>
                    </div>
                  </div>
                  <ChevronRight size={16} className="text-slate-600" />
                </button>
              </div>
            </div>

             <div className="p-5 border-t border-subtle bg-panel-raised/50 flex gap-2">
              {selectedItem.is_deleted ? (
                <Button 
                  variant="primary" 
                  className="flex-1 bg-green-600 hover:bg-green-500"
                  onClick={async () => {
                    if (window.confirm(`Przywrócić materiał "${selectedItem.name}"?`)) {
                      try {
                        await TechModulAPI.restoreMaterial(selectedItem.id);
                        const itemsData = await TechModulAPI.getCatalogItems({ 
                          category_id: selectedCategory || undefined,
                          include_deleted: includeDeleted
                        });
                        setItems(itemsData);
                        setSelectedItem(itemsData.find(i => i.id === selectedItem.id));
                      } catch (e: any) {
                        alert(e?.message || "Błąd przywracania materiału");
                      }
                    }
                  }}
                >
                  <RefreshCw className="w-4 h-4 mr-2" /> Przywróć
                </Button>
              ) : (
                <>
                  <Button 
                    variant="secondary" 
                    className="hover:text-red-400 hover:border-red-400/30 transition-all"
                    onClick={async () => {
                      if (window.confirm(`Usunąć materiał "${selectedItem.name}"? (Soft Delete)`)) {
                        try {
                          await TechModulAPI.deleteMaterial(selectedItem.id);
                          const itemsData = await TechModulAPI.getCatalogItems({ 
                            category_id: selectedCategory || undefined,
                            include_deleted: includeDeleted
                          });
                          setItems(itemsData);
                          if (!includeDeleted) {
                            setSelectedItem(null);
                          } else {
                            setSelectedItem(itemsData.find(i => i.id === selectedItem.id));
                          }
                        } catch (e: any) {
                          alert(e?.message || "Błąd usuwania materiału");
                        }
                      }
                    }}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                  <Button variant="secondary" className="flex-1">Edytuj</Button>
                  <Button variant="primary" className="flex-1">Wybierz</Button>
                </>
              )}
            </div>
          </Card>
        )}
      </aside>
    </div>
  );
}
