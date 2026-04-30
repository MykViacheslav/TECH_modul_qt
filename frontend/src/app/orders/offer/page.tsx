"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import {
  FileText,
  Plus,
  Trash2,
  DollarSign,
  Percent,
  Calculator,
  Eye,
  Download,
  CheckCircle2,
  Printer,
  ChevronRight,
  Sparkles
} from "lucide-react";
import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

interface OfferItem {
  id: string;
  name: string;
  quantity: number;
  unitPrice: number;
}

export default function OfferBuilderPage() {
  const [items, setItems] = useState<OfferItem[]>([
    { id: "1", name: "Korpusy (Pyta 18mm Oak)", quantity: 12, unitPrice: 450 },
    { id: "2", name: "Fronty Lakierowane (Mat)", quantity: 5.5, unitPrice: 850 },
    { id: "3", name: "Montaz i Transport", quantity: 1, unitPrice: 1500 },
  ]);
  const [margin, setMargin] = useState(30); // 30% margin

  const subtotal = useMemo(() => items.reduce((sum, item) => sum + (item.quantity * item.unitPrice), 0), [items]);
  const totalWithMargin = useMemo(() => subtotal * (1 + margin / 100), [subtotal, margin]);

  const addItem = () => {
    setItems([...items, { id: Date.now().toString(), name: "Nowa pozycja", quantity: 1, unitPrice: 0 }]);
  };

  const removeItem = (id: string) => {
    setItems(items.filter(i => i.id !== id));
  };

  const updateItem = (id: string, field: keyof OfferItem, value: any) => {
    setItems(items.map(i => i.id === id ? { ...i, [field]: value } : i));
  };

  const generatePDF = () => {
    alert("Generowanie profesjonalnego PDF... (Modu PDF startuje)");
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Sales & Estimating"
        title={<>Kreator <span className="text-brand-hover">Ofert Premium</span></>}
        subtitle="Przygotuj elegancka wycene dla klienta w mniej niz 2 minuty."
        actions={
          <div className="flex gap-2">
            <Button variant="ghost" onClick={generatePDF}>
               <Eye className="w-4 h-4 mr-2" /> Podglad
            </Button>
            <Button onClick={generatePDF} className="bg-brand shadow-brand-glow">
               <Download className="w-4 h-4 mr-2" /> Pobierz PDF
            </Button>
          </div>
        }
      />

      <div className="max-w-6xl mx-auto py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
         {/* ITEM LIST */}
         <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between px-2">
               <h3 className="text-xs font-black uppercase tracking-widest text-slate-500">Specyfikacja Meble / Usugi</h3>
               <button onClick={addItem} className="text-[10px] font-black uppercase text-brand-hover flex items-center gap-1 hover:scale-105 transition-all">
                  <Plus size={14} /> Dodaj pozycje
               </button>
            </div>

            <div className="space-y-3">
               <AnimatePresence>
                  {items.map((item, idx) => (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ delay: idx * 0.05 }}
                    >
                       <Card className="p-4 bg-panel-solid/30 border-white/5 hover:border-white/10 transition-all flex flex-col md:flex-row items-center gap-4">
                          <div className="flex-1 w-full">
                             <input
                               value={item.name}
                               onChange={(e) => updateItem(item.id, 'name', e.target.value)}
                               className="bg-transparent border-none text-white font-bold placeholder:text-slate-600 outline-none w-full"
                               placeholder="Nazwa elementu / usugi..."
                             />
                          </div>
                          <div className="grid grid-cols-3 gap-4 shrink-0 w-full md:w-auto">
                             <div className="flex flex-col">
                                <label className="text-[8px] font-black text-slate-600 uppercase mb-1">Ilosc / mb</label>
                                <input
                                  type="number"
                                  value={item.quantity}
                                  onChange={(e) => updateItem(item.id, 'quantity', parseFloat(e.target.value))}
                                  className="bg-canvas-deep border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white outline-none w-20"
                                />
                             </div>
                             <div className="flex flex-col">
                                <label className="text-[8px] font-black text-slate-600 uppercase mb-1">Cena netto</label>
                                <input
                                  type="number"
                                  value={item.unitPrice}
                                  onChange={(e) => updateItem(item.id, 'unitPrice', parseFloat(e.target.value))}
                                  className="bg-canvas-deep border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white outline-none w-24"
                                />
                             </div>
                             <div className="flex items-end justify-end">
                                <button
                                  onClick={() => removeItem(item.id)}
                                  className="p-2 text-slate-600 hover:text-red-500 transition-colors"
                                >
                                   <Trash2 size={16} />
                                </button>
                             </div>
                          </div>
                       </Card>
                    </motion.div>
                  ))}
               </AnimatePresence>
            </div>
         </div>

         {/* SUMMARY & MARGINS */}
         <div className="space-y-6">
            <h3 className="eyebrow-brand px-2">Podsumowanie i Marza</h3>
            <Card className="p-8 bg-canvas-deep border-white/5 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-5">
                   <Calculator size={100} />
                </div>

                <div className="space-y-8 relative z-10">
                   <div className="space-y-2">
                      <div className="flex justify-between text-xs text-slate-500 font-bold uppercase tracking-widest">
                         <span>Koszt bazowy</span>
                         <span>{subtotal.toLocaleString()} PLN</span>
                      </div>
                      <div className="flex items-center gap-4 py-4">
                         <div className="flex-1">
                            <label className="text-[9px] font-black text-brand-hover uppercase tracking-widest block mb-2">Marza zysku (%)</label>
                            <input
                              type="range"
                              min="0" max="100"
                              value={margin}
                              onChange={(e) => setMargin(parseInt(e.target.value))}
                              className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-brand"
                            />
                         </div>
                         <div className="w-16 text-center text-xl font-black italic text-white">{margin}%</div>
                      </div>
                   </div>

                   <div className="pt-6 border-t border-white/10 space-y-1">
                      <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Wielka Suma (Brutto)</span>
                      <div className="text-5xl font-black text-white italic tracking-tighter tabular-nums truncate">
                         {totalWithMargin.toLocaleString()} <span className="text-xl text-brand-hover not-italic">PLN</span>
                      </div>
                   </div>

                   <div className="pt-6">
                      <Button className="w-full py-8 rounded-2xl bg-brand text-white font-black italic uppercase text-lg hover:bg-brand-hover shadow-brand-glow transition-all">
                         GOTOWA OFERTA <ChevronRight className="ml-2 w-5 h-5" />
                      </Button>
                   </div>

                   <div className="p-4 rounded-xl bg-brand/5 border border-brand/10 flex items-start gap-3">
                      <Sparkles size={16} className="text-brand-hover shrink-0 mt-0.5" />
                      <p className="text-[11px] text-slate-400 font-bold leading-relaxed">
                         Strateg AI radzi: Projekt o tak wysokim standardzie (Lakier Mat) pozwala na zastosowanie marzy rzedu 35-40%.
                      </p>
                   </div>
                </div>
            </Card>

            {/* QUICK ACTIONS */}
            <div className="grid grid-cols-2 gap-4">
               <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex flex-col items-center text-center">
                  <Printer size={20} className="text-slate-500 mb-2" />
                  <span className="text-[8px] font-black text-slate-500 uppercase">Drukuj</span>
               </div>
               <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex flex-col items-center text-center">
                  <CheckCircle2 size={20} className="text-emerald-500 mb-2" />
                  <span className="text-[8px] font-black text-slate-500 uppercase">Status: Projektuj</span>
               </div>
            </div>
         </div>
      </div>
    </AppShell>
  );
}
