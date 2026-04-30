"use client";

import React, { useState } from "react";
import { Button, Card, Section } from "@/components/ui";
import { Search, BookOpen, GraduationCap, Clock, ChevronRight, FileText, Bookmark, Share2, Info, ArrowLeft } from "lucide-react";
import Link from 'next/link';

const SAMPLE_ARTICLES = [
  {
    id: 1,
    title: "Zasady wiercenia w pytach EGGER",
    summary: "Parametry posuwu i obrotow dla wierte diamentowych i HM.",
    category: "Obrobka",
    level: "Zaawansowany",
    readTime: "5 min",
    icon: "drill"
  },
  {
    id: 2,
    title: "Konfiguracja zawiasow Blum CLIP top",
    summary: "Instrukcja montazu i regulacji w trzech paszczyznach.",
    category: "Okucia",
    level: "Podstawowy",
    readTime: "8 min",
    icon: "tool"
  },
  {
    id: 3,
    title: "Obliczanie frontow wsuwanych",
    summary: "Wzory na szczeliny i odliczenia dla systemow bezuchwytowych.",
    category: "Projektowanie",
    level: "Sredni",
    readTime: "12 min",
    icon: "calc"
  }
];

export default function KnowledgeBasePage() {
  const [selectedArticle, setSelectedArticle] = useState<any>(null);

  return (
    <div className="flex h-[calc(100vh-140px)] gap-6 overflow-hidden">
      {/* LEFT: NAV */}
      <aside className="w-80 flex flex-col gap-6">
        <Section title="Eksploruj Wiedze">
           <div className="relative mb-4">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
             <input
               type="text"
               placeholder="Szukaj artykuow..."
               className="w-full bg-panel-solid/60 border border-subtle rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-brand/50 transition-colors"
             />
           </div>

           <div className="space-y-1">
             {["Wszystkie", "Montaz", "Obrobka CNC", "Projektowanie", "Okucia", "Materiay", "Normy BHP"].map(cat => (
               <button
                 key={cat}
                 className={`w-full text-left px-4 py-2.5 rounded-xl text-sm transition-colors flex items-center justify-between group ${cat === 'Wszystkie' ? 'bg-brand/10 text-brand' : 'hover:bg-white/5 text-slate-400 font-medium'}`}
               >
                 <span>{cat}</span>
                 <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded-full group-hover:bg-brand/20 transition-colors">12</span>
               </button>
             ))}
           </div>
        </Section>

        <Card className="bg-gradient-to-br from-brand/20 to-blue-600/10 border-brand/20 relative overflow-hidden">
           <GraduationCap className="absolute -bottom-4 -right-4 text-brand/20" size={120} />
           <h4 className="font-bold text-white mb-1 relative z-10">Akademia TECH_modul</h4>
           <p className="text-xs text-slate-300 mb-4 relative z-10">Certyfikowane kursy i szkolenia dla pracownikow produkcji.</p>
           <Button size="sm" className="relative z-10">Otworz kursy</Button>
        </Card>
      </aside>

      {/* CENTER: ARTICLES / CONTENT */}
      <main className="flex-1 overflow-y-auto pr-2 custom-scrollbar flex flex-col gap-6">
        {!selectedArticle ? (
          <>
            <header className="mb-2">
              <Link
                href="/database"
                className="inline-flex items-center gap-2 text-[10px] text-slate-500 hover:text-brand font-black uppercase tracking-widest mb-4 group transition-colors"
                id="back-to-hub-btn"
              >
                <div className="w-5 h-5 rounded-full border border-subtle flex items-center justify-center group-hover:border-brand/40 group-hover:bg-brand/10 transition-all">
                   <ArrowLeft size={10} />
                </div>
                Powrot do Centrum Baz Danych
              </Link>
              <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Baza Wiedzy Technicznej</h1>
              <p className="text-slate-400">Instrukcje, standardy zakadowe i parametry technologiczne w jednym miejscu.</p>
            </header>

            <Section title="Najnowsze Artykuy">
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {SAMPLE_ARTICLES.map(art => (
                  <Card
                    key={art.id}
                    className="hover:scale-[1.01] transition-transform cursor-pointer group"
                    onClick={() => setSelectedArticle(art)}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div className={`p-3 rounded-xl bg-slate-800 border border-subtle text-brand group-hover:bg-brand/10 transition-colors`}>
                        <BookOpen size={24} />
                      </div>
                      <div className="flex gap-2">
                        <span className="text-[10px] bg-white/5 px-2 py-1 rounded uppercase font-bold text-slate-500">{art.category}</span>
                      </div>
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2 group-hover:text-brand transition-colors">{art.title}</h3>
                    <p className="text-sm text-slate-400 mb-6">{art.summary}</p>
                    <div className="flex items-center gap-6 text-xs text-slate-500 font-medium">
                      <div className="flex items-center gap-2"><GraduationCap size={14} /> {art.level}</div>
                      <div className="flex items-center gap-2"><Clock size={14} /> {art.readTime}</div>
                    </div>
                  </Card>
                ))}
              </div>
            </Section>

            <Section title="Standardy Zakadowe (PDF)">
               <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                 {[
                   { t: "Standard Okleinowania 2024", c: "pdf" },
                   { t: "Katalog Okuc Blum 23/24", c: "pdf" },
                   { t: "System Szuflandii Standard", c: "pdf" },
                   { t: "Procedura Lakierowania", c: "doc" }
                 ].map((doc, idx) => (
                   <Card key={idx} className="flex flex-col items-center text-center p-4 hover:bg-white/5 transition-colors cursor-pointer group" padded={false}>
                      <div className="p-4 mb-3 rounded-lg bg-slate-900 border border-subtle text-slate-500 group-hover:text-slate-200 transition-colors">
                        <FileText size={32} />
                      </div>
                      <span className="text-xs font-semibold text-slate-400 px-2 line-clamp-2">{doc.t}</span>
                   </Card>
                 ))}
               </div>
            </Section>
          </>
        ) : (
          <article className="max-w-4xl mx-auto w-full pb-20">
            <Button variant="ghost" onClick={() => setSelectedArticle(null)} className="mb-8 font-medium">
              &larr; Wroc do bazy
            </Button>

            <header className="mb-10">
              <div className="flex items-center gap-2 mb-4 text-brand font-bold text-sm uppercase tracking-widest">
                <Bookmark size={14} /> {selectedArticle.category}
              </div>
              <h1 className="text-4xl font-extrabold text-white mb-6 tracking-tight leading-tight">{selectedArticle.title}</h1>
              <div className="flex items-center gap-6 p-4 rounded-2xl bg-panel-solid/40 border border-subtle">
                <div className="flex items-center gap-2 text-slate-400 text-sm"><GraduationCap size={18} className="text-brand" /> <strong>Poziom:</strong> {selectedArticle.level}</div>
                <div className="flex items-center gap-2 text-slate-400 text-sm"><Clock size={18} className="text-brand" /> <strong>Czas czytania:</strong> {selectedArticle.readTime}</div>
                <div className="flex-1" />
                <Button variant="ghost" size="sm"><Share2 size={16} /></Button>
              </div>
            </header>

            <div className="prose prose-invert max-w-none space-y-6 text-slate-300 leading-relaxed">
              <p className="text-lg text-slate-200">
                Dokument ten opisuje standardowe procedury i parametry obrobki wymagane dla osiagniecia najwyzszej jakosci wykonczenia przy wykorzystaniu parku maszynowego TECH_modul.
              </p>

              <div className="p-6 bg-blue-500/5 border-l-4 border-blue-500 rounded-r-2xl my-8">
                 <h4 className="text-blue-200 font-bold mb-2 flex items-center gap-2 italic">
                   <Info size={16} /> Wskazowka Technologa
                 </h4>
                 <p className="text-sm">
                   Zawsze sprawdzaj stan naostrzenia frezow przed przystapieniem do obrobki pyt laminowanych w dekorach o gebokiej strukturze. Zaleca sie posuw zredukowany o 15% na krawedziach wejsciowych.
                 </p>
              </div>

              <h3 className="text-2xl font-bold text-white mt-12 mb-4 font-mono uppercase tracking-tight border-b border-subtle pb-2">1. Parametry Techniczne</h3>
              <p>Podstawa poprawnej obrobki jest dobranie odpowiedniej predkosci obrotowej wrzeciona (n) oraz posuwu (vf) zgodnie ze wzorem:</p>

              <div className="bg-black/40 p-8 rounded-2xl font-mono text-brand text-2xl text-center my-8 border border-subtle/50 shadow-inner">
                 vf = fz * z * n
              </div>

              <table className="w-full border-collapse border border-subtle mt-6 overflow-hidden rounded-xl">
                <thead>
                  <tr className="bg-panel-raised text-left">
                    <th className="p-3 border border-subtle eyebrow">Materia</th>
                    <th className="p-3 border border-subtle eyebrow text-center">N [obr/min]</th>
                    <th className="p-3 border border-subtle eyebrow text-center">Posuw [m/min]</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="p-3 border border-subtle font-medium">Pyta Wiorowa</td>
                    <td className="p-3 border border-subtle text-center text-slate-400">18 000</td>
                    <td className="p-3 border border-subtle text-center text-slate-400">12 - 15</td>
                  </tr>
                  <tr className="bg-white/5">
                    <td className="p-3 border border-subtle font-medium">MDF Surowy</td>
                    <td className="p-3 border border-subtle text-center text-slate-400">16 000</td>
                    <td className="p-3 border border-subtle text-center text-slate-400">10 - 12</td>
                  </tr>
                </tbody>
              </table>

              <h3 className="text-2xl font-bold text-white mt-12 mb-4 font-mono uppercase tracking-tight border-b border-subtle pb-2">2. Kontrola Jakosci</h3>
              <p>Po kazdym cyklu obrobki operator zobowiazany jest do sprawdzenia krawedzi pod katem wyrwan oraz poprawnosci wymiarowej przy uzyciu suwmiarki elektronicznej z dokadnoscia do 0.05 mm.</p>
            </div>
          </article>
        )}
      </main>
    </div>
  );
}
