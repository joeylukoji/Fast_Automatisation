import { useEffect, useState } from 'react';
import { api } from '../api';
import Icon from '../icons.jsx';

// Atelier : l'utilisateur décrit son business, Gemma personnalise les 4 apps (docs/app-builder-contract.md).
export const BUILD_APPS = [
  { app: 'caisse', title: 'Caisse', icon: 'trigger_erp_sale' },
  { app: 'clients', title: 'Clients', icon: 'erp_customer_lookup' },
  { app: 'ventes', title: 'Ventes & factures', icon: 'invoice_render' },
  { app: 'automatisation', title: 'Automatisation', icon: 'bolt' },
];

const EXAMPLES = [
  { label: 'Pharmacie · Lubumbashi', text: "Pharmacie de quartier à Lubumbashi : médicaments génériques, paracétamol, sirops, antipaludiques. Clients fidèles suivis par quartier et numéro d'assuré. Couleurs vert santé." },
  { label: 'Quincaillerie · Goma', text: 'Quincaillerie à Goma : ciment, tôles, clous, peinture, outillage. Clients artisans et entreprises de construction, suivis par chantier. Style robuste, orange chantier.' },
  { label: 'Pagnes · Kinshasa', text: 'Boutique de pagnes wax et super-wax au marché central de Kinshasa : pièces de 6 yards, tissus Vlisco, couture sur mesure. Clientes suivies par commune. Couleurs chaudes et élégantes.' },
];

const SOURCE = { gemma: 'Gemma', local: 'local', mock: 'local' };

// Diff unifié coloré : + vert, − rouge, en-têtes atténués.
function Diff({ text }) {
  return (
    <pre className="os-atelier-diff">
      {(text || '').split('\n').map((l, i) => {
        const cls = l.startsWith('+++') || l.startsWith('---') || l.startsWith('@@') ? 'h' : l[0] === '+' ? 'add' : l[0] === '-' ? 'del' : '';
        return <span key={i} className={cls}>{l || ' '}{'\n'}</span>;
      })}
    </pre>
  );
}

function BuildCard({ build, meta }) {
  const [open, setOpen] = useState(false);
  const max = build.max_lines ?? 120;
  const n = build.lines_changed ?? 0;
  const ok = build.status === 'applied';
  return (
    <article className={`os-atelier-card ${ok ? 'ok' : 'ko'}`}>
      <header>
        <span className="os-icon-tile small"><Icon name={meta?.icon ?? 'grid'} size={18} /></span>
        <div className="os-atelier-card-title">
          <strong>{build.spec?.title || meta?.title || build.app}</strong>
          <span className="mono small muted">{build.app}</span>
        </div>
        <span className={`pill ${ok ? 'st-success' : 'st-error'}`}>{ok ? 'appliquée' : 'refusée'}</span>
        <span className="pill">{SOURCE[build.source] ?? build.source ?? '—'}</span>
      </header>
      <div className="os-atelier-gauge" title={`${n} lignes modifiées sur ${max} autorisées`}>
        <div className={n > max ? 'over' : ''} style={{ width: `${Math.min(100, (n / max) * 100)}%` }} />
      </div>
      <span className="mono small">{n} / {max} lignes</span>
      {build.error && <p className="os-error">{build.error}</p>}
      {build.diff ? (
        <>
          <button className="btn ghost os-atelier-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
            <Icon name="chevron" size={13} /> {open ? 'Masquer le diff' : 'Voir le diff'}
          </button>
          {open && <Diff text={build.diff} />}
        </>
      ) : <span className="muted small">Aucune modification (spec de base).</span>}
    </article>
  );
}

export default function Atelier({ initialPrompt = '', onDeployed }) {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [builds, setBuilds] = useState(null);
  const [tick, setTick] = useState(0);

  // Pendant la génération (un appel Gemma ≈ 30 s), on fait avancer l'app « en cours » à titre indicatif.
  useEffect(() => {
    if (!busy) return undefined;
    setTick(0);
    const t = setInterval(() => setTick((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, [busy]);
  const current = Math.min(BUILD_APPS.length - 1, Math.floor(tick / 8));

  const generate = async () => {
    setBusy(true); setError(null); setBuilds(null);
    try {
      const r = await api.buildApps(prompt.trim());
      setBuilds(r.builds ?? []);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="os-atelier">
      <div className="os-wall" aria-hidden="true" />
      <div className="os-atelier-inner">
        <header className="os-atelier-head">
          <span className="eyebrow">Atelier · générateur d'applications</span>
          <h1>Décrivez votre business, <span className="serif-i">Gemma prépare vos applications.</span></h1>
          <p className="muted">Caisse, clients, ventes et automatisation sont personnalisées par petites touches
            (≤ 120 lignes de spec par application), vérifiées avant déploiement.</p>
        </header>

        {!builds && (
          <section className="os-card os-atelier-form">
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={busy} rows={5}
              placeholder="Ex. Dépôt de boissons à Kinshasa, casiers Primus et Simba, clients suivis par quartier…" />
            <div className="os-atelier-examples">
              {EXAMPLES.map((x) => (
                <button key={x.label} className="pill os-atelier-ex" disabled={busy} onClick={() => setPrompt(x.text)}>{x.label}</button>
              ))}
            </div>
            {error && <p className="os-error">{error}</p>}
            <button className="btn accent os-atelier-go" disabled={busy || prompt.trim().length < 5} onClick={generate}>
              <Icon name="bolt" size={15} /> {busy ? 'Génération en cours…' : 'Générer mes applications'}
            </button>
          </section>
        )}

        {busy && (
          <section className="os-atelier-building" aria-live="polite">
            <p className="muted small">Gemma prépare le profil de votre commerce puis l'applique à chaque application. Environ 30 à 45 secondes.</p>
            <ol>
              {BUILD_APPS.map((a, i) => (
                <li key={a.app} className={i === current ? 'run' : ''} style={{ '--i': i }}>
                  <span className="os-icon-tile small"><Icon name={a.icon} size={18} /></span>
                  <strong>{a.title}</strong>
                  <span className="os-atelier-bar"><span /></span>
                  <span className="mono small muted">en cours…</span>
                </li>
              ))}
            </ol>
          </section>
        )}

        {builds && (
          <section className="os-atelier-result">
            <div className="os-atelier-grid">
              {builds.map((b) => <BuildCard key={b.id ?? b.app} build={b} meta={BUILD_APPS.find((a) => a.app === b.app)} />)}
            </div>
            <div className="os-actions">
              <button className="btn dark" onClick={onDeployed}><Icon name="grid" size={14} /> Ouvrir le bureau</button>
              <button className="btn ghost" onClick={() => setBuilds(null)}>Modifier la description</button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
