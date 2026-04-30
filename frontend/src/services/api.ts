const rawApiBase = (process.env.NEXT_PUBLIC_API_URL ?? "").trim();
const normalizedApiBase = rawApiBase.replace(/\s+/g, "").replace(/\/+$/, "");
const browserHost = typeof window !== "undefined" ? window.location.hostname : "";
const browserProtocol = typeof window !== "undefined" ? window.location.protocol : "http:";
const isLocalBrowser = browserHost === "localhost" || browserHost === "127.0.0.1";
const browserApiBase = browserHost ? `${browserProtocol}//${browserHost}:8000` : "";
export const API_BASE_URL = isLocalBrowser
  ? "http://localhost:8000"
  : (normalizedApiBase || browserApiBase || "http://localhost:8000");

export type AgentChange = {
  id: number;
  name: string;
  param: "width" | "height" | "depth" | string;
  old: number;
  new: number;
};

export type AgentPreview = {
  type: "preview";
  action: string;
  changes: AgentChange[];
};

export type ProjectModule = {
  id: number;
  name: string;
  width: number;
  height: number;
  depth: number;
  material_id?: number;
  material_name?: string;
  materials?: Record<string, string>;
  edgebands?: Record<string, string>;
  materials_finish?: Record<string, any>;
  carcass_top_mode?: string;
  carcass_bottom_mode?: string;
  top_rail_offset_mm?: number;
  bottom_rail_offset_mm?: number;
  back_mounting_mode?: string;
  shelf_count?: number;
  show_interior?: boolean;
  divider_count?: number;
  drawer_count?: number;
  facade_mode?: string;
  hinge_vendor?: string;
  drawer_vendor?: string;
  parts?: Record<string, any>;
  carcass_joint_type?: string;
  carcass_joint_type_bottom?: string;
  leg_type?: string;
  legs_height_mm?: number;
  leg_offset_front?: number;
  leg_offset_side?: number;
  leg_offset_back?: number;
  gap_top?: number;
  gap_bottom?: number;
  gap_left?: number;
  gap_right?: number;
  handle_type?: string;
  handle_length?: number;
  handle_orientation?: 'horizontal' | 'vertical';
  handle_pos_x?: 'left' | 'center' | 'right';
  handle_pos_y?: 'top' | 'middle' | 'bottom';
  handle_offset_edge?: number;
  x?: number;
  y?: number;
  z?: number;
  code?: string;
  plinth_inset_side_mm?: number;
  plinth_height_mm?: number;
  plinth_inset_mm?: number;
  cabinet_type?: 'base' | 'wall' | 'tall' | 'corner_base' | 'corner_wall';
  description?: string;
  notes?: string;
  front_gap_top?: number;
  front_gap_bottom?: number;
  front_gap_left?: number;
  front_gap_right?: number;
  drawer_guide_type?: string;
  quantity?: number;
  has_plinth?: boolean;
  visible_in_projection?: boolean;
  lock_dimensions?: boolean;
};

export type Obstacle = {
  id: string;
  type: 'window' | 'door' | 'column' | 'pipe' | 'shaft' | 'utility' | 'socket';
  x: number;
  y: number;
  width: number;
  height: number;
  depth?: number;
};

export type WallConfig = {
  id: number;
  wall_name?: string;
  points_count?: number;
  width: number;
  height: number;
  room_depth?: number;
  left_angle?: number;
  right_angle?: number;
};

export interface ImportResult {
  summary: {
    name: string;
    module: string;
    area_m2: number;
    edge_mb: number;
    parts_count: number;
    file_path: string;
    max_w?: number;
    max_h?: number;
    max_l?: number;
  };
  rows: Array<{
    section: string;
    code: string;
    name: string;
    qty: number;
    length_mm: number;
    width_mm: number;
    thickness_mm: number;
    material_original: string;
    status: string;
    source_id: string;
    cnc_data?: string;
    edges?: Record<string, string | null>;
    technology_summary?: ImportedTechnologySummary;
  }>;
  modules?: ProjectModule[];
}

export type ImportedTechnologySummary = {
  part_name: string;
  part_type?: string;
  material_name?: string | null;
  length_mm: number;
  width_mm: number;
  thickness_mm: number;
  quantity: number;
  drill_count_total: number;
  drill_count_face: number;
  drill_count_edge: number;
  drill_diameters_mm: number[];
  drill_depths_mm: number[];
  drill_summary_text?: string | null;
  groove_count: number;
  groove_total_length_mm: number;
  groove_depths_mm: number[];
  groove_tool_widths_mm: number[];
  groove_summary_text?: string | null;
  milling_count: number;
  milling_total_path_length_mm?: number;
  milling_length_estimated_mm?: number;
  milling_tool_diameters_mm: number[];
  milling_depths_mm: number[];
  milling_arc_count: number;
  milling_line_count: number;
  milling_summary_text?: string | null;
  tool_names: string[];
  tool_diameters_mm: number[];
  tool_count_unique: number;
  tool_summary_text?: string | null;
  operation_count_total: number;
  operation_type_count: number;
  has_drilling: boolean;
  has_grooving: boolean;
  has_milling: boolean;
  cnc_complexity_score: number;
};

export type ServicePricingValidationFlag = {
  code: string;
  severity: "info" | "warning" | "error" | string;
  message: string;
};

export type ServicePricingBuckets = {
  material_cost: number;
  cnc_service_cost: number;
  finishing_cost: number;
  extra_cost: number;
  net_total: number;
};

export type ServicePricingResult = {
  schema_version: string;
  tariff_schema_version?: string;
  normalized_item: Record<string, unknown>;
  buckets: ServicePricingBuckets;
  pricing_status: "ready" | "manual_review" | string;
  validation_flags: ServicePricingValidationFlag[];
  manual_review_reasons: string[];
  summary_text: string;
};

export type ProjectRecord = {
  id: number;
  title: string;
  client_name?: string;
  status?: string;
};

export type OrderRecord = {
  id: number;
  project_id: number;
  client_name: string;
  title: string;
  deadline?: string;
  deadline_from?: string;
  deadline_to?: string;
  budget?: number;
  status: string;
  spec_json?: string;
  created_at?: string;
  order_name?: string;
};

export type OperationAction =
  | "module.set_depth"
  | "module.set_width"
  | "module.set_height"
  | "module.add_shelves"
  | "module.change_material"
  | "module.set_material"
  | "module.change_edgeband"
  | "module.apply_scheme"
  | "module.update_properties"
  | "wall.add_point"
  | "wall.remove_point";

export type OperationTarget = {
  id?: string;
  name?: string;
  scope?: string;
};

export type OperationRequest = {
  action: OperationAction;
  target: OperationTarget;
  params?: Record<string, unknown>;
  source?: string;
};

export type OperationChange = {
  path: string;
  label: string;
  before: unknown;
  after: unknown;
  unit?: string;
  kind?: string;
  target_ref?: { type: string; id: string; name: string };
};

export type OperationError = {
  code: string;
  message: string;
  path?: string;
};

export type OperationResult = {
  version: string;
  status: "ok" | "validation_error" | "conflict" | "error";
  mode: "preview" | "apply";
  action: string;
  target: { type: string; id: string; name: string; scope?: string };
  warnings: string[];
  errors: OperationError[];
  changes: OperationChange[];
  can_apply: boolean;
  meta: { source: string; requested_at: string };
};

export type BulkOperationError = {
  module_id: string;
  message: string;
};

export type BulkOperationResult = {
  status: "ok" | "validation_error";
  can_apply?: boolean;
  action?: string;
  warnings: string[];
  errors: BulkOperationError[];
  changes?: OperationChange[];
  applied_count?: number;
};

export type AssemblySummary = {
  project_id: number;
  modules_count: number;
  total_width_mm: number;
  total_height_mm: number;
  total_depth_mm: number;
  total_volume_l: number;
  avg_width_mm: number;
  avg_height_mm: number;
  avg_depth_mm: number;
};

export type WorkspaceSummary = {
  project_id: number;
  project_title: string;
  client_name: string;
  modules_count: number;
  orders_count: number;
  draft_orders_count: number;
  total_budget: number;
  latest_deadline: string;
};

export type FinanceSummary = {
  project_id: number;
  project_title: string;
  client_name: string;
  margin: number;
  base_cost: number;
  total_net: number;
  vat: number;
  total_gross: number;
  profit: number;
  orders_count: number;
};

export type UnifiedSummaryPricing = {
  material_value: number;
  services_total: number;
  extras_total: number;
  base_total: number;
  sale_total: number;
  brutto_total: number;
  profit_total: number;
  technical_total: number;
  vat: number;
  margin_percent: number;
};

export type UnifiedSummaryScope = {
  modules_count: number;
  orders_count: number;
  draft_orders_count: number;
  materials_used: number;
};

export type UnifiedSummaryAudit = {
  built_from: string[];
  adapter_name: string;
  built_at: string;
  notes: string;
};

export type UnifiedSummaryData = {
  project_id: number;
  project_title: string;
  client_name: string;
  pricing: UnifiedSummaryPricing;
  scope: UnifiedSummaryScope;
  audit: UnifiedSummaryAudit;
  computed_at: string;
};

export type WallPoint = {
  id: string;
  type: "bolt" | "droplet" | "flame" | string;
  x: number;
  y: number;
};

