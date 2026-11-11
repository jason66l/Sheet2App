import './importPanel.css';
import type { ImportState } from './types';

type Props = {
  state: ImportState;
  onConfirm: () => void;
  onClose: () => void;
};

/**
 * Temporary result panel for an upload. Shows what run_import() found.
 * The full review screen (weeks 7-8) replaces this.
 */
export default function ImportPanel({ state, onConfirm, onClose }: Props) {
  if (state.phase === 'idle') return null;

  return (
    <div className="s2a import-backdrop" role="dialog" aria-modal="true" aria-labelledby="import-title">
      <div className="import-panel">
        <div className="import-head">
          <h2 id="import-title">
            {state.phase === 'uploading' && 'Reading your spreadsheet…'}
            {state.phase === 'error' && 'Upload failed'}
            {(state.phase === 'ready' || state.phase === 'confirming') && 'Here’s what we found'}
            {state.phase === 'confirmed' && 'Your app is ready'}
          </h2>
          {state.phase !== 'uploading' && (
            <button type="button" className="text-button" onClick={onClose}>
              Close
            </button>
          )}
        </div>

        {state.phase === 'uploading' && <p className="muted">{state.fileName}</p>}

        {state.phase === 'error' && (
          <p className="import-error" role="alert">
            {state.message}
          </p>
        )}

        {'data' in state && state.data.status === 'failed' && (
          <p className="import-error" role="alert">
            {state.data.error ?? 'Something went wrong while reading the file.'}
          </p>
        )}

        {'data' in state && state.data.proposal && (
          <>
            <dl className="import-facts">
              <div>
                <dt>File</dt>
                <dd>{state.data.file_name}</dd>
              </div>
              <div>
                <dt>App name</dt>
                <dd>{state.data.proposal.name}</dd>
              </div>
              <div>
                <dt>Tables</dt>
                <dd>{state.data.proposal.entities.map((e) => e.name).join(', ')}</dd>
              </div>
              {state.data.reconciliation && (
                <div>
                  <dt>Formulas</dt>
                  <dd>
                    {state.data.reconciliation.formulas_translated > 0
                      ? `${state.data.reconciliation.matched} of ${state.data.reconciliation.formulas_total} match your file`
                      : `${state.data.reconciliation.formulas_total} formulas found`}
                  </dd>
                </div>
              )}
            </dl>
            {state.data.warnings.length > 0 && (
              <ul className="import-warnings">
                {state.data.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}
          </>
        )}

        {state.phase === 'ready' && state.data.status === 'ready' && (
          <div className="import-actions">
            <button type="button" className="btn btn-primary" onClick={onConfirm}>
              Create app
            </button>
          </div>
        )}
        {state.phase === 'confirming' && <p className="muted">Creating your app…</p>}
        {state.phase === 'confirmed' && (
          <p>
            Created with {state.records} records. App id <span className="mono">{state.appId}</span>.
          </p>
        )}
      </div>
    </div>
  );
}
