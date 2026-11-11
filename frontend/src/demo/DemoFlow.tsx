import { useState } from 'react';
import Landing from '../landing/Landing';
import Analyzing from './Analyzing';
import GeneratedApp from './GeneratedApp';
import { demoImport } from './api';
import type { DemoResponse } from './types';

/**
 * Demo mode (VITE_DEMO_MODE=true): no sign-in, nothing saved.
 * Talks to backend/demo_server.py.
 */
type Phase =
  | { kind: 'home' }
  | { kind: 'analyzing'; fileName: string; error?: string }
  | { kind: 'app'; data: DemoResponse };

export default function DemoFlow() {
  const [phase, setPhase] = useState<Phase>({ kind: 'home' });

  const onUpload = async (file: File) => {
    setPhase({ kind: 'analyzing', fileName: file.name });
    try {
      const data = await demoImport(file);
      setPhase({ kind: 'app', data });
      window.scrollTo(0, 0);
    } catch (err) {
      setPhase({ kind: 'analyzing', fileName: file.name, error: err instanceof Error ? err.message : String(err) });
    }
  };

  if (phase.kind === 'app') {
    return <GeneratedApp data={phase.data} onBack={() => setPhase({ kind: 'home' })} />;
  }
  return (
    <>
      <Landing onUpload={onUpload} />
      {phase.kind === 'analyzing' && (
        <Analyzing fileName={phase.fileName} error={phase.error} onCancel={() => setPhase({ kind: 'home' })} />
      )}
    </>
  );
}