export type WallPointsResponse = {
  name: string;
  points: WallPoint[];
};

export type MaterialRecord = {
  id: number;
  name: string;
  price: number;
  thickness: number;
  material_code?: string;
  category: "boards" | "hardware" | "finishes" | string;
  material_kind?: string;
  unit: string;
  is_library: boolean;
  stock_quantity: number;
  min_stock?: number;
  is_low_stock?: boolean;
  purchase_type: "invoice" | "cash" | "nothing";
  supplier?: string;
  wholesaler?: string;
  format_length_mm?: number;
  format_width_mm?: number;
  pack_size?: number;
  parameter_json?: string;
  texture_url?: string;
  color_hex?: string;
};

export type ArrivalRecord = {
  id: number;
  material_id: number;
  order_id?: number | null;
  invoice_id?: number | null;
  invoice_line_item_id?: number | null;
  order_title?: string;
  material_name?: string;
  quantity: number;
  unit: string;
  purchase_type: string;
  document_nr: string;
  supplier?: string;
  wholesaler?: string;
  unit_price_net?: number;
  unit_price_gross?: number;
  price_total: number;
  date: string;
};

export type LowStockItem = {
  id: number;
  name: string;
  category: string;
  material_kind: string;
  unit: string;
  stock_quantity: number;
  min_stock: number;
  missing_qty: number;
  supplier?: string;
  wholesaler?: string;
};

export type DatabaseOverview = {
  materials_count: number;
  clients_count: number;
  projects_count: number;
  modules_count: number;
  orders_count: number;
};

export type SystemSummary = {
  status: string;
  api_version: string;
  engine: string;
  db: DatabaseOverview;
};

export type DashboardConfidence = "READY" | "PARTIAL" | string;

export type DashboardV1OperationalSummary = {
  confidence: DashboardConfidence;
  source_route: string;
  active_projects_count: number;
  orders_by_state: Record<string, number>;
  mvp_readiness_distribution: {
    ready: number;
    risk: number;
    critical: number;
    total_projects: number;
    avg_readiness_score: number;
  };
};

export type DashboardV1TopBlocker = {
  reason: string;
  count: number;
};

export type DashboardV1PricingQuality = {
  confidence: DashboardConfidence;
  source_route: string;
  total_service_items: number;
  ready_items_count: number;
  manual_review_items_count: number;
  missing_mandatory_inputs_count: number;
  top_blockers: DashboardV1TopBlocker[];
};

export type DashboardV1WorkstationTaskLoad = {
  task_type: string;
  count: number;
};

export type DashboardV1ProductionRisk = {
  confidence: DashboardConfidence;
  source_route: string;
  overdue_issues_count: number;
  critical_issues_count: number;
  routes_active_count: number;
  routes_overdue_count: number;
  workstation_task_load: DashboardV1WorkstationTaskLoad[];
  recommended_route_actions_count: number;
};

export type DashboardV1KioskLaborActivity = {
  confidence: DashboardConfidence;
  source_route: string;
  active_kiosk_sessions_count: number;
  sessions_missing_linkage_count: number;
  logged_hours_total_period: number;
  logged_hours_period_days: number;
  logged_hours_quality: DashboardConfidence;
};

export type DashboardV1LowStockItem = {
  id: number;
  name: string;
  missing_qty: number;
  stock_quantity: number;
  min_stock: number;
  unit: string;
};

export type DashboardV1MaterialsProcurement = {
  confidence: DashboardConfidence;
  source_route: string;
  low_stock_materials_count: number;
  top_critical_low_stock: DashboardV1LowStockItem[];
  arrivals_recent_count: number;
  arrivals_period_days: number;
};

export type DashboardV1InvoiceProcessingControl = {
  confidence: DashboardConfidence;
  source_route: string;
  imported_invoices_count: number;
  unresolved_invoice_lines_count: number;
  confirmed_invoices_count: number;
  partial_invoices_count: number;
  low_confidence_line_count: number;
  duplicates_prevented_count: number;
  price_history_writes_count: number;
};

export type DashboardV1Response = {
  generated_at: string;
  period_days: number;
  operational_summary: DashboardV1OperationalSummary;
  pricing_quality: DashboardV1PricingQuality;
  production_risk: DashboardV1ProductionRisk;
  kiosk_labor_activity: DashboardV1KioskLaborActivity;
  materials_procurement: DashboardV1MaterialsProcurement;
  invoice_processing_control: DashboardV1InvoiceProcessingControl;
};

export type GlobalSystemSummary = {
  finance: {
    total_sales_net: number;
    total_costs_net: number;
    gross_profit: number;
    cash_in_hand: number;
  };
  tax: {
    sales_net: number;
    vat_collected: number;
    costs_net: number;
    vat_paid: number;
    costs_gross: number;
    tax_balance: number;
    recommendation: string;
  };
  hr: {
    total_hours: number;
    estimated_payroll_net: number;
    active_workers: number;
    average_hour_cost?: number | null;
    direct_hour_cost?: number | null;
    workers_total?: number;
    workers_with_rate?: number;
    workers_missing_rate?: number;
    payroll_confidence?: "READY" | "PARTIAL" | string;
  };
  inventory: {
    total_value: number;
    materials_types: number;
  };
  cost_insights?: {
    employee_hour_cost?: number | null;
    production_hour_cost?: number | null;
    service_hour_cost?: number | null;
    lacquer_hour_cost?: number | null;
    direct_employee_hour_cost?: number | null;
    direct_production_hour_cost?: number | null;
    direct_service_hour_cost?: number | null;
    direct_lacquer_hour_cost?: number | null;
    fixed_overhead_monthly?: number;
    variable_overhead_monthly?: number;
    overhead_hour_cost?: number;
    confidence?: "READY" | "PARTIAL" | string;
    notes?: string[];
  };
  production: {
    total_modules: number;
    total_orders: number;
    active_projects: number;
  };
  timestamp: string;
};

export type CompanyExpenseItem = {
  expense_id?: string;
  name: string;
  amount: number;
  account_type?: string;
  source_type?: string;
};

export type FixedCompanyExpensesResponse = {
  fixed: CompanyExpenseItem[];
  variable_total: number;
  workers_count: number;
  hours_per_worker: number;
  metrics: {
    fixed_total: number;
    variable_total: number;
    total_costs: number;
    total_hours: number;
    real_hour_rate: number;
  };
};

export type ProductionStatus = {
  workstations: Array<{
    id: string;
    name: string;
    position: string;
    status: "IDLE" | "BUSY" | "READY";
    workers: string[];
    progress: number;
    active_job: { title: string } | null;
  }>;
  stats: {
    active_orders: number;
    online_workers: number;
    pending_tasks: number;
    finished_today: number;
    critical_issues: number;
  };
  activity_log: Array<{
    time: string;
    worker: string;
    action: string;
    order: string;
  }>;
};

export type ProductionTask = {
  id: string;
  created_at?: string;
  updated_at?: string;
  issue_id?: string;
  task_type: string;
  project_name: string;
  client_name: string;
  city?: string;
  address?: string;
  planned_date?: string;
  crew?: string;
  status: string;
  estimated_time_minutes?: number;
  notes?: string;
  blocked_reason?: string;
  handoff_status?: string;
  quality_result?: string;
  rework_reason?: string;
  rejected_by?: string;
  accepted_by?: string;
  is_ready?: boolean;
  prerequisite_blocked?: boolean;
  prerequisite_name?: string;
  prev_task_id?: string | null;
  prev_handoff_status?: string | null;
};

export interface StationJob extends ProductionTask {
  is_ready: boolean;
  prerequisite_blocked: boolean;
  prerequisite_name: string;
  prev_task_id: string | null;
  prev_handoff_status: string | null;
}

