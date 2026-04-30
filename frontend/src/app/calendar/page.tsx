"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import {
  TechModulAPI,
  type CalendarEventPayload,
  type CalendarEventRecord,
} from "@/services/api";
import {
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Filter,
  MapPin,
  Plus,
  RefreshCw,
  Trash2,
  User,
} from "lucide-react";

type CalendarView = "month" | "week" | "day";
type PanelMode = "empty" | "create" | "edit";

type EventTypeId =
  | "measurement"
  | "installation"
  | "meeting"
  | "transport"
  | "production"
  | "service"
  | "other";

type EventFormState = {
  title: string;
  type: EventTypeId;
  status: string;
  allDay: boolean;
  startDate: string;
  endDate: string;
  startTime: string;
  endTime: string;
  clientName: string;
  projectRef: string;
  location: string;
  assignedTo: string;
  notes: string;
};

type CalendarEventViewModel = CalendarEventRecord & {
  normalizedType: EventTypeId;
  startDateTime: Date;
  endDateTime: Date;
  startDayKey: string;
  endDayKey: string;
  assignedLabel: string;
  projectLabel: string;
  statusLabel: string;
};

const EVENT_TYPES: Array<{
  id: EventTypeId;
  label: string;
  short: string;
  chipClass: string;
  pillClass: string;
}> = [
  {
    id: "measurement",
    label: "Pomiar",
    short: "PM",
    chipClass: "border-sky-500/40 bg-sky-500/12 text-sky-200",
    pillClass: "bg-sky-500 text-white",
  },
  {
    id: "installation",
    label: "Montaz",
    short: "MN",
    chipClass: "border-emerald-500/40 bg-emerald-500/12 text-emerald-200",
    pillClass: "bg-emerald-500 text-white",
  },
  {
    id: "meeting",
    label: "Spotkanie",
    short: "SP",
    chipClass: "border-amber-500/40 bg-amber-500/12 text-amber-200",
    pillClass: "bg-amber-500 text-slate-950",
  },
  {
    id: "transport",
    label: "Transport",
    short: "TR",
    chipClass: "border-violet-500/40 bg-violet-500/12 text-violet-200",
    pillClass: "bg-violet-500 text-white",
  },
  {
    id: "production",
    label: "Produkcja",
    short: "PR",
    chipClass: "border-indigo-500/40 bg-indigo-500/12 text-indigo-200",
    pillClass: "bg-indigo-500 text-white",
  },
  {
    id: "service",
    label: "Serwis",
    short: "SR",
    chipClass: "border-rose-500/40 bg-rose-500/12 text-rose-200",
    pillClass: "bg-rose-500 text-white",
  },
  {
    id: "other",
    label: "Inne",
    short: "IN",
    chipClass: "border-slate-500/40 bg-slate-500/12 text-slate-200",
    pillClass: "bg-slate-500 text-white",
  },
];

const STATUS_OPTIONS = [
  { id: "planned", label: "Planned" },
  { id: "confirmed", label: "Confirmed" },
  { id: "in_progress", label: "In progress" },
  { id: "done", label: "Done" },
  { id: "cancelled", label: "Cancelled" },
];

const EVENT_TYPE_ALIASES: Record<string, EventTypeId> = {
  measurement: "measurement",
  installation: "installation",
  meeting: "meeting",
  transport: "transport",
  production: "production",
  service: "service",
  other: "other",
  pomiary: "measurement",
  pomiar: "measurement",
  montaz: "installation",
  "montaż": "installation",
  zlecenie: "production",
  wstepna_wycena: "meeting",
  zamowienie_mat: "transport",
  poprawki: "service",
  badania: "other",
  bhp: "other",
  urlop: "other",
  delegacja: "transport",
  produkcja: "production",
  serwis: "service",
  inne: "other",
};

function resolveEventType(raw?: string): EventTypeId {
  const key = (raw || "").trim().toLowerCase();
  return EVENT_TYPE_ALIASES[key] || "other";
}

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

function dateKey(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function parseStoredDateTime(value: string): Date {
  if (!value) return new Date(NaN);
  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnlyMatch) {
    const [, year, month, day] = dateOnlyMatch;
    return new Date(Number(year), Number(month) - 1, Number(day), 0, 0, 0, 0);
  }
  return new Date(value);
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
}

function endOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
}

function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

