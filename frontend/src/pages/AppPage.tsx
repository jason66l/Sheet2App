import { useCallback, useEffect, useState } from 'react';
import GeneratedApp, { type AppActions } from '../demo/GeneratedApp';
import type { AppView, DemoResponse } from '../demo/types';
import { api } from '../lib/api';
import People from './People';

type Props = { appId: string; myId?: string };

/** A saved app, loaded from the database. Every action saves, then the page reloads the data. */
export default function AppPage({ appId, myId }: Props) {
  const [view, setView] = useState<AppView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setView(await api<AppView>(`/apps/${appId}/view`));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [appId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <div className="s2a center-page">
        <div>
          <h1>Can't open this app</h1>
          <p>{error}</p>
          <a className="btn btn-secondary btn-sm" href="#/">Back to my apps</a>
        </div>
      </div>
    );
  }
  if (!view) return <div className="s2a center-page"><p>Loading…</p></div>;

  const actions: AppActions = {
    approve: async (id) => {
      await api(`/records/${id}/approve`, { method: 'POST' });
      await load();
    },
    reject: async (id) => {
      await api(`/records/${id}/reject`, { method: 'POST' });
      await load();
    },
    create: async (entity, data) => {
      await api(`/apps/${appId}/records`, { method: 'POST', body: JSON.stringify({ entity, data }) });
      await load();
    },
  };

  const data: DemoResponse = {
    file_name: view.file_name,
    seconds: 0,
    source: 'saved',
    spec: view.spec,
    rows: view.rows,
    kpis: view.kpis,
    warnings: [],
  };

  return (
    <GeneratedApp
      data={data}
      role={view.role}
      actions={actions}
      onBack={() => (window.location.hash = '#/')}
      backLabel="My apps"
      extra={<People appId={appId} myRole={view.role} myId={myId} />}
    />
  );
}