export type FulfillmentRecord = {
  project_name: string;
  status: string;
  packed_at: string;
  packed_by: string;
  dispatched_at: string;
  dispatched_by: string;
  delivered_at: string;
  delivered_by: string;
  delivery_note: string;
  package_count: number;
  carrier_name: string;
  tracking_number: string;
  installation_planned_date: string;
  installation_team: string;
  installation_progress: number;
  blocked_reason: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type FulfillmentQueueItem = {
  project_name: string;
  client_name: string;
  production_status: string;
  fulfillment: FulfillmentRecord;
};

export interface ProjectProductionReadiness {
  project_name: string;
  client_name: string;
  current_stage: string | null;
  next_stage: string | null;
  is_blocked: boolean;
  blocked_reason: string;
  stages: Record<string, string>;
  last_update: string | null;
  is_complete: boolean;
}

export type IssueCandidate = {
  issue: {
    id: string;
    title: string;
    description: string;
    issue_type: string;
    project_name: string;
    project_id?: string;
    created_at: string;
    status: string;
    priority_manual: "normalny" | "waLLny" | "krytyczny";
    estimated_cost?: number;
    estimated_revenue_unlock: number;
    estimated_time_minutes: number;
    quantity_required: number;
    quantity_bought: number;
  };
  score: number;
  impact: string;
};

export type AiTip = {
  type: "warning" | "opportunity" | "info";
  title: string;
  content: string;
  impact: string;
};

export type AiPrediction = {
  type: "delay" | "bottleneck" | "finance";
  severity: "high" | "medium" | "info";
  title: string;
  content: string;
  confidence: number;
};

export type WorkTimeEntry = {
  entry_id: string;
  day: number;
  date_iso: string;
  work_type: string;
  start_time: string;
  end_time: string;
  hours: number;
  overtime_hours: number;
  extra_pay: number;
  project_code: string;
  note: string;
};

export type WorkerMonthSheet = {
  sheet_id: string;
  worker_name: string;
  year: number;
  month: number;
  entries: WorkTimeEntry[];
};

export type KioskResult = {
  ok: boolean;
  message: string;
  worker: any | null;
  session: any | null;
  entry: WorkTimeEntry | null;
};

export type WallSummary = {
  project_id: number;
  wall_name: string;
  points_count: number;
};

export type CalendarEventRecord = {
  id: string;
  title: string;
  date: string;
  date_end?: string;
  date_from?: string;
  date_to?: string;
  start_at?: string;
  end_at?: string;
  all_day: boolean;
  event_type?: string;
  type?: "measurement" | "installation" | "meeting" | "transport" | "production" | "service" | "other" | string;
  station?: string;
  order_code?: string;
  project_ref?: string;
  worker_name?: string;
  assigned_to?: string;
  client_name?: string;
  location?: string;
  notes?: string;
  status?: string;
  color?: string;
  created_at?: string;
};

export type CalendarEventPayload = {
  title: string;
  type?: "measurement" | "installation" | "meeting" | "transport" | "production" | "service" | "other" | string;
  event_type?: string;
  start_at?: string;
  end_at?: string;
  date?: string;
  date_end?: string;
  all_day?: boolean;
  station?: string;
  worker_name?: string;
  assigned_to?: string;
  order_code?: string;
  project_ref?: string;
  client_name?: string;
  location?: string;
  notes?: string;
  status?: string;
};

export type CalendarWorkItem = {
  id: string;
  source: "order_calendar" | "production_route" | "operations_issue" | string;
  kind: "order_event" | "production_task" | "issue" | string;
  title: string;
  subtitle?: string;
  date_from?: string;
  date_to?: string;
  status_key: "planned" | "in_progress" | "done" | "blocked" | "unknown" | string;
  status_label: string;
  color_key: "blue" | "amber" | "emerald" | "red" | "slate" | string;
  assignees: string[];
  order_id?: number | null;
  route_task_id?: string | null;
  issue_id?: string | null;
  is_overdue: boolean;
  source_route: string;
  confidence: "READY" | "PARTIAL" | string;
};

export type CalendarWorkboardResponse = {
  status: "ok" | string;
  generated_at: string;
  window: {
    start: string;
    end: string;
  };
  summary: {
    total_items: number;
    overdue_count: number;
  };
  items: CalendarWorkItem[];
};

export type AlarmRecord = {
  alarm_id: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  related_order?: string;
  related_client?: string;
  related_worker?: string;
  related_material?: string;
  created_at?: string;
  due_date?: string;
  is_resolved: boolean;
  resolved_at?: string;
  extra?: Record<string, unknown>;
};

export type OperationsIssueRecord = {
  id: string;
  title: string;
  description: string;
  status: string;
  priority_manual: string;
  owner: string;
  project_name: string;
  client_name: string;
  issue_type: string;
  due_date?: string;
  estimated_revenue_unlock?: number;
  blocks_invoice?: boolean;
  updated_at?: string;
  notes?: string;
};

export type OperationsSummary = {
  issues_total: number;
  issues_active: number;
  issues_overdue: number;
  issues_critical: number;
  issues_blocks_invoice: number;
  routes_total: number;
  routes_active: number;
  routes_overdue: number;
  routes_done: number;
  revenue_unlock_total: number;
};

export type RouteRecommendation = {
  issue_id: string;
  title: string;
  project_name: string;
  client_name: string;
  city?: string;
  address?: string;
  owner?: string;
  score: number;
  quick_close: boolean;
  overdue: boolean;
  estimated_time_minutes: number;
  estimated_revenue_unlock: number;
  recommended_planned_date: string;
  recommended_crew: string;
};

export type MvpReadiness = {
  project_id: number;
  ready: boolean;
  checks: {
    has_modules: boolean;
    has_orders: boolean;
    has_wall_points: boolean;
    has_materials: boolean;
    has_clients: boolean;
  };
  missing: string[];
  missing_labels: string[];
  missing_details: Array<{
    check: string;
    label: string;
    priority: number;
  }>;
  counts: {
    modules: number;
    orders: number;
    wall_points: number;
    materials: number;
    clients: number;
  };
  score: {
    passed_checks: number;
    total_checks: number;
    percent: number;
  };
  next_actions: Array<{
    for_check: string;
    code: string;
    label: string;
    priority: number;
    route: string;
  }>;
  next_action: {
    for_check: string;
    code: string;
    label: string;
    priority: number;
    route: string;
  } | null;
};

export type ProjectsMvpReadinessSummary = {
  total_projects: number;
  ready_projects: number;
  not_ready_projects: number;
  avg_readiness_score: number;
  readiness_bands: {
    critical: number;
    risk: number;
    ready: number;
  };
  generated_at: string;
  blocking_reasons: Record<string, number>;
  blocking_reasons_details: Array<{
    check: string;
    label: string;
    priority: number;
    count: number;
  }>;
  action_queue: Array<{
    code: string;
    label: string;
    priority: number;
    route: string;
    affected_projects: number;
  }>;
  next_global_action: {
    code: string;
    label: string;
    priority: number;
    route: string;
    affected_projects: number;
  } | null;
  projects: Array<{
    project_id: number;
    project_title: string;
    ready: boolean;
    readiness_score: number;
    missing_count: number;
    missing: string[];
    missing_labels: string[];
    missing_details: Array<{
      check: string;
      label: string;
      priority: number;
    }>;
    next_actions: Array<{
      for_check: string;
      code: string;
      label: string;
      priority: number;
      route: string;
    }>;
    next_action: {
      for_check: string;
      code: string;
      label: string;
      priority: number;
      route: string;
    } | null;
  }>;
};

export type ClientRecord = {
  id: number;
  name: string;
  location: string;
  address?: string;
  email?: string;
  phone?: string;
  type: "person" | "b2b";
  status: "active" | "vip" | "archived";
  created_at?: string;
};

export interface SelectedUser {
  id: number;
  name: string;
  role: string;
  avatar_color: string;
  initials: string;
}

async function readJsonError(res: Response, fallback: string): Promise<never> {
  const err = await res.json().catch(() => ({}));
  if (typeof err?.detail === "string") throw new Error(err.detail);
  const detail = err?.detail;
  if (detail?.errors?.[0]?.message) throw new Error(detail.errors[0].message);
  throw new Error(fallback);
}

async function postJson<T>(path: string, body: unknown, fallbackError: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) await readJsonError(res, fallbackError);
  return res.json();
}

async function patchJson<T>(path: string, body: unknown, fallbackError: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) await readJsonError(res, fallbackError);
  return res.json();
}

async function putJson<T>(path: string, body: unknown, fallbackError: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) await readJsonError(res, fallbackError);
  return res.json();
}

async function getJson<T>(path: string, fallbackError: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    credentials: "include"
  });
  if (!res.ok) await readJsonError(res, fallbackError);
  return res.json();
}

async function deleteJson<T>(path: string, fallbackError: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    credentials: "include"
  });
  if (!res.ok) await readJsonError(res, fallbackError);
  return res.json();
}

export interface AuditEntry {
  id: number;
  timestamp: string;
  user_name: string;
  action: string;
  target_type?: string;
  target_id?: string;
  details?: string;
  metadata_json?: string;
}

export interface RouteTaskRecord {
  id: string;
  created_at: string;
  updated_at: string;
  issue_id: string;
  task_type: string;
  project_name: string;
  client_name: string;
  city: string;
  address: string;
  planned_date: string;
  crew: string;
  status: string;
  estimated_time_minutes: number;
  route_group: string;
  trip_order: number;
  route_score: number;
  blocks_payment: boolean;
  estimated_payment_unlock: number;
  finance_followup_status: string;
  ready_to_invoice: boolean;
  requires_settlement: boolean;
  requires_confirmation: boolean;
  finance_followup_note: string;
  notes: string;
}

export interface DashboardV2Response {
  generated_at: string;
  summary: {
    active_orders_count: number;
    critical_alarms_count: number;
    blocked_production_count: number;
    low_stock_count: number;
    cost_overrun_count: number;
    cnc_active_count: number;
    cnc_problem_count: number;
  };
  production: {
    cnc_summary: {
      waiting: number;
      active: number;
      problem: number;
      done_today: number;
    };
    top_issues: any[];
  };
  costs: {
    top_overruns: Array<{
      id: string | number;
      title: string;
      real: number;
      est: number;
      variance: number;
    }>;
  };
  inventory: {
    top_low_stock: any[];
    recent_scrap_count: number;
    recent_corrections_count: number;
  };
  recent_events: AuditEntry[];
}

export interface NotificationSummary {
  overdue_count: number;
  unassigned_high_prio_count: number;
  blocked_too_long_count: number;
  critical_alarms_count: number;
  total_urgent: number;
}