function startOfWeek(date: Date): Date {
  const current = startOfDay(date);
  const day = current.getDay();
  const delta = day === 0 ? -6 : 1 - day;
  return addDays(current, delta);
}

function sameDay(left: Date, right: Date): boolean {
  return dateKey(left) === dateKey(right);
}

function formatMonthTitle(date: Date): string {
  return new Intl.DateTimeFormat("pl-PL", {
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatLongDate(date: Date): string {
  return new Intl.DateTimeFormat("pl-PL", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatShortDay(date: Date): string {
  return new Intl.DateTimeFormat("pl-PL", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  }).format(date);
}

function formatTime(date: Date): string {
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

function typeMeta(typeId?: string) {
  return EVENT_TYPES.find((item) => item.id === typeId) ?? EVENT_TYPES[EVENT_TYPES.length - 1];
}

function statusLabel(status?: string): string {
  return STATUS_OPTIONS.find((item) => item.id === status)?.label ?? (status || "planned");
}

function buildDefaultForm(seedDate: Date = new Date()): EventFormState {
  const baseDate = dateKey(seedDate);
  return {
    title: "",
    type: "installation",
    status: "planned",
    allDay: true,
    startDate: baseDate,
    endDate: baseDate,
    startTime: "08:00",
    endTime: "10:00",
    clientName: "",
    projectRef: "",
    location: "",
    assignedTo: "",
    notes: "",
  };
}

function buildFormFromEvent(event: CalendarEventViewModel): EventFormState {
  return {
    title: event.title || "",
    type: event.normalizedType,
    status: event.status || "planned",
    allDay: Boolean(event.all_day),
    startDate: dateKey(event.startDateTime),
    endDate: dateKey(event.endDateTime),
    startTime: formatTime(event.startDateTime),
    endTime: formatTime(event.endDateTime),
    clientName: event.client_name || "",
    projectRef: event.projectLabel,
    location: event.location || "",
    assignedTo: event.assignedLabel,
    notes: event.notes || "",
  };
}

function buildPayloadFromForm(form: EventFormState): CalendarEventPayload {
  const payload: CalendarEventPayload = {
    title: form.title.trim(),
    type: form.type,
    all_day: form.allDay,
    client_name: form.clientName.trim(),
    project_ref: form.projectRef.trim(),
    location: form.location.trim(),
    assigned_to: form.assignedTo.trim(),
    notes: form.notes.trim(),
    status: form.status,
  };

  if (form.allDay) {
    payload.start_at = form.startDate;
    payload.end_at = form.endDate || form.startDate;
  } else {
    payload.start_at = `${form.startDate}T${form.startTime}`;
    payload.end_at = `${form.endDate || form.startDate}T${form.endTime}`;
  }

  return payload;
}

function eventOccursOnDay(event: CalendarEventViewModel, day: Date): boolean {
  const dayStart = startOfDay(day);
  const dayEnd = endOfDay(day);
  return event.startDateTime <= dayEnd && event.endDateTime >= dayStart;
}

function sortEvents(events: CalendarEventViewModel[]): CalendarEventViewModel[] {
  return [...events].sort((left, right) => {
    const diff = left.startDateTime.getTime() - right.startDateTime.getTime();
    if (diff !== 0) return diff;
    return left.title.localeCompare(right.title);
  });
}

function normalizeEvents(events: CalendarEventRecord[]): CalendarEventViewModel[] {
  return events
    .map((event) => {
      const normalizedType = resolveEventType(event.type || event.event_type);
      const startDateTime = parseStoredDateTime(event.start_at || event.date || event.date_from || "");
      const endRaw = event.end_at || event.date_end || event.date_to || event.start_at || event.date || event.date_from || "";
      const endDateTime = parseStoredDateTime(endRaw);
      const safeEnd = Number.isNaN(endDateTime.getTime()) ? startDateTime : endDateTime;
      return {
        ...event,
        normalizedType: EVENT_TYPES.some((item) => item.id === normalizedType) ? normalizedType : "other",
        startDateTime,
        endDateTime: safeEnd < startDateTime ? startDateTime : safeEnd,
        startDayKey: dateKey(startDateTime),
        endDayKey: dateKey(safeEnd < startDateTime ? startDateTime : safeEnd),
        assignedLabel: event.assigned_to || event.worker_name || "",
        projectLabel: event.project_ref || event.order_code || "",
        statusLabel: statusLabel(event.status),
      };
    })
    .filter((event) => !Number.isNaN(event.startDateTime.getTime()));
}

function EventChip({
  event,
  active,
  onClick,
}: {
  event: CalendarEventViewModel;
  active?: boolean;
  onClick: () => void;
}) {
  const meta = typeMeta(event.normalizedType);
  const timeLabel = event.all_day ? "All day" : `${formatTime(event.startDateTime)} - ${formatTime(event.endDateTime)}`;
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", event.id);
        e.dataTransfer.effectAllowed = "move";
        if (e.currentTarget instanceof HTMLElement) {
          e.currentTarget.style.opacity = "0.4";
        }
      }}
      onDragEnd={(e) => {
        if (e.currentTarget instanceof HTMLElement) {
          e.currentTarget.style.opacity = "1";
        }
      }}
      onClick={onClick}
      className={[
        "w-full cursor-grab rounded-xl border px-3 py-2 text-left transition-colors active:cursor-grabbing",
        meta.chipClass,
        active ? "ring-2 ring-white/70" : "hover:bg-white/10",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{event.title || "Untitled event"}</div>
          <div className="mt-1 flex flex-wrap gap-2 text-[11px] opacity-85">
            <span>{timeLabel}</span>
            {event.assignedLabel && <span>{event.assignedLabel}</span>}
          </div>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${meta.pillClass}`}>
          {meta.short}
        </span>
      </div>
    </div>
  );
}

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEventRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>("");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [view, setView] = useState<CalendarView>("month");
  const [panelMode, setPanelMode] = useState<PanelMode>("empty");
  const [selectedEventId, setSelectedEventId] = useState<string>("");
  const [form, setForm] = useState<EventFormState>(() => buildDefaultForm(new Date()));
  const [filters, setFilters] = useState({
    type: "all",
    worker: "all",
    status: "all",
  });
  const [dragOverDay, setDragOverDay] = useState<string>("");

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await TechModulAPI.getCalendarEvents(2000);
      setEvents(response.events || []);
    } catch (loadError: any) {
      setError(loadError?.message || "Nie udalo sie pobrac kalendarza");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadEvents();
  }, []);

  const normalizedEvents = useMemo(() => sortEvents(normalizeEvents(events)), [events]);

  const workerOptions = useMemo(() => {
    const workers = new Set<string>();
    normalizedEvents.forEach((event) => {
      if (event.assignedLabel.trim()) workers.add(event.assignedLabel.trim());
    });
    return Array.from(workers).sort((left, right) => left.localeCompare(right));
  }, [normalizedEvents]);

  const filteredEvents = useMemo(() => {
    return normalizedEvents.filter((event) => {
      if (filters.type !== "all" && event.normalizedType !== filters.type) return false;
      if (filters.worker !== "all" && event.assignedLabel !== filters.worker) return false;
      if (filters.status !== "all" && (event.status || "planned") !== filters.status) return false;
      return true;
    });
  }, [filters, normalizedEvents]);

  const selectedEvent = useMemo(
    () => filteredEvents.find((event) => event.id === selectedEventId) || normalizedEvents.find((event) => event.id === selectedEventId) || null,
    [filteredEvents, normalizedEvents, selectedEventId]
  );

  const eventsTodayCount = useMemo(() => filteredEvents.filter((event) => eventOccursOnDay(event, new Date())).length, [filteredEvents]);
  const weekStart = startOfWeek(currentDate);
  const weekEnd = addDays(weekStart, 6);
  const eventsThisWeekCount = useMemo(
    () =>
      filteredEvents.filter(
        (event) => event.startDateTime <= endOfDay(weekEnd) && event.endDateTime >= startOfDay(weekStart)
      ).length,
    [filteredEvents, weekEnd, weekStart]
  );

  const openCreatePanel = (seedDate?: Date) => {
    const base = seedDate ?? currentDate;
    setPanelMode("create");
    setSelectedEventId("");
    setForm(buildDefaultForm(base));
    setError("");
  };

  const openEditPanel = (event: CalendarEventViewModel) => {
    setPanelMode("edit");
    setSelectedEventId(event.id);
    setForm(buildFormFromEvent(event));
    setError("");
  };

  const closePanel = () => {
    setPanelMode("empty");
    setSelectedEventId("");
    setError("");
  };

  const changeDateWindow = (direction: -1 | 1) => {
    const next = new Date(currentDate);
    if (view === "month") next.setMonth(next.getMonth() + direction);
    if (view === "week") next.setDate(next.getDate() + 7 * direction);
    if (view === "day") next.setDate(next.getDate() + direction);
    setCurrentDate(next);
  };

  const handleSave = async () => {
    if (!form.title.trim()) {
      setError("Title is required.");
      return;
    }

    const payload = buildPayloadFromForm(form);
    const startCandidate = parseStoredDateTime(String(payload.start_at || ""));
    const endCandidate = parseStoredDateTime(String(payload.end_at || ""));
    if (Number.isNaN(startCandidate.getTime()) || Number.isNaN(endCandidate.getTime())) {
      setError("Date or time is invalid.");
      return;
    }
    if (endCandidate.getTime() < startCandidate.getTime()) {
      setError("End cannot be before start.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const response =
        panelMode === "edit" && selectedEventId
          ? await TechModulAPI.patchCalendarEvent(selectedEventId, payload)
          : await TechModulAPI.createCalendarEvent(payload);
      await loadEvents();
      const saved = response.event;
      const refreshed = sortEvents(normalizeEvents([saved]))[0];
      if (refreshed) openEditPanel(refreshed);
      else closePanel();
    } catch (saveError: any) {
      setError(saveError?.message || "Nie udalo sie zapisac zdarzenia");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedEventId) return;
    if (!window.confirm("Delete this event?")) return;
    setSaving(true);
    setError("");
    try {
      await TechModulAPI.deleteCalendarEvent(selectedEventId);
      await loadEvents();
      closePanel();
    } catch (deleteError: any) {
      setError(deleteError?.message || "Nie udalo sie usunac zdarzenia");
    } finally {
      setSaving(false);
    }
  };

  const handleDropOnDay = useCallback(async (targetDay: Date, eventId: string) => {
    setDragOverDay("");
    const event = normalizedEvents.find((e) => e.id === eventId);
    if (!event) return;

    const targetKey = dateKey(targetDay);
    if (event.startDayKey === targetKey) return;

    const durationMs = event.endDateTime.getTime() - event.startDateTime.getTime();
    const newStart = startOfDay(targetDay);
    const newEnd = new Date(newStart.getTime() + durationMs);

    const newStartKey = dateKey(newStart);
    const newEndKey = dateKey(newEnd);

    try {
      await TechModulAPI.patchCalendarEvent(eventId, {
        start_at: newStartKey,
        end_at: newEndKey,
        date: newStartKey,
        date_end: newEndKey,
        date_from: newStartKey,
        date_to: newEndKey,
      } as any);
      await loadEvents();
    } catch (err: any) {
      setError(err?.message || "Nie udalo sie przeniesc zdarzenia");
    }
  }, [normalizedEvents, loadEvents]);

  const monthGridDays = useMemo(() => {
    const firstOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
    const firstVisible = startOfWeek(firstOfMonth);
    return Array.from({ length: 42 }, (_, index) => addDays(firstVisible, index));
  }, [currentDate]);

  const renderMonthView = () => (
    <div className="grid grid-cols-7 gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10">
      {WEEKDAY_LABELS.map((label) => (
        <div key={label} className="bg-[#17181d] px-3 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
          {label}
        </div>
      ))}
      {monthGridDays.map((day) => {
        const dayEvents = filteredEvents.filter((event) => eventOccursOnDay(event, day));
        const inCurrentMonth = day.getMonth() === currentDate.getMonth();
        const isToday = sameDay(day, new Date());
        const dk = dateKey(day);
        const isDragOver = dragOverDay === dk;
        return (
          <div
            key={`${view}-${dk}`}
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOverDay(dk); }}
            onDragLeave={() => setDragOverDay((prev) => prev === dk ? "" : prev)}
            onDrop={(e) => { e.preventDefault(); const id = e.dataTransfer.getData("text/plain"); if (id) void handleDropOnDay(day, id); }}
            className={[
              "min-h-[152px] bg-[#101116] p-2 text-left transition-colors",
              inCurrentMonth ? "" : "text-slate-600",
              isDragOver ? "ring-2 ring-inset ring-brand/60 bg-brand/10" : "",
            ].join(" ")}
          >
            <div className="mb-2 flex items-center justify-between">
              <span
                className={[
                  "inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold",
                  isToday ? "bg-brand text-white" : "text-slate-300",
                ].join(" ")}
              >
                {day.getDate()}
              </span>
              <button
                type="button"
                onClick={() => openCreatePanel(day)}
                className="rounded-full border border-white/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-slate-500 hover:bg-white/10"
              >
                + add
              </button>
            </div>
            <div className="space-y-1.5">
              {dayEvents.slice(0, 3).map((event) => (
                <EventChip key={event.id} event={event} active={event.id === selectedEventId} onClick={() => openEditPanel(event)} />
              ))}
              {dayEvents.length > 3 && (
                <div className="rounded-xl border border-dashed border-white/10 px-3 py-2 text-xs text-slate-400">
                  +{dayEvents.length - 3} more
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );

  const renderWeekView = () => {
    const days = Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
    return (
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-7">
        {days.map((day) => {
          const dayEvents = filteredEvents.filter((event) => eventOccursOnDay(event, day));
          const dk = dateKey(day);
          const isDragOver = dragOverDay === dk;
          return (
            <Card
              key={dk}
              className={["bg-[#101116]/95 p-0 transition-colors", isDragOver ? "ring-2 ring-brand/60" : ""].join(" ")}
              onDragOver={(e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOverDay(dk); }}
              onDragLeave={() => setDragOverDay((prev) => prev === dk ? "" : prev)}
              onDrop={(e: React.DragEvent) => { e.preventDefault(); const id = e.dataTransfer.getData("text/plain"); if (id) void handleDropOnDay(day, id); }}
            >
              <button
                type="button"
                onClick={() => openCreatePanel(day)}
                className="w-full border-b border-white/10 px-4 py-4 text-left hover:bg-white/5"
              >
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{formatShortDay(day)}</div>
                <div className="mt-1 text-lg font-semibold text-white">{day.getDate()}</div>
              </button>
              <div className="space-y-2 p-3">
                {dayEvents.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-white/10 px-3 py-6 text-center text-sm text-slate-500">
                    Brak zdarzen
                  </div>
                ) : (
                  dayEvents.map((event) => (
                    <EventChip key={event.id} event={event} active={event.id === selectedEventId} onClick={() => openEditPanel(event)} />
                  ))
                )}
              </div>
            </Card>
          );
        })}
      </div>
    );
  };

  const renderDayView = () => {
    const dayEvents = filteredEvents.filter((event) => eventOccursOnDay(event, currentDate));
    return (
      <Card className="bg-[#101116]/95">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Day view</div>
            <h3 className="mt-1 text-xl font-semibold text-white">{formatLongDate(currentDate)}</h3>
          </div>
          <Button variant="secondary" onClick={() => openCreatePanel(currentDate)}>
            <Plus className="h-4 w-4" />
            Add event
          </Button>
        </div>
        <div className="mt-5 space-y-3">
          {dayEvents.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 px-4 py-12 text-center text-slate-500">
              Brak zdarzen na ten dzien.
            </div>
          ) : (
            dayEvents.map((event) => (
              <div key={event.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${typeMeta(event.normalizedType).pillClass}`}>
                        {typeMeta(event.normalizedType).label}
                      </span>
                      <span className="text-xs text-slate-400">{event.statusLabel}</span>
                    </div>
                    <h4 className="mt-2 text-lg font-semibold text-white">{event.title}</h4>
                    <div className="mt-2 flex flex-wrap gap-4 text-sm text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <Clock3 className="h-4 w-4" />
                        {event.all_day ? "All day" : `${formatTime(event.startDateTime)} - ${formatTime(event.endDateTime)}`}
                      </span>
                      {event.location && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="h-4 w-4" />
                          {event.location}
                        </span>
                      )}
                      {event.assignedLabel && (
                        <span className="inline-flex items-center gap-1">
                          <User className="h-4 w-4" />
                          {event.assignedLabel}
                        </span>
                      )}
                    </div>
                  </div>
                  <Button variant="secondary" onClick={() => openEditPanel(event)}>
                    Open details
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    );
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-[1700px] space-y-3 px-4 pb-20 pt-4">
        {/* Compact header: title + stats + nav + filters in one dense bar */}
        <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-[#101116]/95 px-5 py-3">
          {/* Row 1: Title, stats pills, view switcher, actions */}
          <div className="flex flex-wrap items-center gap-4">
            <h1 className="text-lg font-bold text-white tracking-tight">Kalendarz</h1>

            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span>Dzis: <strong className="text-white">{eventsTodayCount}</strong></span>
              <span className="text-white/20">|</span>
              <span>Tydzien: <strong className="text-white">{eventsThisWeekCount}</strong></span>
              <span className="text-white/20">|</span>
              <span>Pracownicy: <strong className="text-white">{workerOptions.length}</strong></span>
              <span className="text-white/20">|</span>
              <span>Zaladowano: <strong className="text-white">{filteredEvents.length}</strong></span>
            </div>

            <div className="ml-auto flex items-center gap-2">
              <div className="inline-flex items-center rounded-xl border border-white/10 bg-[#0c0d11] p-0.5">
                <button type="button" onClick={() => changeDateWindow(-1)} className="rounded-lg px-2 py-1.5 text-slate-300 hover:bg-white/10">
                  <ChevronLeft className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentDate(new Date())}
                  className="rounded-lg px-2 py-1.5 text-[11px] font-semibold uppercase tracking-[0.15em] text-slate-300 hover:bg-white/10"
                >
                  Dzis
                </button>
                <button type="button" onClick={() => changeDateWindow(1)} className="rounded-lg px-2 py-1.5 text-slate-300 hover:bg-white/10">
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>

              <span className="text-sm font-semibold text-white">
                {view === "month" ? formatMonthTitle(currentDate) : view === "week" ? `${dateKey(weekStart)} – ${dateKey(weekEnd)}` : formatLongDate(currentDate)}
              </span>

              <div className="inline-flex items-center rounded-xl border border-white/10 bg-[#0c0d11] p-0.5">
                {(["month", "week", "day"] as CalendarView[]).map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setView(option)}
                    className={[
                      "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                      view === option
                        ? "bg-brand text-white"
                        : "text-slate-400 hover:bg-white/10 hover:text-white",
                    ].join(" ")}
                  >
                    {option}
                  </button>
                ))}
              </div>

              <Button variant="secondary" className="h-8 px-3 text-xs" onClick={() => openCreatePanel(new Date())}>
                <Plus className="h-3.5 w-3.5" />
                Nowe
              </Button>
              <button type="button" onClick={() => void loadEvents()} disabled={loading} className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white">
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>

          {/* Row 2: Filters inline */}
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-slate-500" />
            <select
              value={filters.type}
              onChange={(event) => setFilters((current) => ({ ...current, type: event.target.value }))}
              className="rounded-lg border border-white/10 bg-[#0c0d11] px-2.5 py-1.5 text-xs text-white outline-none"
            >
              <option value="all">Typ: wszystkie</option>
              {EVENT_TYPES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
            <select
              value={filters.worker}
              onChange={(event) => setFilters((current) => ({ ...current, worker: event.target.value }))}
              className="rounded-lg border border-white/10 bg-[#0c0d11] px-2.5 py-1.5 text-xs text-white outline-none"
            >
              <option value="all">Pracownik: wszyscy</option>
              {workerOptions.map((worker) => (
                <option key={worker} value={worker}>
                  {worker}
                </option>
              ))}
            </select>
            <select
              value={filters.status}
              onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
              className="rounded-lg border border-white/10 bg-[#0c0d11] px-2.5 py-1.5 text-xs text-white outline-none"
            >
              <option value="all">Status: wszystkie</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status.id} value={status.id}>
                  {status.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="rounded-lg px-2 py-1.5 text-[11px] text-slate-500 hover:bg-white/10 hover:text-white"
              onClick={() => setFilters({ type: "all", worker: "all", status: "all" })}
            >
              Reset
            </button>
            <div className="ml-2 flex flex-wrap gap-1.5">
              {EVENT_TYPES.map((item) => (
                <span key={item.id} className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${item.chipClass}`}>
                  {item.label}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-3">

            {loading ? (
              <Card className="bg-[#101116]/95">
                <div className="flex min-h-[320px] items-center justify-center gap-3 text-slate-400">
                  <RefreshCw className="h-5 w-5 animate-spin" />
                  Loading calendar...
                </div>
              </Card>
            ) : view === "month" ? (
              renderMonthView()
            ) : view === "week" ? (
              renderWeekView()
            ) : (
              renderDayView()
            )}
          </div>

          <Card className="sticky top-4 h-fit bg-[#101116]/95">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Details</div>
                <h3 className="mt-1 text-xl font-semibold text-white">
                  {panelMode === "create" ? "New event" : panelMode === "edit" ? "Edit event" : "Calendar inspector"}
                </h3>
              </div>
              {panelMode !== "empty" && (
                <Button variant="ghost" onClick={closePanel}>
                  Close
                </Button>
              )}
            </div>

            {panelMode === "empty" ? (
              <div className="mt-6 space-y-4 text-sm text-slate-400">
                <div className="rounded-2xl border border-dashed border-white/10 p-4">
                  Click a day to create an event or click an existing event block to open details and edit it.
                </div>
                <div className="space-y-3">
                  <button
                    type="button"
                    onClick={() => openCreatePanel(new Date())}
                    className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-left hover:bg-white/[0.06]"
                  >
                    <span className="inline-flex items-center gap-2 text-white">
                      <CalendarClock className="h-4 w-4 text-brand" />
                      Create event for today
                    </span>
                    <Plus className="h-4 w-4 text-slate-400" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-5 space-y-4">
                {selectedEvent && panelMode === "edit" && (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${typeMeta(selectedEvent.normalizedType).pillClass}`}>
                        {typeMeta(selectedEvent.normalizedType).label}
                      </span>
                      <span className="text-xs text-slate-400">{selectedEvent.statusLabel}</span>
                    </div>
                    <div className="mt-3 text-sm text-slate-300">
                      <div>{selectedEvent.title}</div>
                      <div className="mt-2 text-slate-500">{selectedEvent.all_day ? "All day" : `${formatTime(selectedEvent.startDateTime)} - ${formatTime(selectedEvent.endDateTime)}`}</div>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Title</label>
                  <input
                    value={form.title}
                    onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                    className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                    placeholder="Measurement at client site"
                  />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Type</label>
                    <select
                      value={form.type}
                      onChange={(event) => setForm((current) => ({ ...current, type: event.target.value as EventTypeId }))}
                      className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                    >
                      {EVENT_TYPES.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Status</label>
                    <select
                      value={form.status}
                      onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                      className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                    >
                      {STATUS_OPTIONS.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <label className="flex items-center gap-3 rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-3 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={form.allDay}
                    onChange={(event) => setForm((current) => ({ ...current, allDay: event.target.checked }))}
                    className="h-4 w-4 rounded border-white/20 bg-[#0c0d11]"
                  />
                  All day event
                </label>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Start date</label>
                    <input
                      type="date"
                      value={form.startDate}
                      onChange={(event) => setForm((current) => ({ ...current, startDate: event.target.value }))}
                      className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.2em] text-slate-500">End date</label>
                    <input
                      type="date"
                      value={form.endDate}
                      onChange={(event) => setForm((current) => ({ ...current, endDate: event.target.value }))}
                      className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                    />
                  </div>
                </div>

                {!form.allDay && (
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Start time</label>
                      <input
                        type="time"
                        value={form.startTime}
                        onChange={(event) => setForm((current) => ({ ...current, startTime: event.target.value }))}
                        className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs uppercase tracking-[0.2em] text-slate-500">End time</label>
                      <input
                        type="time"
                        value={form.endTime}
                        onChange={(event) => setForm((current) => ({ ...current, endTime: event.target.value }))}
                        className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Client name</label>
                  <input
                    value={form.clientName}
                    onChange={(event) => setForm((current) => ({ ...current, clientName: event.target.value }))}
                    className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Order / project reference</label>
                  <input
                    value={form.projectRef}
                    onChange={(event) => setForm((current) => ({ ...current, projectRef: event.target.value }))}
                    className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Location</label>
                  <input
                    value={form.location}
                    onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))}
                    className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Assigned worker / team</label>
                  <input
                    value={form.assignedTo}
                    onChange={(event) => setForm((current) => ({ ...current, assignedTo: event.target.value }))}
                    className="w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.2em] text-slate-500">Notes</label>
                  <textarea
                    value={form.notes}
                    onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                    className="min-h-[120px] w-full rounded-xl border border-white/10 bg-[#0c0d11] px-3 py-2 text-white outline-none"
                  />
                </div>

                {error && <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</div>}

                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
                  {panelMode === "edit" ? (
                    <Button variant="danger" onClick={handleDelete} disabled={saving}>
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </Button>
                  ) : (
                    <div />
                  )}
                  <div className="flex gap-2">
                    <Button variant="ghost" onClick={closePanel} disabled={saving}>
                      Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={saving}>
                      {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}
                      Save event
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
