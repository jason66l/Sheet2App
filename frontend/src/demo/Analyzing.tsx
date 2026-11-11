import './demo.css';
import { useEffect, useState } from 'react';

type Props = {
  fileName: string;
  error?: string | null;
  onCancel: () => void;
};

const STEPS = [
  { at: 0, text: 'Reading your spreadsheet' },
  { at: 2, text: 'Finding tables, formulas and rules' },
  { at: 5, text: 'Designing your app' },
];

/** Full-screen progress while the AI designs the app (can take a minute or more). */
export default function Analyzing({ fileName, error, onCancel }: Props) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (error) return;
    const start = Date.now();
    const t = setInterval(() => setSeconds(Math.floor((Date.now() - start) / 1000)), 250);
    return () => clearInterval(t);
  }, [error]);

  const current = STEPS.filter((s) => seconds >= s.at).length - 1;

  return (
    <div className="s2a gen-analyzing" role="dialog" aria-modal="true" aria-labelledby="analyzing-title">
      <div className="gen-analyzing-panel">
        <p className="eyebrow">{fileName}</p>
        {error ? (
          <>
            <h2 id="analyzing-title">Something went wrong</h2>
            <p className="gen-error" role="alert">
              {error}
            </p>
            <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel}>
              Back
            </button>
          </>
        ) : (
          <>
            <h2 id="analyzing-title">Building your app…</h2>
            <ol className="gen-steps" aria-live="polite">
              {STEPS.map((s, i) => (
                <li key={s.text} className={i < current ? 'is-done' : i === current ? 'is-active' : ''}>
                  <span className="gen-step-dot" aria-hidden="true" />
                  {s.text}
                  {i === current && i === STEPS.length - 1 && <span className="mono muted"> {seconds}s</span>}
                </li>
              ))}
            </ol>
            <div className="gen-progress" aria-hidden="true">
              <span />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