export interface NotificationItem {
  id: string;
  category: "OVERDUE" | "UNASSIGNED" | "BLOCKED_LONG" | "ALARM";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  title: string;
  details: string;
  source_id: string | number;
  source_type: string;
  timestamp: string;
  owner?: string;
  status?: string;
  priority?: string;
  escalation_reason?: string;
}

export interface ProcurementItem {
  material_id: number;
  name: string;
  code: string;
  unit: string;
  category: string;
  qty_on_hand: number;
  qty_reserved: number;
  qty_incoming: number;
  qty_available: number;
  min_stock: number;
  shortage: number;
  status: "OK" | "SHORTAGE" | "CRITICAL";
  demand_orders: Array<{
    order_id: number;
    order_title: string;
    client_name: string;
    qty: number;
  }>;
}

export interface ProcurementExecutionItem {
  id: number;
  material_id: number;
  material_name: string;
  material_unit: string;
  material_category: string;
  order_id: number | null;
  order_title: string | null;
  qty_target: number;
  qty_ordered: number;
  status: string;
  owner_name: string | null;
  supplier_name: string | null;
  due_date: string | null;
  priority: string;
  note: string | null;
  purchase_document_id: number | null;
  purchase_doc_number: string | null;
  created_at: string;
}

export interface OrderReadiness {
  order_id: number;
  order_title: string;
  client_name: string;
  readiness: "READY" | "PARTIAL" | "BLOCKED";
  ready_count: number;
  partial_count: number;
  blocked_count: number;
  total_count: number;
  materials: Array<{
    material_id: number;
    name: string;
    reserved_qty: number;
    unit: string;
    status: "READY" | "PARTIAL" | "BLOCKED";
  }>;
}

export interface KriResponse {
  generated_at: string;
  risks: Array<{
    severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    category: "DEADLINE" | "FLOW" | "MATERIAL" | "COST" | "PROCESS";
    title: string;
    details: string;
    source_id?: string | number;
    source_type?: string;
    timestamp?: string;
    actor?: string;
    status?: string;
    owner?: string;
    priority?: string;
    due_date?: string;
  }>;
}

