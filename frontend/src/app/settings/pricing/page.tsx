"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import { 
  ChevronLeft, 
  Plus, 
  Save, 
  X, 
  Loader2, 
  Edit2, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  Settings2
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { TechModulAPI, type OperationTariff } from "@/services/api";
import clsx from "clsx";

const CATEGORIES = ["Oklejanie", "Ciecie", "CNC Fronty", "Inne"];
const OPERATION_TYPES = [
  { value: "EDGE_BANDING", label: "Oklejanie" },
  { value: "CUTTING", label: "Cięcie" },
  { value: "CNC_FRONT", label: "Front Gładki" },
  { value: "CNC_FRAME", label: "Front Ramka" },
  { value: "CNC_RIBBED", label: "Front Ryflowany" },
  { value: "OTHER", label: "Inne" },
];
const UNITS = ["mb", "m2", "szt", "godz", "fixed"];

const baseInput = "w-full rounded border border-[#333] bg-[#2d2d2d] px-3 py-2 text-[12px] outline-none focus:border-blue-500 transition-colors placeholder:text-slate-600";

export default function PricingSettingsPage() {
  const router = useRouter();
  const [tariffs, setTariffs] = useState<OperationTariff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<Partial<OperationTariff>>({
    code: "",
    name: "",
    category: "Inne",
    operation_type: "OTHER",
    unit: "szt",
    sell_rate_net: 0,
    internal_cost_net: 0,
    vat_rate: 23,
    min_charge_net: 0,
    is_active: 1,
    description: "",
  });

  const loadTariffs = async () => {
    setLoading(true);
    try {
      const data = await TechModulAPI.getOperationTariffs(false);
      setTariffs(data);
    } catch (e: any) {
      setError(e?.message ?? "Blad pobierania cennika");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTariffs();
  }, []);

  const handleEdit = (tariff: OperationTariff) => {
    setEditingId(tariff.id);
    setForm({ ...tariff });
    setIsEditing(true);
    setError(null);
    setSuccess(null);
  };

  const handleAddNew = () => {
    setEditingId(null);
    setForm({
      code: "",
      name: "",
      category: "Inne",
      operation_type: "OTHER",
      unit: "szt",
      sell_rate_net: 0,
      internal_cost_net: 0,
      vat_rate: 23,
      min_charge_net: 0,
      is_active: 1,
      description: "",
    });
    setIsEditing(true);
    setError(null);
    setSuccess(null);
  };

  const validate = () => {
    if (!form.name?.trim()) return "Nazwa jest wymagana";
    if (!form.code?.trim()) return "Kod jest wymagany";
    if (form.sell_rate_net === undefined || form.sell_rate_net < 0) return "Cena sprzedazy musi byc >= 0";
    return null;
  };

  const handleSave = async () => {
    const valError = validate();
    if (valError) {
      setError(valError);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      if (editingId) {
        await TechModulAPI.updateOperationTariff(editingId, form);
        setSuccess("Taryfa zaktualizowana pomyslnie");
      } else {
        await TechModulAPI.createOperationTariff(form);
        setSuccess("Nowa taryfa dodana pomyslnie");
      }
      setIsEditing(false);
      await loadTariffs();
    } catch (e: any) {
      setError(e?.message ?? "Blad zapisu");
    } finally {
      setLoading(false);
    }
  };

  const toggleActive = async (tariff: OperationTariff) => {
    try {
      await TechModulAPI.updateOperationTariff(tariff.id, { is_active: tariff.is_active ? 0 : 1 });
      await loadTariffs();
    } catch (e: any) {
      setError("Blad zmiany statusu");
    }
  };

  return (
    <AppShell>
      <div className="flex flex-col h-full overflow-hidden">
        <div className="shrink-0">
          <div className="flex items-center gap-2 mb-2">
            <Button variant="ghost" size="sm" onClick={() => router.push("/settings")}>
              <ChevronLeft className="w-4 h-4 mr-1" /> Powrot do ustawien
            </Button>
          </div>
          <PageHeader
            eyebrow="Konfiguracja finansowa"
            title={<>Cennik <span className="text-brand-hover">obróbki</span></>}
            subtitle="Zarządzaj stawkami za oklejanie, cięcie i operacje CNC."
            actions={
              !isEditing && (
                <Button onClick={handleAddNew} className="bg-brand-hover hover:bg-brand-soft">
                  <Plus className="w-4 h-4 mr-2" /> Dodaj taryfę
                </Button>
              )
            }
          />
        </div>

        <div className="flex-1 overflow-auto custom-scrollbar p-1">
          {error && (
            <div className="mb-4 flex items-center gap-2 rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-red-300 text-sm">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 flex items-center gap-2 rounded border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-emerald-300 text-sm">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              {success}
            </div>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-6 items-start">
            {/* List Table */}
            <Card className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11px] border-collapse">
                  <thead className="bg-[#1a1a1a] text-slate-400 uppercase tracking-wider sticky top-0 z-10">
                    <tr>
                      <th className="px-4 py-3 border-b border-[#333]">Status</th>
                      <th className="px-4 py-3 border-b border-[#333]">Nazwa / Kod</th>
                      <th className="px-4 py-3 border-b border-[#333]">Kategoria</th>
                      <th className="px-4 py-3 border-b border-[#333]">Cena (Netto)</th>
                      <th className="px-4 py-3 border-b border-[#333]">Jedn.</th>
                      <th className="px-4 py-3 border-b border-[#333] text-right">Akcje</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#2a2a2a]">
                    {loading && tariffs.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                          Ladowanie taryf...
                        </td>
                      </tr>
                    ) : tariffs.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                          Brak zdefiniowanych taryf.
                        </td>
                      </tr>
                    ) : (
                      tariffs.map((t) => (
                        <tr 
                          key={t.id} 
                          className={clsx(
                            "hover:bg-white/[0.02] transition-colors",
                            !t.is_active && "opacity-50 grayscale-[0.5]"
                          )}
                        >
                          <td className="px-4 py-3 whitespace-nowrap">
                            <button 
                              onClick={() => toggleActive(t)}
                              className={clsx(
                                "flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-black uppercase",
                                t.is_active 
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : "bg-slate-500/10 text-slate-400 border border-slate-500/20"
                              )}
                            >
                              {t.is_active ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                              {t.is_active ? "Aktywna" : "Nieaktywna"}
                            </button>
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-bold text-slate-200">{t.name}</div>
                            <div className="text-[10px] text-slate-500 font-mono">{t.code}</div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-slate-400">
                            {t.category}
                          </td>
                          <td className="px-4 py-3 font-bold text-brand-hover">
                            {t.sell_rate_net.toFixed(2)} PLN
                          </td>
                          <td className="px-4 py-3 text-slate-400">
                            {t.unit}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-7 w-7 p-0"
                              onClick={() => handleEdit(t)}
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Edit / Add Form */}
            {isEditing ? (
              <Card className="border-blue-500/30 bg-blue-500/5 sticky top-0">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-black uppercase tracking-widest text-blue-300">
                    {editingId ? "Edytuj taryfę" : "Dodaj nową taryfę"}
                  </h3>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => setIsEditing(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Nazwa usługi</label>
                    <input 
                      className={baseInput}
                      value={form.name}
                      onChange={(e) => setForm({...form, name: e.target.value})}
                      placeholder="np. Oklejanie standard"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Kod</label>
                      <input 
                        className={clsx(baseInput, "font-mono")}
                        value={form.code}
                        onChange={(e) => setForm({...form, code: e.target.value.toUpperCase()})}
                        placeholder="np. EDGE_STD"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Jednostka</label>
                      <select 
                        className={baseInput}
                        value={form.unit}
                        onChange={(e) => setForm({...form, unit: e.target.value})}
                      >
                        {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Kategoria</label>
                      <select 
                        className={baseInput}
                        value={form.category}
                        onChange={(e) => setForm({...form, category: e.target.value})}
                      >
                        {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Typ operacji</label>
                      <select 
                        className={baseInput}
                        value={form.operation_type}
                        onChange={(e) => setForm({...form, operation_type: e.target.value})}
                      >
                        {OPERATION_TYPES.map(ot => <option key={ot.value} value={ot.value}>{ot.label}</option>)}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Koszt wewn. netto</label>
                      <input 
                        type="number"
                        className={baseInput}
                        value={form.internal_cost_net}
                        onChange={(e) => setForm({...form, internal_cost_net: Number(e.target.value)})}
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Cena sprzed. netto</label>
                      <input 
                        type="number"
                        className={clsx(baseInput, "font-bold text-brand-hover")}
                        value={form.sell_rate_net}
                        onChange={(e) => setForm({...form, sell_rate_net: Number(e.target.value)})}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">VAT %</label>
                      <input 
                        type="number"
                        className={baseInput}
                        value={form.vat_rate}
                        onChange={(e) => setForm({...form, vat_rate: Number(e.target.value)})}
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Min. opłata netto</label>
                      <input 
                        type="number"
                        className={baseInput}
                        value={form.min_charge_net}
                        onChange={(e) => setForm({...form, min_charge_net: Number(e.target.value)})}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Opis</label>
                    <textarea 
                      className={clsx(baseInput, "h-20 resize-none")}
                      value={form.description}
                      onChange={(e) => setForm({...form, description: e.target.value})}
                    />
                  </div>

                  <div className="flex items-center gap-2 pt-2">
                    <Button 
                      className="flex-1 bg-blue-600 hover:bg-blue-500"
                      onClick={handleSave}
                      disabled={loading}
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                      Zapisz taryfę
                    </Button>
                    <Button 
                      variant="secondary"
                      onClick={() => setIsEditing(false)}
                    >
                      Anuluj
                    </Button>
                  </div>
                </div>
              </Card>
            ) : (
              <Card className="flex flex-col items-center justify-center text-center p-8 border-dashed border-[#333] bg-transparent">
                <Settings2 className="w-12 h-12 text-slate-700 mb-4" />
                <h4 className="text-slate-400 font-bold mb-1">Zarządzanie cennikiem</h4>
                <p className="text-[10px] text-slate-600 max-w-[200px]">
                  Wybierz taryfę z listy po lewej aby ją edytować lub dodaj nową pozycję do cennika.
                </p>
                <Button variant="secondary" className="mt-6" onClick={handleAddNew}>
                  <Plus className="w-4 h-4 mr-2" /> Dodaj taryfę
                </Button>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
