import '../landing/landing.css';
import './demo.css';
import { useMemo, useState, type FormEvent } from 'react';
import type {
  ApprovalQueueView, AppSpec, BudgetTableView, DemoResponse, Entity, FormView, KpiView, RecordTableView, Row, View,
} from './types';
import { STATE_LABEL, cell, column, money, num, percent } from './format';

type Rows = Record<string, Row[]>;

type Props = {
  data: DemoResponse;
  onBack: () => void;
};

/**
 * Renders any generated app from its AppSpec. Nothing here knows about budgets
 * or clubs: every table, column, rule and form comes from data.spec.
 * Approvals and new expenses change local state only (demo; nothing is saved).
 */
export default function GeneratedApp({ data, onBack }: Props) {
  const { spec } = data;
  const [rows, setRows] = useState<Rows>(data.rows);
  const entity = (name: string) => spec.entities.find((e) => e.name === name);

  const updateRow = (entityName: string, index: number, patch: Partial<Row>) =>
    setRows((r) => ({ ...r, [entityName]: r[entityName].map((row, i) => (i === index ? { ...row, ...patch } : row)) }));

  const addRow = (entityName: string, row: Row) =>
    setRows((r) => ({ ...r, [entityName]: [...(r[entityName] ?? []), row] }));

  const sourceLabel =
    data.source === 'fallback'
      ? 'Sample app (AI step failed)'
      : `Designed by ${data.model ?? 'AI'}${data.source === 'cache' ? ' · saved result' : ''}`;

  return (
    <div className="s2a gen">
      <header className="gen-bar">
        <div className="container gen-bar-inner">
          <div className="gen-title">
            <span className="gen-mark" aria-hidden="true">
              {initials(spec.name)}
            </span>
            <div>
              <h1>{spec.name}</h1>
              {spec.description && <p>{spec.description}</p>}
            </div>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onBack}>
            New upload
          </button>
        </div>
      </header>

      <div className="container">
        <p className="gen-source">
          <span className={`gen-dot gen-dot-${data.source}`} aria-hidden="true" />
          {sourceLabel} from <strong>{data.file_name}</strong>
          {data.source === 'ai' && <> in {Math.round(data.seconds)}s</>}
          <span className="gen-source-meta">
            {spec.entities.map((e) => `${(rows[e.name] ?? []).length} ${e.label.toLowerCase()}`).join(' · ')}
          </span>
        </p>

        <main className="gen-grid">
          {spec.views.map((view) => (
            <ViewBlock key={view.id} view={view} spec={spec} data={data} rows={rows} entity={entity} updateRow={updateRow} addRow={addRow} />
          ))}
        </main>
      </div>
    </div>
  );
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter((w) => /^[A-Za-z]/.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');
}

type BlockProps = {
  view: View;
  spec: AppSpec;
  data: DemoResponse;
  rows: Rows;
  entity: (name: string) => Entity | undefined;
  updateRow: (entity: string, index: number, patch: Partial<Row>) => void;
  addRow: (entity: string, row: Row) => void;
};

function ViewBlock(props: BlockProps) {
  const { view } = props;
  switch (view.type) {
    case 'kpi':
      return <Kpis view={view} kpis={props.data.kpis} />;
    case 'budget_table':
      return <BudgetTable {...props} view={view} />;
    case 'approval_queue':
      return <ApprovalQueue {...props} view={view} />;
    case 'record_table':
      return <RecordTable {...props} view={view} />;
    case 'form':
      return <EntityForm {...props} view={view} />;
    default:
      return null;
  }
}

/* ---------------------------------------------------------------- KPI tiles */

