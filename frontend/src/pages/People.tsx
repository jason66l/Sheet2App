import { useCallback, useEffect, useState } from 'react';
import type { Member, Role } from '../demo/types';
import { api } from '../lib/api';

const ROLES: Role[] = ['submitter', 'approver', 'admin'];
const ROLE_LABEL: Record<Role, string> = { admin: 'Admin', approver: 'Approver', submitter: 'Submitter' };

type Props = { appId: string; myRole: Role; myId?: string };

/** Members of an app. Admins can invite people by link and change roles. */
export default function People({ appId, myRole, myId }: Props) {
  const [members, setMembers] = useState<Member[]>([]);
  const [inviteRole, setInviteRole] = useState<Role>('submitter');
  const [link, setLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = myRole === 'admin';

  const load = useCallback(() => {
    api<Member[]>(`/apps/${appId}/members`).then(setMembers).catch((e) => setError(String(e.message ?? e)));
  }, [appId]);

  useEffect(load, [load]);

  const createLink = async () => {
    setError(null);
    try {
      const res = await api<{ token: string }>(`/apps/${appId}/invites`, {
        method: 'POST',
        body: JSON.stringify({ role: inviteRole }),
      });
      setLink(`${window.location.origin}${window.location.pathname}#/join/${res.token}`);
      setCopied(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const changeRole = async (id: string, role: Role) => {
    setError(null);
    try {
      await api(`/apps/${appId}/members/${id}`, { method: 'PATCH', body: JSON.stringify({ role }) });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <section className="gen-block gen-card gen-span-12" aria-labelledby="people-h">
      <div className="gen-card-head">
        <h2 id="people-h">People</h2>
        <span className="muted">{members.length} members</span>
      </div>
      {error && <p className="gen-alert" role="alert" style={{ margin: 16 }}>{error}</p>}
      <ul className="gen-people">
        {members.map((m) => (
          <li key={m.id}>
            <span>
              {m.name ?? m.email ?? 'Member'}
              {m.id === myId && ' (you)'}
              <span className="muted">{m.email}</span>
            </span>
            {isAdmin && m.id !== myId ? (
              <select aria-label={`Role for ${m.name ?? m.email}`} value={m.role} onChange={(e) => void changeRole(m.id, e.target.value as Role)}>
                {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </select>
            ) : (
              <span className={`gen-role gen-role-${m.role}`}>{ROLE_LABEL[m.role]}</span>
            )}
          </li>
        ))}
      </ul>
      {isAdmin && (
        <div className="gen-invite">
          <label htmlFor="invite-role">Invite as</label>
          <select id="invite-role" value={inviteRole} onChange={(e) => setInviteRole(e.target.value as Role)}>
            {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
          </select>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void createLink()}>
            Create invite link
          </button>
          {link && (
            <>
              <input className="gen-invite-link" readOnly value={link} aria-label="Invite link" onFocus={(e) => e.target.select()} />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void navigator.clipboard.writeText(link).then(() => setCopied(true))}
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}
