"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card, StatCard } from "@/components/ui";
import { Upload, Check, AlertCircle, Loader2, Save, ArrowRight, FileType } from "lucide-react";
import { useState, useMemo } from "react";
import { TechModulAPI } from "@/services/api";
import { useRouter } from "next/navigation";

export default function Import3dPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [importData, setImportData] = useState<{ summary: any; rows: any[] } | null>(null);
  const [finalizeLoading, setFinalizeLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const startParse = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.importParse(file);
      setImportData(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const finalize = async () => {
    if (!importData) return;
    setFinalizeLoading(true);
    try {
      const res = await TechModulAPI.importFinalize({
        title: importData.summary.name || "Import 3D",
        client_name: "Klient z Importu",
        rows: importData.rows
      });
      router.push(`/configuration?id=${res.project_id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setFinalizeLoading(false);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Integracja z 3D Constructor"
        title={<>Kreator <span className="text-brand-hover">Importu</span></>}
        subtitle="Wgraj plik .project, zmapuj materiay i stworz gotowy projekt w systemie Web."
      />

      <div className="max-w-5xl mx-auto">
        {!importData ? (
          <Card className="p-12 border-dashed border-2 flex flex-col items-center justify-center text-center">
            <div className="w-20 h-20 rounded-full bg-brand/10 flex items-center justify-center mb-6">
              <Upload className="w-10 h-10 text-brand" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Wybierz plik .project</h3>
            <p className="text-slate-400 mb-8 max-w-sm">Przeciagnij plik wyeksportowany z 3D Constructor, aby rozpoczac proces mapowania.</p>

            <input
              id="file-upload"
              type="file"
              accept=".project"
              onChange={handleFileChange}
              className="hidden"
            />

            <div className="flex flex-col items-center gap-4 w-full max-w-xs">
              <label
                htmlFor="file-upload"
                className="w-full py-4 rounded-xl border border-slate-700 bg-canvas-deep hover:bg-slate-800 transition-colors cursor-pointer flex items-center justify-center gap-2 font-medium"
              >
                <FileType className="w-4 h-4" />
                {file ? file.name : "Wybierz plik z dysku"}
              </label>

              <Button
                onClick={startParse}
                disabled={!file || loading}
                className="w-full py-6 text-lg"
              >
                {loading ? <Loader2 className="animate-spin mr-2" /> : <ArrowRight className="mr-2" />}
                Rozpocznij analize
              </Button>
            </div>

            {error && (
              <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex items-center gap-2 font-medium">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}
          </Card>
        ) : (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <StatCard label="Nazwa Projektu" value={importData.summary.name} />
              <StatCard label="Modu Gowny" value={importData.summary.module} />
              <StatCard label="Powierzchnia" value={`${importData.summary.area_m2.toFixed(2)} m2`} />
              <StatCard label="Elementy" value={importData.summary.parts_count} />
            </div>

            <Card className="overflow-hidden">
              <div className="p-6 border-b border-white/5 flex items-center justify-between bg-brand/5">
                <h3 className="font-semibold text-lg">Raport elementow do importu</h3>
                <span className="text-xs text-slate-400 px-3 py-1 rounded-full bg-white/5 tracking-wider">
                  WYMAGA WERYFIKACJI
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-canvas-deep text-slate-400 font-medium">
                      <th className="px-6 py-4 text-left">Sekcja</th>
                      <th className="px-6 py-4 text-left">Nazwa / Kod</th>
                      <th className="px-6 py-4 text-left">Wymiary (mm)</th>
                      <th className="px-6 py-4 text-left">Materia (Import)</th>
                      <th className="px-6 py-4 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {importData.rows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            row.section === 'Front' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-500/20 text-slate-400'
                          }`}>
                            {row.section}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-medium">{row.name}</div>
                          <div className="text-[10px] text-slate-500">{row.code}</div>
                        </td>
                        <td className="px-6 py-4 tabular-nums text-slate-300">
                          {row.length_mm} x {row.width_mm} x {row.thickness_mm}
                        </td>
                        <td className="px-6 py-4 text-slate-300 font-mono text-xs">
                          {row.material_original}
                        </td>
                        <td className="px-6 py-4 text-center">
                          {row.status === 'OK' ? (
                            <Check className="w-4 h-4 text-emerald-500 mx-auto" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-amber-500 mx-auto" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <div className="flex justify-end gap-4">
              <Button variant="secondary" onClick={() => setImportData(null)}>Anuluj i wroc</Button>
              <Button onClick={finalize} disabled={finalizeLoading} className="px-10 py-6">
                {finalizeLoading ? <Loader2 className="animate-spin mr-2" /> : <Save className="mr-2" />}
                Finalizuj i stworz projekt
              </Button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
