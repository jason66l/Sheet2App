import {
  BUDGET_LINES,
  PENDING_REQUESTS,
  TOTALS,
  TOTAL_LEFT,
  money,
  plain,
  remaining,
  percent,
} from './data';

/** Small bracketed reference that ties a spreadsheet cell to the app element it became. */
function Ref({ n }: { n: number }) {
  return (
    <span className="ref mono" aria-label={`reference ${n}`}>
      [{n}]
    </span>
  );
}

function SpreadsheetPane() {
  return (
    <div className="pane pane-source">
      <div className="pane-head">
        <span className="eyebrow">Source</span>
        <span className="pane-file mono">Event_Budget_2026.xlsx</span>
      </div>

      <div className="formula-bar mono" aria-hidden="true">
        <span className="formula-cell">E6</span>
        <span className="formula-fx">fx</span>
        <span className="formula-text">=B6-C6-D6</span>
      </div>

      <div className="sheet-scroll">
        <table className="sheet">
          <caption className="sr-only">Budget tab of the source spreadsheet</caption>
          <thead>
            <tr>
              <th scope="col" className="rowhead" />
              <th scope="col">A</th>
              <th scope="col">B</th>
              <th scope="col">C</th>
              <th scope="col">D</th>
              <th scope="col" className="col-hl">E</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row" className="rowhead">1</th>
              <td colSpan={5} className="sheet-title">Spring Showcase 2026 – Budget</td>
            </tr>
            <tr>
              <th scope="row" className="rowhead">2</th>
              <td colSpan={5} />
            </tr>
            <tr className="sheet-header">
              <th scope="row" className="rowhead">3</th>
              <td>Line</td>
              <td className="num">Budget</td>
              <td className="num">Approved</td>
              <td className="num">Pending</td>
              <td className="num col-hl">
                Remaining <Ref n={1} />
              </td>
            </tr>
            {BUDGET_LINES.map((l, i) => {
              const row = i + 4;
              return (
                <tr key={l.name}>
                  <th scope="row" className="rowhead">{row}</th>
                  <td>{l.name}</td>
                  <td className="num">{plain(l.budget)}</td>
                  <td className="num">{plain(l.approved)}</td>
                  <td className="num">{plain(l.pending)}</td>
                  <td className={`num col-hl${row === 6 ? ' cell-selected' : ''}`}>
                    {plain(remaining(l))}
                  </td>
                </tr>
              );
            })}
            <tr className="sheet-total">
              <th scope="row" className="rowhead">10</th>
              <td>Total</td>
              <td className="num">{plain(TOTALS.budget)}</td>
              <td className="num">{plain(TOTALS.approved)}</td>
              <td className="num">{plain(TOTALS.pending)}</td>
              <td className="num col-hl">{plain(TOTAL_LEFT)}</td>
            </tr>
            <tr>
              <th scope="row" className="rowhead">11</th>
              <td colSpan={5} />
            </tr>
            <tr>
              <th scope="row" className="rowhead">12</th>
              <td colSpan={5} className="sheet-note">
                Purchases over $200 need 2 signatures <Ref n={2} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="sheet-tabs" aria-hidden="true">
        <span className="is-active">Budget</span>
        <span>
          Expenses <Ref n={3} />
        </span>
        <span>Members</span>
      </div>
    </div>
  );
}

function AppPane() {
  return (
    <div className="pane pane-app">
      <div className="pane-head">
        <span className="eyebrow">Generated app</span>
        <span className="pane-file">Spring Showcase Budget</span>
      </div>

      <div className="app-body">
        <dl className="kpis">
          <div className="kpi">
            <dt>Budget</dt>
            <dd>{money(TOTALS.budget)}</dd>
          </div>
          <div className="kpi">
            <dt>Approved</dt>
            <dd>{money(TOTALS.approved)}</dd>
          </div>
          <div className="kpi">
            <dt>Pending</dt>
            <dd>{money(TOTALS.pending)}</dd>
          </div>
          <div className="kpi">
            <dt>
              Left <Ref n={1} />
            </dt>
            <dd>{money(TOTAL_LEFT)}</dd>
          </div>
        </dl>

        <table className="lines">
          <caption className="sr-only">Budget by line</caption>
          <thead>
            <tr>
              <th scope="col">Line</th>
              <th scope="col">Committed</th>
              <th scope="col" className="num">Left</th>
            </tr>
          </thead>
          <tbody>
            {BUDGET_LINES.map((l) => {
              const a = (l.approved / l.budget) * 100;
              const p = (l.pending / l.budget) * 100;
              return (
                <tr key={l.name}>
                  <td>{l.name}</td>
                  <td>
                    <div className="bar-row">
                      <div
                        className="bar"
                        role="img"
                        aria-label={`${Math.round(a)}% approved, ${Math.round(p)}% pending`}
                      >
                        <span className="bar-approved" style={{ width: `${a}%` }} />
                        <span className="bar-pending" style={{ width: `${p}%` }} />
                      </div>
                      <span className="bar-pct mono">{percent(l.approved + l.pending, l.budget)}%</span>
                    </div>
                  </td>
                  <td className="num">{money(remaining(l))}</td>
                </tr>
              );
            })}
          </tbody>
        </table>

        <div className="queue">
          <div className="queue-head">
            <span>
              Needs approval <Ref n={3} />
            </span>
            <span className="queue-rule">
              2 approvals over $200 <Ref n={2} />
            </span>
          </div>
          <ul>
            {PENDING_REQUESTS.map((r) => (
              <li key={r.id}>
                <div className="queue-main">
                  <span className="queue-title">{r.title}</span>
                  <span className="queue-meta">
                    {r.submittedBy} · {r.line}
                  </span>
                </div>
                <span className="queue-amount">{money(r.amount)}</span>
                <span className="queue-count mono">
                  {r.approvals}/{r.required}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function ProductPreview() {
  return (
    <figure className="preview">
      <div className="frame">
        <div className="frame-bar mono">sheet2app.com/westview-robotics/spring-showcase</div>
        <div className="frame-body">
          <SpreadsheetPane />
          <AppPane />
        </div>
      </div>
      <figcaption className="legend">
        <p>
          <Ref n={1} /> The Remaining formula <span className="mono">=B−C−D</span> becomes the Left column,
          recalculated in code on every change.
        </p>
        <p>
          <Ref n={2} /> A note typed in row 12 becomes an approval rule: 2 different people over $200.
        </p>
        <p>
          <Ref n={3} /> The Expenses tab's Status column becomes the approval workflow.
        </p>
      </figcaption>
    </figure>
  );
}
