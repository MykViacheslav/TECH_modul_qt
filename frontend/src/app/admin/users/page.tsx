"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI } from "@/services/api";
import { useCurrentUser } from "@/services/user-context";
import { Users, Shield, Plus, Lock, KeyRound, Check, X, UserX, UserCheck } from "lucide-react";
import clsx from "clsx";

export default function AdminUsersPage() {
  const [user, , loading] = useCurrentUser();
  const [users, setUsers] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Create user state
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("operator");
  const [newPassword, setNewPassword] = useState("");

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      const data = await TechModulAPI.getAdminUsers();
      setUsers(data || []);
    } catch (e: any) {
      alert("Błąd ładowania użytkowników: " + e.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!loading && user?.role === "admin") {
      loadUsers();
    }
  }, [loading, user]);

  if (loading) return <div className="p-20 text-center">Ładowanie...</div>;
  
  if (user?.role !== "admin") {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <Shield className="w-16 h-16 mb-4 text-red-500/20" />
          <h2 className="text-xl font-bold text-white">Brak uprawnień</h2>
          <p>Ta strona jest dostępna tylko dla administratorów.</p>
        </div>
      </AppShell>
    );
  }

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await TechModulAPI.createAdminUser({ name: newName, role: newRole, password: newPassword });
      setNewName("");
      setNewPassword("");
      setShowCreate(false);
      loadUsers();
    } catch (err: any) {
      alert("Błąd: " + err.message);
    }
  };

  const handleUpdateRole = async (userId: number, role: string) => {
    try {
      await TechModulAPI.updateAdminUser(userId, { role });
      loadUsers();
    } catch (err: any) {
      alert("Błąd: " + err.message);
    }
  };

  const handleToggleActive = async (userId: number, currentActive: number) => {
    try {
      await TechModulAPI.updateAdminUser(userId, { is_active: currentActive ? 0 : 1 });
      loadUsers();
    } catch (err: any) {
      alert("Błąd: " + err.message);
    }
  };

  const handleResetPassword = async (userId: number) => {
    const pw = prompt("Podaj nowe hasło dla tego użytkownika:");
    if (!pw) return;
    try {
      await TechModulAPI.updateAdminUser(userId, { password: pw });
      alert("Hasło zostało zmienione.");
    } catch (err: any) {
      alert("Błąd: " + err.message);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Administracja"
        title="Użytkownicy Systemu"
        subtitle="Zarządzaj kontami, uprawnieniami i hasłami"
        actions={
          <Button onClick={() => setShowCreate(!showCreate)} className="bg-brand text-white hover:bg-brand/90">
            {showCreate ? <X className="w-4 h-4 mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
            {showCreate ? "Anuluj" : "Nowy użytkownik"}
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto pb-20 space-y-6">
        {showCreate && (
          <Card className="p-6 border-brand/30 bg-brand/5">
            <h3 className="text-lg font-bold text-white mb-4">Dodaj nowego użytkownika</h3>
            <form onSubmit={handleCreateUser} className="flex flex-col md:flex-row gap-4 items-end">
              <div className="flex-1 space-y-1">
                <label className="text-xs text-slate-400 font-bold uppercase">Imię i Nazwisko</label>
                <input required value={newName} onChange={e => setNewName(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-white" />
              </div>
              <div className="w-48 space-y-1">
                <label className="text-xs text-slate-400 font-bold uppercase">Rola</label>
                <select value={newRole} onChange={e => setNewRole(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-white outline-none">
                  <option value="admin">Admin</option>
                  <option value="manager">Manager</option>
                  <option value="operator">Operator (Produkcja)</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
              <div className="flex-1 space-y-1">
                <label className="text-xs text-slate-400 font-bold uppercase">Hasło startowe</label>
                <input required type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-white" />
              </div>
              <Button type="submit" className="bg-emerald-600 hover:bg-emerald-500 text-white py-2 h-[42px]">Zapisz</Button>
            </form>
          </Card>
        )}

        <Card padded={false} className="overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white/5 border-b border-white/10 text-xs uppercase tracking-wider text-slate-400">
                <th className="p-4 font-bold">ID</th>
                <th className="p-4 font-bold">Użytkownik</th>
                <th className="p-4 font-bold">Rola</th>
                <th className="p-4 font-bold">Status</th>
                <th className="p-4 font-bold">Ostatnia Aktywność</th>
                <th className="p-4 font-bold text-right">Akcje</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-sm">
              {users.map(u => (
                <tr key={u.id} className={clsx("hover:bg-white/5 transition-colors", !u.is_active && "opacity-50")}>
                  <td className="p-4 text-slate-500 font-mono">#{u.id}</td>
                  <td className="p-4 font-medium text-white flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-slate-800 border border-white/10 flex items-center justify-center text-xs font-bold" style={{ color: u.avatar_color || '#3b82f6' }}>
                      {u.name.substring(0, 2).toUpperCase()}
                    </div>
                    {u.name}
                  </td>
                  <td className="p-4">
                    <select 
                      value={u.role}
                      onChange={e => handleUpdateRole(u.id, e.target.value)}
                      disabled={!u.is_active || u.id === user?.id}
                      className="bg-black/20 border border-white/10 rounded px-2 py-1 text-slate-300 outline-none focus:border-brand disabled:opacity-50"
                    >
                      <option value="admin">Admin</option>
                      <option value="manager">Manager</option>
                      <option value="operator">Operator</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  </td>
                  <td className="p-4">
                    {u.is_active ? (
                      <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 text-xs font-bold border border-emerald-500/20">
                        <Check className="w-3 h-3" /> Aktywny
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-red-500/10 text-red-400 text-xs font-bold border border-red-500/20">
                        <X className="w-3 h-3" /> Zablokowany
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-slate-400">
                    {u.last_active ? u.last_active.split(".")[0] : "-"}
                  </td>
                  <td className="p-4 text-right flex items-center justify-end gap-2">
                    <Button 
                      variant="ghost" 
                      onClick={() => handleResetPassword(u.id)}
                      className="text-slate-400 hover:text-white"
                      title="Zmień hasło"
                    >
                      <KeyRound className="w-4 h-4" />
                    </Button>
                    {u.id !== user?.id && (
                      <Button 
                        variant="ghost" 
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                        className={u.is_active ? "text-red-400 hover:bg-red-500/10" : "text-emerald-400 hover:bg-emerald-500/10"}
                        title={u.is_active ? "Zablokuj" : "Odblokuj"}
                      >
                        {u.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </AppShell>
  );
}
