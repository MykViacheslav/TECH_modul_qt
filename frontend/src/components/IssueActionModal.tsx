"use client";

import React, { useState, useEffect } from "react";
import { TechModulAPI, type OperationsIssueRecord } from "@/services/api";
import { Button, Card } from "@/components/ui";
import { X, User, Calendar, Flag, CheckCircle2, AlertCircle } from "lucide-react";
import clsx from "clsx";

interface IssueActionModalProps {
  issue: OperationsIssueRecord;
  isOpen: boolean;
  onClose: () => void;
  onUpdate: () => void;
}

const STATUS_OPTIONS = [
  { value: "nowe", label: "Open", icon: AlertCircle, color: "text-blue-400" },
  { value: "w_toku", label: "In Progress", icon: Flag, color: "text-amber-400" },
  { value: "zablokowane", label: "Blocked", icon: X, color: "text-red-400" },
  { value: "zamkniete", label: "Resolved", icon: CheckCircle2, color: "text-emerald-400" },
];

const PRIORITY_OPTIONS = [
  { value: "niski", label: "Low" },
  { value: "normalny", label: "Medium" },
  { value: "wysoki", label: "High" },
  { value: "krytyczny", label: "Critical" },
];

export default function IssueActionModal({ issue, isOpen, onClose, onUpdate }: IssueActionModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [technicians, setTechnicians] = useState<any[]>([]);
  
  // Form state
  const [status, setStatus] = useState(issue.status);
  const [owner, setOwner] = useState(issue.owner || "");
  const [priority, setPriority] = useState(issue.priority_manual);
  const [dueDate, setDueDate] = useState(issue.due_date || "");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (isOpen) {
      TechModulAPI.getTechnicians().then(setTechnicians).catch(console.error);
      setStatus(issue.status);
      setOwner(issue.owner || "");
      setPriority(issue.priority_manual);
      setDueDate(issue.due_date || "");
      setNote("");
      setError(null);
    }
  }, [isOpen, issue]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await TechModulAPI.patchOperationsIssue(issue.id, {
        status,
        owner,
        priority_manual: priority,
        due_date: dueDate,
        notes: note ? (issue.notes ? `${issue.notes}\n---\n${note}` : note) : undefined
      });
      onUpdate();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to update issue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <Card className="w-full max-w-lg shadow-2xl border-white/10" padded={false}>
        <div className="p-4 border-b border-white/10 flex items-center justify-between bg-panel-solid/50">
          <div>
            <p className="text-[10px] text-brand font-black uppercase tracking-widest mb-0.5">Issue Update</p>
            <h2 className="text-sm font-bold text-white truncate max-w-[300px]">{issue.title || issue.id}</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-lg transition-colors">
            <X size={18} className="text-slate-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
              {error}
            </div>
          )}

          {/* Status Selection */}
          <div>
            <label className="text-[10px] text-slate-500 uppercase font-black mb-2 block">Status</label>
            <div className="grid grid-cols-2 gap-2">
              {STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setStatus(opt.value)}
                  className={clsx(
                    "flex items-center gap-2 p-2 rounded-lg border text-xs font-bold transition-all",
                    status === opt.value 
                      ? "bg-brand/10 border-brand text-white shadow-brand-glow" 
                      : "bg-white/5 border-white/5 text-slate-400 hover:bg-white/10"
                  )}
                >
                  <opt.icon className={clsx("w-3.5 h-3.5", opt.color)} />
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Owner dropdown */}
            <div>
              <label className="text-[10px] text-slate-500 uppercase font-black mb-2 block">Owner</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <select
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                  className="w-full bg-panel-solid border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-none focus:border-brand/50 appearance-none"
                >
                  <option value="">Unassigned</option>
                  {technicians.map((t) => (
                    <option key={t.id} value={t.name}>{t.name}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Priority dropdown */}
            <div>
              <label className="text-[10px] text-slate-500 uppercase font-black mb-2 block">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full bg-panel-solid border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand/50 appearance-none"
              >
                {PRIORITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Due Date */}
          <div>
            <label className="text-[10px] text-slate-500 uppercase font-black mb-2 block">Due Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full bg-panel-solid border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-none focus:border-brand/50 [color-scheme:dark]"
              />
            </div>
          </div>

          {/* Resolution Note */}
          <div>
            <label className="text-[10px] text-slate-500 uppercase font-black mb-2 block">Add Note / Resolution Details</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Explain what happened or what needs to be done..."
              className="w-full bg-panel-solid border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand/50 min-h-[100px] resize-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? "Updating..." : "Save Changes"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
