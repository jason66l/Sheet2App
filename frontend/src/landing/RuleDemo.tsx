import { useId, useState, type FormEvent } from 'react';

type ScenarioKey = 'approvals' | 'warning' | 'vendor';

type Scenario = {
  prompt: string;
  area: string;
  summary: string;
  before: string[];
  after: string[];
  impact: string[];
};

const SCENARIOS: Record<ScenarioKey, Scenario> = {
  approvals: {
    prompt: 'Require two approvals for purchases over $200',
    area: 'Approval rule',
    summary: 'Expenses over $200.00 will need approval from 2 different people.',
    before: ['1 approval for any amount'],
    after: ['1 approval up to $200.00', '2 approvals over $200.00, from different people'],
    impact: [
      'Servo motors (6), $372.00: now needs 2 approvals',
      'Pizza for build night, $240.00: needs 1 more approval',
    ],
  },
  warning: {
    prompt: 'Warn me when a budget line is 90% spent',
    area: 'Budget warning',
    summary: 'The dashboard will warn when approved plus pending spending reaches 90% of a line.',
    before: ['Warn at 85% committed'],
    after: ['Warn at 90% committed'],
    impact: ['Supplies & parts (88%) no longer shows a warning'],
  },
  vendor: {
    prompt: 'Add a Vendor field to expenses',
    area: 'Expense form',
    summary: 'Expenses get an optional Vendor field after Description.',
    before: ['Date, Description, Budget line, Amount, Receipt'],
    after: ['Date, Description, Vendor, Budget line, Amount, Receipt'],
    impact: ['11 existing expenses get an empty Vendor', 'The expense form shows Vendor as optional'],
  },
};

const EXAMPLES: ScenarioKey[] = ['approvals', 'warning', 'vendor'];

/** Stand-in for the backend's propose_edit(): maps a request to a known change. */
function classify(text: string): ScenarioKey | null {
  const t = text.toLowerCase();
  if (t.includes('vendor')) return 'vendor';
  if (/(warn|alert|notify)/.test(t) || /\d+\s*%/.test(t)) return 'warning';
  if (t.includes('approv')) return 'approvals';
  return null;
}

type State =
  | { phase: 'idle'; note?: string }
  | { phase: 'proposed'; key: ScenarioKey; sent: string }
  | { phase: 'applied'; key: ScenarioKey; sent: string }
  | { phase: 'unknown'; sent: string };

export default function RuleDemo() {
  const [draft, setDraft] = useState('');
  const [state, setState] = useState<State>({ phase: 'idle' });
  const inputId = useId();

  const propose = (text: string) => {
    const sent = text.trim();
    if (!sent) return;
    const key = classify(sent);
    setState(key ? { phase: 'proposed', key, sent } : { phase: 'unknown', sent });
    setDraft('');
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    propose(draft);
  };

  const scenario = 'key' in state ? SCENARIOS[state.key] : null;
  const busy = state.phase === 'proposed';

  return (
    <div className="console">
      <div className="console-head">
        <span>Spring Showcase Budget</span>
        <span className="console-sub">Change this app</span>
      </div>

      <div className="console-body" aria-live="polite">
        {state.phase === 'idle' && (
          <div className="console-empty">
            <p>Describe a change in your own words. Nothing goes live until you confirm it.</p>
            {state.note && <p className="console-note">{state.note}</p>}
          </div>
        )}

        {'sent' in state && <p className="msg-user">{state.sent}</p>}

        {state.phase === 'unknown' && (
          <div className="proposal">
            <p className="proposal-summary">
              I can change fields, approval rules and budget warnings. Which one did you mean? Try one of the
              examples below.
            </p>
          </div>
        )}

        {scenario && (
          <div className={`proposal${state.phase === 'applied' ? ' is-applied' : ''}`}>
            <div className="proposal-head">
              <span className="eyebrow">{scenario.area}</span>
              {state.phase === 'applied' && <span className="proposal-live">Live</span>}
            </div>
            <p className="proposal-summary">{scenario.summary}</p>

            <div className="diff mono" role="group" aria-label="Before and after">
              {scenario.before.map((b) => (
                <div className="diff-row diff-del" key={b}>
                  <span aria-hidden="true">−</span>
                  <span>
                    <span className="sr-only">Before: </span>
                    {b}
                  </span>
                </div>
              ))}
              {scenario.after.map((a) => (
                <div className="diff-row diff-add" key={a}>
                  <span aria-hidden="true">+</span>
                  <span>
                    <span className="sr-only">After: </span>
                    {a}
                  </span>
                </div>
              ))}
            </div>

            <div className="impact">
              <span className="impact-label">Affects</span>
              <ul>
                {scenario.impact.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            </div>

            {state.phase === 'proposed' && (
              <div className="proposal-actions">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => setState({ phase: 'applied', key: state.key, sent: state.sent })}
                >
                  Confirm change
                </button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setState({ phase: 'idle' })}>
                  Cancel
                </button>
              </div>
            )}

            {state.phase === 'applied' && (
              <div className="proposal-actions">
                <span className="applied-text">Applied for everyone in this app.</span>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setState({ phase: 'idle', note: 'Change undone. The previous version is back.' })}
                >
                  Undo
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <form className="console-form" onSubmit={onSubmit}>
        <label htmlFor={inputId} className="sr-only">
          Describe a change
        </label>
        <input
          id={inputId}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="e.g. Require two approvals for purchases over $200"
          autoComplete="off"
          disabled={busy}
        />
        <button type="submit" className="btn btn-primary" disabled={busy || !draft.trim()}>
          Preview
        </button>
      </form>

      <div className="console-examples">
        <span>Try</span>
        {EXAMPLES.map((k) => (
          <button key={k} type="button" className="example" onClick={() => propose(SCENARIOS[k].prompt)} disabled={busy}>
            {SCENARIOS[k].prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
