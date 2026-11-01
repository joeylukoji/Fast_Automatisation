import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import Atelier from '../apps/Atelier.jsx';
import Desktop, { useWindows } from '../apps/Desktop.jsx';
import { Automation, Customers, Invoice, Pos, Sales } from '../apps/erp.jsx';
import { SpecContext } from '../apps/spec.jsx';
import Icon from '../icons.jsx';

// Onglet « Applications » : Atelier (génération) puis bureau ERP piloté par les specs déployées.
// `spec` = nom de l'app côté générateur (docs/app-builder-contract.md).
const BASE = {
  pos: { spec: 'caisse', title: 'Caisse', icon: 'trigger_erp_sale', w: 940, h: 600, render: (_, ctx) => <Pos open={ctx.open} /> },
  customers: { spec: 'clients', title: 'Clients', icon: 'erp_customer_lookup', w: 860, h: 520, render: () => <Customers /> },
  sales: { spec: 'ventes', title: 'Ventes & factures', icon: 'invoice_render', w: 860, h: 500, render: (_, ctx) => <Sales open={ctx.open} /> },
  automation: { spec: 'automatisation', title: 'Automatisation', icon: 'bolt', w: 620, h: 460, render: () => <Automation /> },
  invoice: { title: 'Facture', icon: 'invoice_render', w: 720, h: 640, render: (p) => <Invoice sale={p.sale} /> },
};
const LAUNCHERS = ['pos', 'customers', 'sales', 'automation'];

function Bureau({ specs, onRegenerate, onReset }) {
  const wm = useWindows();
  const { open } = wm;
  useEffect(() => { open('pos', 'pos'); }, [open]); // la Caisse s'ouvre par défaut
  // Titres de fenêtres / icônes issus des specs
  const apps = useMemo(() => Object.fromEntries(Object.entries(BASE).map(([id, a]) =>
    [id, { ...a, title: (a.spec && specs[a.spec]?.title) || a.title }])), [specs]);
  const shop = specs.caisse?.shop ?? {};
  const actions = (
    <>
      <button className="os-task link" onClick={onRegenerate} title="Retour à l'Atelier"><Icon name="bolt" size={14} /> <span>Régénérer</span></button>
      <button className="os-task link" onClick={onReset} title="Supprimer les applications générées"><Icon name="trash" size={14} /> <span>Réinitialiser la démo</span></button>
    </>
  );
  return (
    <Desktop apps={apps} launchers={LAUNCHERS} wm={wm} taskbarExtra={actions}>
      <div className="os-brand">
        <span className="brand-name">{shop.name || 'Fast Automatisation'}</span>
        <span className="serif-i">{shop.name ? [shop.city, shop.slogan].filter(Boolean).join(' — ') : 'Market — Kinshasa'}</span>
      </div>
    </Desktop>
  );
}

export default function Apps() {
  const [state, setState] = useState(null); // {deployed, prompt, apps}
  const [error, setError] = useState(null);
  const [atelier, setAtelier] = useState(false); // forcé par « Régénérer »
  const load = useCallback(() => api.apps()
    .then((s) => { setState(s); setAtelier(!s.deployed); setError(null); })
    .catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);

  const reset = async () => {
    if (!window.confirm('Réinitialiser la démo ? Les applications générées seront retirées du bureau.')) return;
    try { await api.resetApps(); } catch (e) { setError(e.message); return; }
    setState((s) => ({ ...s, deployed: false, apps: {} })); setAtelier(true);
  };

  if (error && !state) return <div className="os-atelier"><div className="os-atelier-inner"><p className="os-error">{error}</p>
    <button className="btn" onClick={load}>Réessayer</button></div></div>;
  if (!state) return <div className="os-atelier"><div className="os-atelier-inner"><p className="muted">Chargement…</p></div></div>;
  if (atelier || !state.deployed) return <Atelier initialPrompt={state.prompt ?? ''} onDeployed={load} />;
  return (
    <SpecContext.Provider value={state.apps ?? {}}>
      <Bureau specs={state.apps ?? {}} onRegenerate={() => setAtelier(true)} onReset={reset} />
    </SpecContext.Provider>
  );
}
