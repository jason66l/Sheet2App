/** Shape of POST /demo/import (backend/demo_server.py). Mirrors backend/spec/models.py loosely. */

export type FieldType = 'text' | 'number' | 'money' | 'date' | 'enum' | 'ref' | 'file' | 'user';
export type ComputedType = 'number' | 'money' | 'percent';

export type Field = { name: string; label: string; type: FieldType; required?: boolean; options?: string[] | null; ref_entity?: string | null };
export type Computed = { name: string; label: string; type: ComputedType; expr: string };
export type Entity = { name: string; label: string; fields: Field[]; computed?: Computed[]; display_field: string; workflow?: string | null };

export type ApprovalRule = { entity: string; amount_field: string; threshold: string; approvals_over: number; approvals_default: number };

export type KpiView = { type: 'kpi'; id: string; title: string; tiles: { label: string; expr: string; format: ComputedType }[] };
export type BudgetTableView = {
  type: 'budget_table'; id: string; title: string; entity: string;
  label_field: string; budget_field: string; approved_field: string; pending_field: string; remaining_field: string; warn_at: string;
};
export type RecordTableView = { type: 'record_table'; id: string; title: string; entity: string; columns: string[] };
export type FormView = { type: 'form'; id: string; title: string; entity: string; fields: string[] };
export type ApprovalQueueView = { type: 'approval_queue'; id: string; title: string; entity: string };
export type View = KpiView | BudgetTableView | RecordTableView | FormView | ApprovalQueueView;

export type AppSpec = { name: string; description?: string | null; entities: Entity[]; approval_rule?: ApprovalRule | null; views: View[] };

/** One logged change to a budget line's amount (saved apps). */
export type FundEntry = { amount: string; note: string; by: string; at: string };

export type Row = Record<string, unknown> & {
  __state__?: string;
  __funds__?: FundEntry[];
  __approved_by__?: string[];
  /** Saved apps only: record id, whether I created it, and why I can't approve it (null = I can). */
  __id__?: string;
  __mine__?: boolean;
  __blocked__?: string | null;
};

export type Role = 'admin' | 'approver' | 'submitter';

export type DemoResponse = {
  file_name: string;
  seconds: number;
  source: 'ai' | 'cache' | 'fallback' | 'saved';
  model?: string;
  spec: AppSpec;
  rows: Record<string, Row[]>;
  kpis: Record<string, string | null>;
  warnings: string[];
};

/** GET /apps/{id}/view (backend/app/routes/apps.py). */
export type AppView = {
  app_id: string;
  role: Role;
  file_name: string;
  created_at: string;
  spec: AppSpec;
  rows: Record<string, Row[]>;
  kpis: Record<string, string | null>;
};

export type MyApp = { id: string; name: string; role: Role; created_at: string };
export type Me = { id: string; email: string | null; name: string | null; apps: MyApp[] };
export type Member = { id: string; name: string | null; email: string | null; role: Role };