function Kpis({ view, kpis }: { view: KpiView; kpis: Record<string, string | null> }) {
  return (
    <section className="gen-block gen-span-12" aria-label={view.title}>
      <dl className="gen-kpis">
        {view.tiles.map((t) => {
          const v = kpis[`${view.id}/${t.label}`];
          const shown = v == null ? '—' : t.format === 'percent' ? percent(v) : t.format === 'money' ? money(v) : num(v).toLocaleString();
          return (
            <div key={t.label} className="gen-kpi">
              <dt>{t.label}</dt>
              <dd>{shown}</dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}

/* ------------------------------------------------------------- budget table */

function BudgetTable({ view, rows, entity }: BlockProps & { view: BudgetTableView }) {
  const ent = entity(view.entity);
  if (!ent) return null;
  const warnAt = num(view.warn_at);
  return (
    <section className="gen-block gen-card gen-span-12" aria-labelledby={`${view.id}-h`}>
      <div className="gen-card-head">
        <h2 id={`${view.id}-h`}>{view.title}</h2>
        <div className="gen-legend">
          <span><i className="swatch swatch-approved" /> Approved</span>
          <span><i className="swatch swatch-pending" /> Pending</span>
        </div>
      </div>
      <div className="gen-scroll">
        <table className="gen-table gen-budget">
          <thead>
            <tr>
              <th>{column(ent, view.label_field)?.label ?? 'Line'}</th>
              <th className="num">{column(ent, view.budget_field)?.label ?? 'Budget'}</th>
              <th className="wide">Committed</th>
              <th className="num">{column(ent, view.remaining_field)?.label ?? 'Left'}</th>
            </tr>
          </thead>
          <tbody>
            {(rows[view.entity] ?? []).map((r, i) => {
              const budget = num(r[view.budget_field]);
              const a = num(r[view.approved_field]);
              const p = num(r[view.pending_field]);
              const used = budget ? (a + p) / budget : 0;
              const warn = used >= warnAt && used < 1;
              return (
                <tr key={i} className={warn ? 'is-warning' : ''}>
                  <td>
                    {String(r[view.label_field] ?? '')}
                    {warn && <span className="warn-text"> · {Math.round(used * 100)}% committed</span>}
                  </td>
                  <td className="num">{money(budget)}</td>
                  <td className="wide">
                    <div className="bar-row">
                      <div className="bar" role="img" aria-label={`${Math.round((a / (budget || 1)) * 100)}% approved, ${Math.round((p / (budget || 1)) * 100)}% pending`}>
                        <span className="bar-approved" style={{ width: `${Math.min(100, (a / (budget || 1)) * 100)}%` }} />
                        <span className="bar-pending" style={{ width: `${Math.min(100, (p / (budget || 1)) * 100)}%` }} />
                      </div>
                      <span className="bar-pct mono">{Math.round(used * 100)}%</span>
                    </div>
                  </td>
                  <td className="num gen-strong">{money(r[view.remaining_field])}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* ----------------------------------------------------------- approval queue */

function ApprovalQueue({ view, spec, rows, entity, updateRow }: BlockProps & { view: ApprovalQueueView }) {
  const ent = entity(view.entity);
  if (!ent) return null;
  const rule = spec.approval_rule?.entity === view.entity ? spec.approval_rule : null;
  const amountField = rule?.amount_field ?? ent.fields.find((f) => f.type === 'money')?.name;
  const who = ent.fields.find((f) => f.type === 'user')?.name;
  const pending = (rows[view.entity] ?? []).map((r, i) => ({ r, i })).filter(({ r }) => r.__state__ === 'submitted');

  const approve = (i: number, r: Row) => {
    const given = [...(r.__approved_by__ ?? []), 'You'];
    const needed = required(r);
    updateRow(view.entity, i, { __approved_by__: given, ...(given.length >= needed ? { __state__: 'approved' } : {}) });
  };
  const required = (r: Row) =>
    rule ? (num(r[rule.amount_field]) > num(rule.threshold) ? rule.approvals_over : rule.approvals_default) : 1;

  return (
    <section className="gen-block gen-card gen-span-7" aria-labelledby={`${view.id}-h`}>
      <div className="gen-card-head">
        <h2 id={`${view.id}-h`}>{view.title}</h2>
        {rule && (
          <span className="gen-rule">
            {rule.approvals_over} approvals over {money(rule.threshold)}
          </span>
        )}
      </div>
      {pending.length === 0 ? (
        <p className="gen-empty">Nothing waiting. New requests show up here.</p>
      ) : (
        <ul className="gen-queue">
          {pending.map(({ r, i }) => {
            const given = (r.__approved_by__ ?? []).length;
            const needed = required(r);
            return (
              <li key={i}>
                <div className="gen-queue-top">
                  <div>
                    <span className="gen-queue-title">{String(r[ent.display_field] ?? 'Request')}</span>
                    <span className="gen-queue-meta">
                      {[who && r[who], ...ent.fields.filter((f) => f.type === 'ref').map((f) => r[f.name])].filter(Boolean).join(' · ')}
                    </span>
                  </div>
                  {amountField && <span className="gen-queue-amount">{money(r[amountField])}</span>}
                </div>
                <div className="approvals-track">
                  {Array.from({ length: needed }, (_, k) => (
                    <span key={k} className={k < given ? 'is-done' : ''} />
                  ))}
                  <span className="muted">
                    {given} of {needed} {needed === 1 ? 'approval' : 'approvals'}{given ? ` · ${(r.__approved_by__ ?? []).join(', ')}` : ''}
                  </span>
                </div>
                <div className="gen-queue-actions">
                  <button type="button" className="btn btn-primary btn-sm" onClick={() => approve(i, r)}>
                    Approve
                  </button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => updateRow(view.entity, i, { __state__: 'rejected' })}>
                    Reject
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/* ------------------------------------------------------------- record table */

function RecordTable({ view, rows, entity }: BlockProps & { view: RecordTableView }) {
  const ent = entity(view.entity);
  if (!ent) return null;
  const list = rows[view.entity] ?? [];
  return (
    <section className="gen-block gen-card gen-span-12" aria-labelledby={`${view.id}-h`}>
      <div className="gen-card-head">
        <h2 id={`${view.id}-h`}>{view.title}</h2>
        <span className="muted">{list.length} rows</span>
      </div>
      <div className="gen-scroll">
        <table className="gen-table">
          <thead>
            <tr>
              {view.columns.map((c) => {
                const col = column(ent, c);
                return (
                  <th key={c} className={col?.type === 'money' || col?.type === 'number' ? 'num' : ''}>
                    {col?.label ?? c}
                  </th>
                );
              })}
              {ent.workflow && <th>Status</th>}
            </tr>
          </thead>
          <tbody>
            {[...list].reverse().map((r, i) => (
              <tr key={i}>
                {view.columns.map((c) => {
                  const col = column(ent, c);
                  return (
                    <td key={c} className={col?.type === 'money' || col?.type === 'number' ? 'num' : col?.type === 'file' ? 'gen-file' : ''}>
                      {cell(ent, c, r[c])}
                    </td>
                  );
                })}
                {ent.workflow && (
                  <td>
                    <span className={`gen-state gen-state-${r.__state__ ?? 'draft'}`}>{STATE_LABEL[r.__state__ ?? 'draft'] ?? r.__state__}</span>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* --------------------------------------------------------------------- form */

function EntityForm({ view, rows, entity, addRow }: BlockProps & { view: FormView }) {
  const ent = entity(view.entity);
  const [values, setValues] = useState<Record<string, string>>({});
  const [done, setDone] = useState(false);
  const fields = useMemo(() => (ent ? view.fields.map((n) => ent.fields.find((f) => f.name === n)).filter(Boolean) : []), [ent, view.fields]);
  if (!ent) return null;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const row: Row = { ...values, __state__: ent.workflow ? 'submitted' : undefined, __approved_by__: [] };
    const who = ent.fields.find((f) => f.type === 'user');
    if (who && !row[who.name]) row[who.name] = 'You';
    addRow(view.entity, row);
    setValues({});
    setDone(true);
  };

  return (
    <section className="gen-block gen-card gen-span-5" aria-labelledby={`${view.id}-h`}>
      <div className="gen-card-head">
        <h2 id={`${view.id}-h`}>{view.title}</h2>
      </div>
      <form className="gen-form" onSubmit={submit}>
        {fields.map((f) => {
          if (!f) return null;
          const id = `${view.id}-${f.name}`;
          const set = (v: string) => {
            setDone(false);
            setValues((s) => ({ ...s, [f.name]: v }));
          };
          const v = values[f.name] ?? '';
          let input;
          if (f.type === 'enum' && f.options) {
            input = (
              <select id={id} value={v} onChange={(e) => set(e.target.value)} required={f.required}>
                <option value="">Choose…</option>
                {f.options.map((o) => <option key={o}>{o}</option>)}
              </select>
            );
          } else if (f.type === 'ref' && f.ref_entity) {
            const target = entity(f.ref_entity);
            const opts = (rows[f.ref_entity] ?? []).map((r) => String(r[target?.display_field ?? ''] ?? '')).filter(Boolean);
            input = (
              <select id={id} value={v} onChange={(e) => set(e.target.value)} required={f.required}>
                <option value="">Choose…</option>
                {opts.map((o) => <option key={o}>{o}</option>)}
              </select>
            );
          } else if (f.type === 'file') {
            input = <input id={id} type="file" onChange={(e) => set(e.target.files?.[0]?.name ?? '')} />;
          } else {
            const type = f.type === 'date' ? 'date' : f.type === 'money' || f.type === 'number' ? 'number' : 'text';
            input = (
              <input
                id={id}
                type={type}
                step={f.type === 'money' ? '0.01' : undefined}
                min={f.type === 'money' ? '0' : undefined}
                value={v}
                onChange={(e) => set(e.target.value)}
                required={f.required}
              />
            );
          }
          return (
            <div key={f.name} className="gen-field">
              <label htmlFor={id}>
                {f.label}
                {f.required && <span aria-hidden="true"> *</span>}
              </label>
              {input}
            </div>
          );
        })}
        <div className="gen-form-foot">
          {done ? <span className="gen-ok" role="status">Submitted. It’s in the approval queue.</span> : <span />}
          <button type="submit" className="btn btn-primary btn-sm">
            Submit
          </button>
        </div>
      </form>
    </section>
  );
}