export const TechModulAPI = {
  async login(name: string, pin: string): Promise<SelectedUser> {
    const res = await postJson<{ user: SelectedUser }>("/api/auth/login", { name, pin }, "Błąd logowania");
    return res.user;
  },

  async logout(): Promise<void> {
    await postJson<{ status: string }>("/api/auth/logout", {}, "Błąd wylogowania");
  },

  async getMe(): Promise<SelectedUser> {
    return await getJson<SelectedUser>("/api/auth/me", "Błąd weryfikacji sesji");
  },

  async getAdminUsers(): Promise<{ id: number; name: string; role: string; is_active: number; avatar_color: string; last_active: string }[]> {
    const res = await getJson<{ users: any[] }>("/api/admin/users", "Błąd pobierania użytkowników");
    return res.users;
  },

  async createAdminUser(payload: { name: string; role: string; password: string }): Promise<void> {
    await postJson("/api/admin/users", payload, "Błąd dodawania użytkownika");
  },

  async updateAdminUser(userId: number, payload: { role?: string; is_active?: number; password?: string }): Promise<void> {
    await patchJson(`/api/admin/users/${userId}`, payload, "Błąd aktualizacji użytkownika");
  },

  async getFixedCompanyExpenses(): Promise<FixedCompanyExpensesResponse> {
    const res = await fetch(`${API_BASE_URL}/finance/fixed-expenses`);
    if (!res.ok) throw new Error("Blad pobierania wydatkow stalych");
    return res.json();
  },

  async updateFixedCompanyExpenses(payload: {
    fixed: CompanyExpenseItem[];
    workers_count: number;
    hours_per_worker: number;
  }): Promise<FixedCompanyExpensesResponse> {
    const res = await fetch(`${API_BASE_URL}/finance/fixed-expenses`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Blad zapisu wydatkow stalych");
    return res.json();
  },

  async getGlobalFinanceSummary(): Promise<GlobalSystemSummary> {
    const res = await fetch(`${API_BASE_URL}/api/finance/system-summary`);
    if (!res.ok) throw new Error("Blad pobierania podsumowania finansAw");
    return res.json();
  },

  async getProjects(options?: { include_deleted?: boolean }): Promise<ProjectRecord[]> {
    const query = options?.include_deleted ? "?include_deleted=true" : "";
    const res = await fetch(`${API_BASE_URL}/projects${query}`);
    if (!res.ok) throw new Error("Blad pobierania projektow");
    return res.json();
  },

  async getNotificationSummary(): Promise<NotificationSummary> {
    return getJson<NotificationSummary>("/api/notifications/summary", "Blad pobierania powiadomien");
  },

  async getNotificationItems(): Promise<NotificationItem[]> {
    return getJson<NotificationItem[]>("/api/notifications/items", "Blad pobierania listy powiadomien");
  },

  async getProcurementAvailability(): Promise<ProcurementItem[]> {
    const res = await getJson<{ items: ProcurementItem[] }>("/api/procurement/availability", "Blad pobierania dostepnosci");
    return res.items;
  },

  async getPurchaseSuggestions(): Promise<ProcurementItem[]> {
    const res = await getJson<{ items: ProcurementItem[] }>("/api/procurement/suggestions", "Blad pobierania sugestii zakupowych");
    return res.items;
  },

  async getProcurementExecution(): Promise<ProcurementExecutionItem[]> {
    const res = await getJson<{ items: ProcurementExecutionItem[] }>("/api/procurement/execution", "Blad pobierania listy wykonania zakupow");
    return res.items;
  },

  async createProcurementExecution(payload: Partial<ProcurementExecutionItem>): Promise<{ id: number }> {
    return postJson<{ id: number }>("/api/procurement/execution", payload, "Blad tworzenia zadania zakupowego");
  },

  async updateProcurementExecution(itemId: number, payload: Partial<ProcurementExecutionItem>): Promise<void> {
    await patchJson(`/api/procurement/execution/${itemId}`, payload, "Blad aktualizacji zadania zakupowego");
  },

  async getOrderReadiness(): Promise<OrderReadiness[]> {
    const res = await getJson<{ orders: OrderReadiness[] }>("/api/procurement/readiness", "Blad pobierania gotowosci zamowien");
    return res.orders;
  },

  async getStationJobs(stationType: string): Promise<StationJob[]> {
    const res = await getJson<{ items: StationJob[] }>(`/api/stations/${stationType}/jobs`, `Blad pobierania zadan dla ${stationType}`);
    return res.items;
  },

  async updateStationJob(taskId: string, payload: { status: string; blocked_reason?: string; note?: string; worker?: string }): Promise<void> {
    await patchJson(`/api/operations/routes/${taskId}/status`, payload, "Blad aktualizacji zadania");
  },

  async handoffStationJob(taskId: string, workerName?: string): Promise<void> {
    await patchJson(`/api/operations/routes/${taskId}/handoff`, { worker: workerName }, "Błąd przekazywania zadania");
  },

  async acceptStationJob(taskId: string, workerName?: string): Promise<void> {
    await patchJson(`/api/operations/routes/${taskId}/accept`, { worker: workerName }, "Błąd akceptacji zadania");
  },

  async rejectStationJob(taskId: string, reason: string, workerName?: string): Promise<void> {
    await patchJson(`/api/operations/routes/${taskId}/reject`, { reason, worker: workerName }, "Błąd odrzucenia zadania");
  },

  async getProductionWorkflowReadiness(): Promise<ProjectProductionReadiness[]> {
    const res = await getJson<{ projects: ProjectProductionReadiness[] }>("/api/production/workflow/readiness", "Blad pobierania gotowosci produkcji");
    return res.projects;
  },

  async getFulfillmentQueue(): Promise<FulfillmentQueueItem[]> {
    const res = await getJson<{ items: FulfillmentQueueItem[] }>("/api/fulfillment/queue", "Błąd pobierania kolejki wysyłkowej");
    return res.items;
  },

  async updateFulfillmentStatus(projectName: string, payload: Partial<FulfillmentRecord>): Promise<void> {
    await patchJson(`/api/fulfillment/${encodeURIComponent(projectName)}/status`, payload, "Błąd aktualizacji statusu wysyłki");
  },

  async createProject(title: string, clientName: string) {
    return postJson<{ status: string; id: number }>(
      "/projects",
      { title, client_name: clientName },
      "Blad zapisu projektu"
    );
  },

  async updateMargin(projectId: number, margin: number) {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/margin`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ margin }),
    });
    if (!res.ok) throw new Error("Blad aktualizacji marzy");
    return res.json();
  },

  async getProjectModules(projectId: number): Promise<ProjectModule[]> {
    const res = await fetch(`${API_BASE_URL}/config/modules/${projectId}`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania modulow projektu");
    return res.json();
  },

  async getModuleValuation(moduleId: number | string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/config/modules/${moduleId}/valuation`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania wyceny modulu");
    return res.json();
  },

  async getProjectAssemblySummary(projectId: number): Promise<AssemblySummary> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/assembly-summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania podsumowania kompletu");
    return res.json();
  },

  async getProjectWorkspaceSummary(projectId: number): Promise<WorkspaceSummary> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/workspace-summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania podsumowania workspace");
    return res.json();
  },

  async getProjectFinanceSummary(projectId: number): Promise<FinanceSummary> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/finance-summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania podsumowania finansAw");
    return res.json();
  },

  async getProjectWallSummary(projectId: number): Promise<WallSummary> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/wall-summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania podsumowania sciany");
    return res.json();
  },

  async getWallConfig(projectId: number): Promise<WallConfig> {
    const res = await fetch(`${API_BASE_URL}/config/wall/${projectId}`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania konfiguracji sciany");
    return res.json();
  },

  async updateWallConfig(
    projectId: number,
    payload: { width: number; height: number; room_depth?: number }
  ): Promise<WallConfig> {
    return putJson<WallConfig>(`/config/wall/${projectId}`, payload, "Blad zapisu konfiguracji sciany");
  },

  async getProjectCalendarEvents(projectId: number): Promise<{ project_id: number; events: CalendarEventRecord[] }> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/calendar-events`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania eventAw kalendarza");
    return res.json();
  },

  async getCalendarEvents(limit = 500): Promise<{ events: CalendarEventRecord[] }> {
    const res = await fetch(`${API_BASE_URL}/api/calendar/events?limit=${limit}`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania kalendarza");
    return res.json();
  },

  async getCalendarWorkboard(
    options?: { daysBack?: number; daysForward?: number; limit?: number; includeUndated?: boolean }
  ): Promise<CalendarWorkboardResponse> {
    const qs = new URLSearchParams({
      days_back: String(options?.daysBack ?? 30),
      days_forward: String(options?.daysForward ?? 365),
      limit: String(options?.limit ?? 500),
      include_undated: String(options?.includeUndated ?? true),
    });
    const res = await fetch(`${API_BASE_URL}/api/calendar/workboard?${qs.toString()}`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania kalendarza prac");
    return res.json();
  },

  async createCalendarEvent(payload: CalendarEventPayload): Promise<{ status: string; event: CalendarEventRecord }> {
    return postJson<{ status: string; event: CalendarEventRecord }>(
      "/api/calendar/events",
      payload,
      "Blad dodawania eventu kalendarza"
    );
  },

  async patchCalendarEvent(eventId: string, payload: Partial<CalendarEventPayload>): Promise<{ status: string; event: CalendarEventRecord }> {
    return patchJson<{ status: string; event: CalendarEventRecord }>(
      `/api/calendar/events/${eventId}`,
      payload,
      "Blad aktualizacji eventu kalendarza"
    );
  },

  async deleteCalendarEvent(eventId: string): Promise<{ status: string }> {
    return deleteJson<{ status: string }>(`/api/calendar/events/${eventId}`, "Blad usuwania eventu kalendarza");
  },

  async getProjectMvpReadiness(projectId: number): Promise<MvpReadiness> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/mvp-readiness`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania gotowosci MVP");
    return res.json();
  },

  async getProjectsMvpReadinessSummary(): Promise<ProjectsMvpReadinessSummary> {
    const res = await fetch(`${API_BASE_URL}/projects/mvp-readiness-summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania zbiorczej gotowosci MVP");
    return res.json();
  },

  async getCatalogCategories(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/catalog/categories`, { credentials: "include" });
    if (!res.ok) return [];
    return res.json();
  },

  async getManufacturers(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/catalog/manufacturers`, { credentials: "include" });
    if (!res.ok) return [];
    return res.json();
  },

  async getCatalogItems(filters?: { category_id?: number; include_deleted?: boolean }): Promise<any[]> {
    const params = new URLSearchParams();
    if (typeof filters?.category_id === "number") params.append("category_id", String(filters.category_id));
    if (filters?.include_deleted) params.append("include_deleted", "true");
    
    const query = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${API_BASE_URL}/catalog/items${query}`, { credentials: "include" });
    if (!res.ok) return [];
    return res.json();
  },

  async getMaterials(options?: { include_deleted?: boolean }): Promise<MaterialRecord[]> {
    const query = options?.include_deleted ? "?include_deleted=true" : "";
    const res = await fetch(`${API_BASE_URL}/db/materials${query}`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania bazy materialow");
    return res.json();
  },

  async createMaterial(payload: {
    name: string;
    price_per_m2: number;
    thickness: number;
    material_code?: string;
    category?: string;
    material_kind?: string;
    unit?: string;
    is_library?: boolean;
    stock_quantity?: number;
    min_stock?: number;
    purchase_type?: string;
    supplier?: string;
    wholesaler?: string;
    format_length_mm?: number;
    format_width_mm?: number;
    pack_size?: number;
    parameter_json?: string;
  }): Promise<{ status: string; id: number }> {
    return postJson<{ status: string; id: number }>(
      "/db/materials",
      payload,
      "Blad zapisu materialu"
    );
  },

  async updateMaterial(materialId: number, payload: {
    name?: string;
    price_per_m2?: number;
    thickness?: number;
    material_code?: string;
    category?: string;
    material_kind?: string;
    unit?: string;
    min_stock?: number;
    purchase_type?: string;
    supplier?: string;
    wholesaler?: string;
    parameter_json?: string;
    format_length_mm?: number;
    format_width_mm?: number;
    pack_size?: number;
  }): Promise<{ status: string }> {
    return patchJson<{ status: string }>(
      `/db/materials/${materialId}`,
      payload,
      "Blad aktualizacji pozycji materialu"
    );
  },

  async parseValuationSheet(text: string): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/agent/parse-valuation-sheet`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error("Blad parsowania arkusza");
    return res.json();
  },

  async getProjectMaterialSummary(projectId: number): Promise<Array<{ name: string; count: number; total_area_m2: number }>> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/material-summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania podsumowania materialow");
    return res.json();
  },

  async getProjectUnifiedSummary(projectId: number): Promise<UnifiedSummaryData> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/unified-summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania ujednoliconego podsumowania");
    return res.json();
  },

  async getDatabaseOverview(): Promise<DatabaseOverview> {
    const res = await fetch(`${API_BASE_URL}/db/overview`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania podsumowania baz");
    return res.json();
  },

  async getSystemSummary(): Promise<SystemSummary> {
    const res = await fetch(`${API_BASE_URL}/system/summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania podsumowania systemu");
    return res.json();
  },

  async getDashboardV1(periodDays = 30, topLimit = 5): Promise<DashboardV1Response> {
    const qs = new URLSearchParams({
      period_days: String(periodDays),
      top_limit: String(topLimit),
    });
    const res = await fetch(`${API_BASE_URL}/api/dashboard/v1?${qs.toString()}`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania dashboardu V1");
    return res.json();
  },

  async getClients(): Promise<ClientRecord[]> {
    const res = await fetch(`${API_BASE_URL}/db/clients`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania kontrahentow");
    return res.json();
  },

  async createClient(payload: {
    name: string;
    location?: string;
    address?: string;
    email?: string;
    phone?: string;
    type?: "person" | "b2b";
    status?: "active" | "vip" | "archived";
  }): Promise<{ status: string; id: number }> {
    return postJson<{ status: string; id: number }>(
      "/db/clients",
      payload,
      "Blad zapisu kontrahenta"
    );
  },

  async getOrders(projectId?: number, include_deleted?: boolean): Promise<OrderRecord[]> {
    const params = new URLSearchParams();
    if (typeof projectId === "number") params.append("project_id", String(projectId));
    if (include_deleted) params.append("include_deleted", "true");
    
    const query = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${API_BASE_URL}/orders${query}`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania zamowien");
    return res.json();
  },

  async createOrder(payload: {
    project_id: number;
    client_name: string;
    title: string;
    deadline?: string;
    deadline_from?: string;
    deadline_to?: string;
    budget?: number;
    status?: string;
    spec_json?: string;
  }): Promise<{ status: string; id: number }> {
    return postJson<{ status: string; id: number }>(
      "/orders",
      payload,
      "Blad zapisu zamowienia"
    );
  },

  async previewServicePricing(payload: {
    item: Record<string, unknown>;
    tariff_profile?: string;
  }): Promise<{ status: string; schema_version: string; result: ServicePricingResult }> {
    return postJson<{ status: string; schema_version: string; result: ServicePricingResult }>(
      "/api/service-pricing/preview",
      payload,
      "Blad podgladu kalkulacji uslugi"
    );
  },

  async updateOrderStatus(
    orderId: number,
    payload: { status: string; worker?: string }
  ): Promise<{ status: string; message?: string }> {
    return postJson<{ status: string; message?: string }>(
      `/api/orders/${orderId}/status`,
      payload,
      "Blad zmiany statusu zamowienia"
    );
  },

  async agentCommand(text: string, projectId = 1): Promise<AgentPreview> {
    return postJson<AgentPreview>(
      "/agent/command",
      { text, project_id: projectId },
      "Agent nie zrozumial polecenia"
    );
  },

  async previewModuleOperation(request: OperationRequest): Promise<OperationResult> {
    return postJson<OperationResult>(
      "/operations/module/preview",
      request,
      "Blad podgladu operacji"
    );
  },

  async applyModuleOperation(request: OperationRequest): Promise<OperationResult> {
    return postJson<OperationResult>(
      "/operations/module/apply",
      request,
      "Blad zastosowania operacji"
    );
  },

  async previewBulkModuleOperation(request: {
    action: OperationAction;
    module_ids: string[];
    params?: Record<string, unknown>;
    source?: string;
  }): Promise<BulkOperationResult> {
    return postJson<BulkOperationResult>(
      "/operations/module/bulk/preview",
      request,
      "Blad podgladu operacji hurtowej"
    );
  },

  async applyBulkModuleOperation(request: {
    action: OperationAction;
    module_ids: string[];
    params?: Record<string, unknown>;
    source?: string;
  }): Promise<BulkOperationResult> {
    return postJson<BulkOperationResult>(
      "/operations/module/bulk/apply",
      request,
      "Blad zastosowania operacji hurtowej"
    );
  },

  async getWallPoints(wallName: string): Promise<WallPointsResponse> {
    const res = await fetch(`${API_BASE_URL}/wall/${encodeURIComponent(wallName)}`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania punktow sciany");
    return res.json();
  },

  async previewWallOperation(request: OperationRequest): Promise<OperationResult> {
    return postJson<OperationResult>(
      "/operations/wall/preview",
      request,
      "Blad podgladu operacji sciany"
    );
  },

  async applyWallOperation(request: OperationRequest): Promise<OperationResult> {
    return postJson<OperationResult>(
      "/operations/wall/apply",
      request,
      "Blad zastosowania operacji sciany"
    );
  },

  // --- NEW: IMPORT & PDF ---
  getProjectPdfUrl(projectId: number): string {
    return `${API_BASE_URL}/projects/${projectId}/export-pdf`;
  },

  async getProjectObstacles(projectId: number): Promise<Obstacle[]> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/obstacles`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania przeszkod");
    return res.json();
  },

  async updateProjectObstacles(projectId: number, obstacles: Obstacle[]) {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/obstacles`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ obstacles }),
    });
    if (!res.ok) throw new Error("Blad aktualizacji przeszkod");
    return res.json();
  },

  async updateProjectModulePlacement(
    projectId: number,
    moduleId: number | string,
    payload: { x_mm?: number; y_mm?: number; z_mm?: number; rotation_deg?: number }
  ): Promise<{ status: string; module_id: number; placement: Record<string, number> }> {
    return patchJson<{ status: string; module_id: number; placement: Record<string, number> }>(
      `/projects/${projectId}/modules/${moduleId}/placement`,
      payload,
      "Blad aktualizacji polozenia modulu"
    );
  },

  async importParse(file: File): Promise<ImportResult> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE_URL}/import-3d/parse`, {
      method: "POST",
      credentials: "include",
      body: formData,
    });
    if (!res.ok) await readJsonError(res, "Blad parsowania pliku .project");
    return res.json();
  },

   async importFinalize(payload: { title: string; client_name: string; rows: any[]; file_path?: string }): Promise<{ project_id: number }> {
    return postJson<{ project_id: number }>(
      "/import-3d/finalize",
      payload,
      "Blad finalizacji importu"
    );
  },

  // --- NEW: PRODUCTION ---
  async getProjectProductionSummary(projectId: number): Promise<ProductionSummary> {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/production-summary`, { credentials: "include" });
    if (!res.ok) throw new Error("Blad pobierania danych produkcyjnych");
    return res.json();
  },

  getProjectProductionExportUrl(projectId: number): string {
    return `${API_BASE_URL}/projects/${projectId}/production-export-csv`;
  },

  async getTechnicians(): Promise<any[]> {
    return getJson<any[]>("/technicians", "Blad pobierania technikow");
  },

  async loginTechnician(name: string, pin: string): Promise<unknown> {
    const res = await fetch(`${API_BASE_URL}/technicians/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name, pin }),
    });
    if (!res.ok) await readJsonError(res, "Blad logowania");
    return res.json();
  },

  async scanInvoices(): Promise<InvoiceScanned[]> {
    const res = await fetch(`${API_BASE_URL}/db/scan-invoices`);
    if (!res.ok) throw new Error("Blad skanowania faktur");
    return res.json();
  },

  async getInvoices(): Promise<InvoiceScanned[]> {
     const res = await fetch(`${API_BASE_URL}/db/invoices`);
     if (!res.ok) throw new Error("Blad pobierania bazy faktur");
     return res.json();
  },

  async createInvoice(payload: {
     nr: string;
     date: string;
     nip: string;
     net: number;
     vat: number;
     gross: number;
     folder: string;
  }): Promise<{ status: string; id: number }> {
     return postJson<{ status: string; id: number }>(
       "/db/invoices",
       payload,
       "Blad zapisu faktury do bazy"
     );
  },

  async importInvoicePdf(file: File): Promise<{
    status: string;
    invoice_id: number;
    is_duplicate: boolean;
    duplicate_reason: string;
    line_items_total: number;
  }> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE_URL}/api/db/invoices/import`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) await readJsonError(res, "Blad importu faktury PDF");
    return res.json();
  },

  async getInvoiceLineItems(invoiceId: number): Promise<{
    status: string;
    invoice_id: number;
    items: InvoiceLineItemRecord[];
    total: number;
  }> {
    const res = await fetch(`${API_BASE_URL}/api/db/invoices/${invoiceId}/line-items`);
    if (!res.ok) throw new Error("Blad pobierania pozycji faktury");
    return res.json();
  },

  async updateInvoiceLineItem(
    invoiceId: number,
    lineItemId: number,
    payload: Partial<InvoiceLineItemRecord> & { review_status?: string }
  ): Promise<{ status: string }> {
    return patchJson<{ status: string }>(
      `/api/db/invoices/${invoiceId}/line-items/${lineItemId}`,
      payload,
      "Blad aktualizacji pozycji faktury"
    );
  },

  async confirmInvoice(
    invoiceId: number,
    lineItemIds: number[] = []
  ): Promise<{
    status: string;
    invoice_id: number;
    arrivals_created: number;
    price_history_written: number;
    skipped_lines: number;
  }> {
    return postJson<{
      status: string;
      invoice_id: number;
      arrivals_created: number;
      price_history_written: number;
      skipped_lines: number;
    }>(
      `/api/db/invoices/${invoiceId}/confirm`,
      { line_item_ids: lineItemIds },
      "Blad potwierdzania faktury"
    );
  },

  async checkInvoiceSources(payload: {
    since_date?: string;
    scan_local?: boolean;
    scan_email?: boolean;
    scan_telegram?: boolean;
    scan_whatsapp?: boolean;
    local_dirs?: string[];
    recursive?: boolean;
    max_local_files?: number;
    max_email_messages?: number;
    worker_name?: string;
  }): Promise<{
    status: string;
    since_date: string;
    summary: { checked: number; imported: number; duplicates: number; errors: number };
    local: { checked: number; imported: number; duplicates: number; errors: number };
    email: { checked: number; imported: number; duplicates: number; errors: number };
    warnings: string[];
  }> {
    return postJson<{
      status: string;
      since_date: string;
      summary: { checked: number; imported: number; duplicates: number; errors: number };
      local: { checked: number; imported: number; duplicates: number; errors: number };
      email: { checked: number; imported: number; duplicates: number; errors: number };
      warnings: string[];
    }>(
      "/api/db/invoices/check-sources",
      payload || {},
      "Blad sprawdzania zrodel faktur"
    );
  },

  async getTaxSummary(): Promise<TaxSummary> {
     const res = await fetch(`${API_BASE_URL}/db/tax-summary`);
     if (!res.ok) throw new Error("Blad pobierania salda podatkowego");
     return res.json();
  },

  // --- WORK TIME (RCP) ---
  async getWorkSheets(): Promise<WorkerMonthSheet[]> {
    const res = await fetch(`${API_BASE_URL}/api/work_time`);
    if (!res.ok) throw new Error("Blad pobierania list obecnosci");
    const data = await res.json();
    return data.data || [];
  },

  async saveWorkSheet(sheet: WorkerMonthSheet): Promise<{ ok: boolean }> {
    return postJson<{ ok: boolean }>(
      "/api/work_time",
      sheet,
      "Blad zapisu listy obecnosci"
    );
  },

  async getKioskWorkers(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/api/kiosk/workers`);
    if (!res.ok) throw new Error("Blad pobierania pracownikow kiosku");
    const data = await res.json();
    return data.workers || [];
  },

  async performKioskAction(
    workerId: string,
    action: string,
    workType = "Produkcja",
    options?: { project_code?: string; order_id?: string; workstation?: string; note?: string; worker_name?: string }
  ): Promise<KioskResult> {
    return postJson<KioskResult>(
      "/api/kiosk/action",
      {
        worker_id: workerId,
        action,
        work_type: workType,
        project_code: options?.project_code || "",
        order_id: options?.order_id || "",
        workstation: options?.workstation || "",
        note: options?.note || "",
        worker_name: options?.worker_name || "",
      },
      "Blad zapisu akcji RCP"
    );
  },

  async resolveKioskScan(qrText: string): Promise<KioskResult> {
    return postJson<KioskResult>(
      "/api/kiosk/scan",
      { qr_text: qrText },
      "Blad rozpoznawania kodu QR"
    );
  },

  // --- ARRIVALS (ETAP 4) ---
  async getArrivals(): Promise<ArrivalRecord[]> {
    const res = await fetch(`${API_BASE_URL}/api/db/arrivals`);
    if (!res.ok) throw new Error("Blad pobierania historii dostaw");
    return res.json();
  },

  async getLowStockMaterials(limit = 200): Promise<{ status: string; total: number; limit: number; items: LowStockItem[] }> {
    const res = await fetch(`${API_BASE_URL}/api/db/materials/low-stock?limit=${encodeURIComponent(String(limit))}`);
    if (!res.ok) throw new Error("Blad pobierania niskich stanow magazynowych");
    return res.json();
  },

  async createArrival(payload: Omit<ArrivalRecord, "id">): Promise<{ status: string }> {
    return postJson<{ status: string }>(
      "/api/db/arrivals",
      payload,
      "Blad zapisu dostawy"
    );
  },

  async updateArrival(arrivalId: number, payload: Partial<Omit<ArrivalRecord, "id">>): Promise<{ status: string }> {
    return patchJson<{ status: string }>(
      `/api/db/arrivals/${arrivalId}`,
      payload,
      "Blad aktualizacji dostawy"
    );
  },

  async getProductionStatus(): Promise<ProductionStatus> {
    const res = await fetch(`${API_BASE_URL}/api/production/status`);
    if (!res.ok) throw new Error("Blad pobierania statusu produkcji");
    return res.json();
  },
  async getProductionTasks(
    station = "",
    status: "active" | "done" | "all" | string = "active",
    limit = 200
  ): Promise<{ status: string; station: string; items: ProductionTask[]; total: number; limit: number }> {
    const params = new URLSearchParams({
      station,
      status,
      limit: String(limit),
    });
    const res = await fetch(`${API_BASE_URL}/api/production/tasks?${params.toString()}`);
    if (!res.ok) throw new Error("Blad pobierania zadan produkcyjnych");
    return res.json();
  },

  async toggleProductionTask(
    taskId: string,
    workerId: string,
    workerName: string,
    action: "start" | "finish",
    options?: { note?: string; correction_note?: string }
  ): Promise<{ status: string; task: ProductionTask; created_issue_id?: string; actor?: { worker_id: string; worker_name: string } }> {
    return postJson<{ status: string; task: ProductionTask; created_issue_id?: string; actor?: { worker_id: string; worker_name: string } }>(
      "/api/production/task-action",
      {
        task_id: taskId,
        worker_id: workerId,
        worker_name: workerName,
        action,
        note: options?.note || "",
        correction_note: options?.correction_note || "",
      },
      "Blad aktualizacji zadania produkcji"
    );
  },

  async getAiAdvice(): Promise<{ tips: AiTip[] }> {
    const res = await fetch(`${API_BASE_URL}/api/ai/advisor`);
    if (!res.ok) throw new Error("Blad pobierania porad AI");
    return res.json();
  },

  async getAiPredictions(): Promise<{ predictions: AiPrediction[] }> {
    const res = await fetch(`${API_BASE_URL}/api/ai/predictions`);
    if (!res.ok) throw new Error("Blad pobierania prognoz AI");
    return res.json();
  },

  async sendTelegramLowStock(limit = 20): Promise<{ status: string; limit: number; message: string }> {
    return postJson<{ status: string; limit: number; message: string }>(
      `/api/telegram/send-low-stock?limit=${encodeURIComponent(String(limit))}`,
      {},
      "Blad wysyL,ki raportu niskich stanow na Telegram"
    );
  },

  async getIssues(): Promise<IssueCandidate[]> {
    const res = await fetch(`${API_BASE_URL}/api/issues`);
    if (!res.ok) throw new Error("Blad pobierania flag systemowych");
    return res.json();
  },

  async getAlarms(includeResolved = false): Promise<{ items: AlarmRecord[]; total: number }> {
    const res = await fetch(`${API_BASE_URL}/api/alarms?include_resolved=${includeResolved ? "true" : "false"}`);
    if (!res.ok) throw new Error("Blad pobierania alarmAw");
    return res.json();
  },

  async acknowledgeAlarm(alarmId: string, acknowledged = true, note = ""): Promise<{ status: string; alarm: AlarmRecord }> {
    return patchJson<{ status: string; alarm: AlarmRecord }>(
      `/api/alarms/${encodeURIComponent(alarmId)}/ack`,
      { acknowledged, note },
      "Blad potwierdzenia alarmu"
    );
  },

  async resolveAlarm(alarmId: string): Promise<{ status: string; alarm_id: string }> {
    return patchJson<{ status: string; alarm_id: string }>(
      `/api/alarms/${encodeURIComponent(alarmId)}/resolve`,
      {},
      "Blad domkniecia alarmu"
    );
  },

  async getOperationsSummary(): Promise<OperationsSummary> {
    const res = await fetch(`${API_BASE_URL}/api/operations/summary`);
    if (!res.ok) throw new Error("Blad pobierania podsumowania operations");
    return res.json();
  },

  async getOperationsIssues(status: "active" | "all" | "closed" | string = "active"): Promise<{ status: string; items: OperationsIssueRecord[]; total: number; filter?: string; limit?: number }> {
    const res = await fetch(`${API_BASE_URL}/api/operations/issues?status=${encodeURIComponent(status)}`);
    if (!res.ok) throw new Error("Blad pobierania issue operations");
    return res.json();
  },

  async patchOperationsIssue(issueId: string, payload: {
    status?: string;
    owner?: string;
    priority_manual?: string;
    due_date?: string;
    notes?: string;
  }): Promise<{ status: string; issue: OperationsIssueRecord }> {
    return patchJson<{ status: string; issue: OperationsIssueRecord }>(
      `/api/operations/issues/${encodeURIComponent(issueId)}`,
      payload,
      "Blad aktualizacji issue"
    );
  },

  async recommendOperationRoutes(payload?: {
    planned_date?: string;
    crew?: string;
    limit?: number;
  }): Promise<{ items: RouteRecommendation[]; total: number }> {
    return postJson<{ items: RouteRecommendation[]; total: number }>(
      "/api/operations/routes/recommend",
      payload ?? {},
      "Blad rekomendacji tras"
    );
  },

  async seedData(): Promise<any> {
    return postJson<any>("/api/dev/seed", {}, "Blad podczas siania danych");
  },

  async saveWorker(worker: any): Promise<{ ok: boolean }> {
    return postJson<{ ok: boolean }>(
      "/api/kiosk/workers",
      worker,
      "Blad zapisu danych pracownika"
    );
  },

  // ===================== Inventory Write-Off =====================

  async getInventoryBalances(limit = 500): Promise<InventoryBalance[]> {
    const res = await fetch(`${API_BASE_URL}/api/inventory/balances?limit=${limit}`);
    if (!res.ok) throw new Error("Blad pobierania stanow magazynowych");
    return res.json();
  },

  async getInventoryMovements(opts?: { material_id?: number; order_id?: number; limit?: number }): Promise<InventoryMovement[]> {
    const qs = new URLSearchParams();
    if (opts?.material_id != null) qs.set("material_id", String(opts.material_id));
    if (opts?.order_id != null) qs.set("order_id", String(opts.order_id));
    qs.set("limit", String(opts?.limit ?? 500));
    const res = await fetch(`${API_BASE_URL}/api/inventory/movements?${qs.toString()}`);
    if (!res.ok) throw new Error("Blad pobierania ruchow magazynowych");
    return res.json();
  },

  async getMaterialUnitCost(materialId: number): Promise<{ material_id: number; unit_cost_net: number }> {
    const res = await fetch(`${API_BASE_URL}/api/inventory/material-cost/${materialId}`);
    if (!res.ok) throw new Error("Blad pobierania kosztu jednostkowego");
    return res.json();
  },

  async getOrderCosts(orderId: number): Promise<{ entries: OrderCostEntry[]; summary: OrderCostSummary }> {
    const res = await fetch(`${API_BASE_URL}/api/inventory/order-costs/${orderId}`);
    if (!res.ok) throw new Error("Blad pobierania kosztow zamowienia");
    return res.json();
  },

  async reserveMaterial(payload: ReserveMaterialPayload): Promise<any> {
    return postJson("/api/inventory/reserve", payload, "Blad rezerwacji materialu");
  },

  async cancelReservation(reservationMovementId: number, createdBy = ""): Promise<any> {
    return postJson("/api/inventory/cancel-reservation", { reservation_movement_id: reservationMovementId, created_by: createdBy }, "Blad anulowania rezerwacji");
  },

  async issueMaterial(payload: IssueMaterialPayload): Promise<any> {
    return postJson("/api/inventory/issue", payload, "Blad wydania materialu");
  },

  async returnMaterial(payload: ReturnMaterialPayload): Promise<any> {
    return postJson("/api/inventory/return", payload, "Blad zwrotu materialu");
  },

  async scrapMaterial(payload: ScrapMaterialPayload): Promise<any> {
    return postJson("/api/inventory/scrap", payload, "Blad odpisu braków");
  },

  async correctInventory(payload: CorrectionPayload): Promise<any> {
    return postJson("/api/inventory/correction", payload, "Blad korekty stanow");
  },

  // ===================== Purchase Documents =====================

  async getPurchaseDocuments(limit = 200): Promise<PurchaseDocument[]> {
    const res = await fetch(`${API_BASE_URL}/api/inventory/purchase-documents?limit=${limit}`);
    if (!res.ok) throw new Error("Blad pobierania dokumentow zakupu");
    return res.json();
  },

  async getPurchaseDocument(docId: number): Promise<{ document: PurchaseDocument; lines: PurchaseDocumentLine[] }> {
    const res = await fetch(`${API_BASE_URL}/api/inventory/purchase-documents/${docId}`);
    if (!res.ok) throw new Error("Blad pobierania dokumentu zakupu");
    return res.json();
  },

  async createPurchaseDocument(payload: PurchaseDocumentCreatePayload): Promise<{ status: string; id: number; line_ids: number[] }> {
    return postJson("/api/inventory/purchase-documents", payload, "Blad tworzenia dokumentu zakupu");
  },

  async receivePurchaseDocument(docId: number, paymentMethod = "", createdBy = ""): Promise<any> {
    return postJson(`/api/inventory/purchase-documents/${docId}/receive`, { payment_method: paymentMethod, created_by: createdBy }, "Blad przyjecia dokumentu zakupu");
  },

  // ===================== Cash/Bank Movements =====================

  async getCashBankMovements(limit = 500): Promise<CashBankMovement[]> {
    const res = await fetch(`${API_BASE_URL}/api/inventory/cash-movements?limit=${limit}`);
    if (!res.ok) throw new Error("Blad pobierania ruchow finansowych");
    return res.json();
  },

  async shutdownSystem(): Promise<void> {
    await fetch(`${API_BASE_URL}/system/shutdown`, { method: "POST" });
  },

  async getAuditLog(limit: number = 500): Promise<AuditEntry[]> {
    const res = await fetch(`${API_BASE_URL}/admin/audit-log?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch audit log");
    const data = await res.json();
    return data.logs;
  },

  async getRouteTasks(): Promise<RouteTaskRecord[]> {
    const res = await fetch(`${API_BASE_URL}/operations/routes`);
    if (!res.ok) throw new Error("Failed to fetch route tasks");
    return res.json();
  },

  async getDashboardV2(): Promise<DashboardV2Response> {
    const res = await fetch(`${API_BASE_URL}/api/dashboard/v2`);
    if (!res.ok) throw new Error("Failed to fetch Dashboard V2");
    return res.json();
  },

  async getKriV1(): Promise<KriResponse> {
    const res = await fetch(`${API_BASE_URL}/kri/v1`);
    if (!res.ok) throw new Error("Failed to fetch KRI");
    return res.json();
  },

  async deleteProject(id: number | string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/projects/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Blad usuwania projektu");
    return res.json();
  },

  async deleteMaterial(id: number | string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/materials/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Blad usuwania materialu");
    return res.json();
  },

  async deleteOrder(id: number | string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/orders/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Blad usuwania zamowienia");
    return res.json();
  },

  async updateRouteTaskStatus(routeId: string, status: string, note?: string, worker?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/operations/routes/${routeId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, note, worker }),
    });
    if (!res.ok) throw new Error("Blad aktualizacji statusu trasy");
    return res.json();
  },

  async restoreProject(projectId: number): Promise<{ status: string }> {
    return postJson<{ status: string }>(`/api/admin/projects/${projectId}/restore`, {}, "Blad przywracania projektu");
  },

  async restoreMaterial(materialId: number): Promise<{ status: string }> {
    return postJson<{ status: string }>(`/api/admin/materials/${materialId}/restore`, {}, "Blad przywracania materialu");
  },

  async restoreOrder(orderId: number): Promise<{ status: string }> {
    return postJson<{ status: string }>(`/api/admin/orders/${orderId}/restore`, {}, "Blad przywracania zamowienia");
  },

  async getBackups(): Promise<{ backups: Array<{ name: string; size: number; created_at: string }> }> {
    const res = await fetch(`${API_BASE_URL}/api/admin/backups`);
    if (!res.ok) throw new Error("Blad pobierania listy backupow");
    return res.json();
  },
};

export interface InvoiceScanned {
  id?: number;
  invoice_id?: number;
  filename: string;
  folder: string;
  nr: string;
  date: string;
  nip: string;
  net: number;
  vat: number;
  total: number;
  status: string;
  raw_text: string;
  line_items_total?: number;
  line_items_reviewed?: number;
  line_items_exported?: number;
  supplier?: string;
  currency?: string;
  source_filename?: string;
  payload_hash?: string;
  parse_method?: string;
  parse_confidence?: number;
  duplicate_of_invoice_id?: number;
}

export interface InvoiceLineItemRecord {
  id: number;
  invoice_id: number;
  line_no: number;
  raw_line: string;
  name_raw: string;
  name_norm: string;
  quantity: number;
  unit: string;
  unit_price_net: number;
  unit_price_gross: number;
  total_net: number;
  total_gross: number;
  vat_rate: string;
  material_type: string;
  thickness_mm: string;
  parse_source: string;
  confidence: number;
  review_status: string;
  selected_material_id?: number | null;
  selected_material_name?: string;
  notes?: string;
}

export interface TaxSummary {
  sales_net: number;
  vat_collected: number;
  costs_net: number;
  vat_paid: number;
  costs_gross: number;
  tax_balance: number;
  recommendation: string;
}

// ===================== Inventory Write-Off Types =====================

export type InventoryBalance = {
  material_id: number;
  material_name?: string | null;
  material_unit?: string | null;
  variant_id?: number | null;
  location: string;
  qty_on_hand: number;
  qty_reserved: number;
  qty_available: number;
  last_updated_at?: string;
};

export type InventoryMovement = {
  id: number;
  catalog_item_id?: number;
  material_id?: number;
  material_name?: string | null;
  variant_id?: number | null;
  movement_type: "IN" | "RESERVED" | "OUT" | "RETURN" | "SCRAP" | "CORRECTION" | string;
  qty: number;
  unit: string;
  unit_cost_net?: number | null;
  total_cost_net?: number | null;
  location?: string;
  order_id?: number | null;
  order_title?: string | null;
  order_client_name?: string | null;
  purchase_document_id?: number | null;
  purchase_document_line_id?: number | null;
  related_movement_id?: number | null;
  note?: string;
  created_at?: string;
  created_by?: string;
};

export type OrderCostEntry = {
  id: number;
  order_id: number;
  cost_type: string;
  source_type: string;
  source_id?: number | null;
  amount_net: number;
  vat_rate: number;
  amount_gross: number;
  qty?: number | null;
  unit?: string | null;
  description: string;
  note?: string;
  created_at?: string;
  created_by?: string;
};

export type OrderCostSummary = Record<string, number>;

export type ReserveMaterialPayload = {
  material_id: number;
  order_id: number;
  qty: number;
  unit?: string;
  note?: string;
  created_by?: string;
};

export type IssueMaterialPayload = {
  material_id: number;
  order_id: number;
  qty: number;
  unit?: string;
  unit_cost_override?: number | null;
  note?: string;
  created_by?: string;
};

export type ReturnMaterialPayload = {
  material_id: number;
  order_id: number;
  qty: number;
  unit?: string;
  related_issue_movement_id?: number | null;
  note?: string;
  created_by?: string;
};

export type ScrapMaterialPayload = {
  material_id: number;
  qty: number;
  unit?: string;
  order_id?: number | null;
  charge_to_order?: boolean;
  note?: string;
  created_by?: string;
};

export type CorrectionPayload = {
  material_id: number;
  qty_delta: number;
  unit?: string;
  note?: string;
  created_by?: string;
};

export type PurchaseDocument = {
  id: number;
  supplier_name: string;
  document_number: string;
  document_date: string;
  document_type: string;
  currency: string;
  total_net: number;
  total_gross: number;
  payment_status: string;
  payment_method: string;
  note: string;
  created_at?: string;
  updated_at?: string;
};

export type PurchaseDocumentLine = {
  id: number;
  purchase_document_id: number;
  material_id?: number | null;
  material_name?: string | null;
  description_snapshot: string;
  qty: number;
  unit: string;
  unit_price_net: number;
  vat_rate: number;
  line_total_net: number;
  line_total_gross: number;
  is_stock_item: number | boolean;
  order_id?: number | null;
  note: string;
};

export type PurchaseDocumentCreatePayload = {
  supplier_name: string;
  document_number: string;
  document_date: string;
  document_type?: string;
  currency?: string;
  total_net?: number;
  total_gross?: number;
  payment_status?: string;
  payment_method?: string;
  note?: string;
  lines?: Array<{
    material_id?: number | null;
    description_snapshot?: string;
    qty: number;
    unit?: string;
    unit_price_net: number;
    vat_rate?: number;
    is_stock_item?: boolean;
    order_id?: number | null;
    note?: string;
  }>;
};

export type CashBankMovement = {
  id: number;
  movement_type: string;
  amount: number;
  currency: string;
  payment_method: string;
  supplier_name: string;
  purchase_document_id?: number | null;
  order_id?: number | null;
  note: string;
  created_at?: string;
  created_by?: string;
};

export interface ProductionSummary {
  project_id: number;
  parts: ProductionPart[];
  material_stats: MaterialUsage[];
  parts_count: number;
}

export interface ProductionPart {
  module_id: number;
  module_name: string;
  part_key: string;
  name: string;
  material: string;
  width: number;
  height: number;
  thickness: number;
  area_m2: number;
}

export interface MaterialUsage {
  name: string;
  total_m2: number;
  parts_count: number;
}
