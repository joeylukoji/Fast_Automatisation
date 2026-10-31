import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import Icon from '../icons.jsx';
import DataTable from './DataTable.jsx';
import { Field, Form } from './Form.jsx';
import { AppRoot, useLabels, useSpec } from './spec.jsx';
import { DEFAULT_RATE, STATUS, cdf, date, toCdf, usd } from './format';

// Petit hook de chargement : renvoie [données, erreur, recharger].
function useLoad(fn) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const reload = useCallback(() => {
    setError(null);
    fn().then(setData).catch((e) => { setError(e.message); setData([]); });
  }, [fn]);
  useEffect(reload, [reload]);
  return [data, error, reload];
}

export function StatusBadge({ status }) {
  const [label, cls] = STATUS[status] ?? [status ?? '—', ''];
  return <span className={`pill ${cls}`}>{label}</span>;
}

const openInvoice = (open, sale) =>
  open(`invoice:${sale.id}`, 'invoice', { sale }, `Facture ${sale.invoice_number}`);

// Formulaire client réutilisé par la Caisse (création rapide) et l'app Clients.
// Les `customer_fields` de la spec « clients » s'ajoutent et partent dans `extra`.
function CustomerForm({ onCreated, compact }) {
  const t = useLabels('clients');
  const extraFields = (useSpec('clients').customer_fields ?? []).filter((x) => /^[a-z_]+$/.test(x?.key ?? ''));
  const blank = { name: '', email: '', phone: '', ...Object.fromEntries(extraFields.map((x) => [x.key, ''])) };
  const [f, setF] = useState(blank);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async () => {
    setBusy(true); setError(null);
    try {
      const extra = Object.fromEntries(extraFields.map((x) => [x.key, (f[x.key] ?? '').trim()]).filter(([, v]) => v));
      const c = await api.createCustomer({ name: f.name.trim(), email: f.email.trim(), phone: f.phone.trim() || null,
        ...(extraFields.length ? { extra } : {}) });
      setF(blank); onCreated(c);
    } catch (e) {
      setError(/exist|409|déjà/i.test(e.message) ? `Un client avec cet email existe déjà (${e.message}).` : e.message);
    } finally { setBusy(false); }
  };
  return (
    <Form onSubmit={submit} error={error} className={compact ? 'compact' : ''}>
      <Field label={t('field_name', 'Nom')} value={f.name} onChange={set('name')} required placeholder="Ex. Marie Kabila" />
      <Field label={t('field_email', 'Email')} type="email" value={f.email} onChange={set('email')} required placeholder="client@exemple.cd" />
      <Field label={t('field_phone', 'Téléphone')} value={f.phone} onChange={set('phone')} placeholder="+243 …" />
      {!compact && extraFields.map((x) => (
        <Field key={x.key} label={x.label || x.key} value={f[x.key] ?? ''} onChange={set(x.key)} />
      ))}
      <button className="btn dark" disabled={busy}><Icon name="plus" size={14} /> {busy ? 'Ajout…' : t('add_customer', 'Ajouter le client')}</button>
    </Form>
  );
}

/* ---------- Caisse ---------- */
export function Pos({ open }) {
  const t = useLabels('caisse');
  const shop = useSpec('caisse').shop ?? {};
  const [customers, , reloadCustomers] = useLoad(api.customers);
  const [products, prodError] = useLoad(api.products);
  const [customer, setCustomer] = useState(null);
  const [query, setQuery] = useState('');
  const [creating, setCreating] = useState(false);
  const [cart, setCart] = useState({});
  const [send, setSend] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (customers ?? []).filter((c) => !q || [c.name, c.email, c.phone].some((v) => v?.toLowerCase().includes(q))).slice(0, 6);
  }, [customers, query]);

  const lines = (products ?? []).filter((p) => cart[p.id] > 0).map((p) => ({ ...p, qty: cart[p.id] }));
  const total = lines.reduce((s, l) => s + l.qty * l.price_usd, 0);
  const rate = result?.sale?.rate ?? DEFAULT_RATE;
  const add = (id, d) => setCart((c) => ({ ...c, [id]: Math.max(0, (c[id] ?? 0) + d) }));

  const checkout = async () => {
    setBusy(true); setError(null);
    try {
      const r = await api.createSale({ customerId: customer.id, items: lines.map((l) => ({ product_id: l.id, qty: l.qty })), sendInvoice: send });
      setResult(r); reloadCustomers();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const reset = () => { setResult(null); setCart({}); setCustomer(null); setQuery(''); setError(null); };

  const root = (body) => <AppRoot app="caisse" className="fill">{body}</AppRoot>;

  if (result) {
    const { sale, runs = [] } = result;
    const failed = runs.flatMap((r) => r.steps ?? []).filter((s) => s.status === 'error');
    return root(
      <div className="os-pane">
        <div className={`os-result ${sale.invoice_status}`}>
          <Icon name={sale.invoice_status === 'failed' ? 'alert' : 'check'} size={20} />
          <div>
            <strong>Vente enregistrée — facture {sale.invoice_number}</strong>
            <p>{sale.customer_name} · {usd(sale.total_usd)} · {cdf(sale.total_cdf)} <span className="muted">(taux {sale.rate})</span></p>
            <p>Facture : <StatusBadge status={sale.invoice_status} />
              {sale.invoice_status === 'sent' && <span className="muted"> à {sale.customer_email}</span>}</p>
            {failed.map((s) => <p key={s.node_id} className="os-error">{s.node_id} : {s.error}</p>)}
          </div>
        </div>
        {runs.map((r) => (
          <div key={r.run_id} className="os-run">
            <span className="eyebrow">Run {r.run_id.slice(0, 8)} · {r.status}{r.dry_run ? ' · simulé' : ''}</span>
            <ol>{(r.steps ?? []).map((s) => (
              <li key={s.node_id} className={`st-${s.status}`}><span className={`pill st-${s.status}`}>{s.status}</span>
                <span className="mono">{s.node_id}</span> <span className="muted">{s.duration_ms} ms{s.simulated ? ' · simulé' : ''}</span></li>
            ))}</ol>
            {r.validation_errors?.map((v) => <p key={v} className="os-error">{v}</p>)}
          </div>
        ))}
        {!runs.length && <p className="muted">Aucun workflow exécuté (envoi de facture désactivé).</p>}
        <div className="os-actions">
          <button className="btn" onClick={() => openInvoice(open, sale)}><Icon name="invoice_render" size={14} /> {t('view_invoice', 'Voir la facture')}</button>
          <button className="btn dark" onClick={reset}><Icon name="plus" size={14} /> {t('new_sale', 'Nouvelle vente')}</button>
        </div>
      </div>
    );
  }

  return root(
    <div className="os-pos">
      <div className="os-pos-main">
        {shop.name && (
          <header className="os-shop">
            <strong>{shop.name}</strong>
            <span className="muted">{[shop.city, shop.slogan].filter(Boolean).join(' · ')}</span>
          </header>
        )}
        <section className="os-card">
          <h4 className="eyebrow">{t('step_customer', '1 · Client')}</h4>
          {customer ? (
            <div className="os-chosen">
              <div><strong>{customer.name}</strong><span className="muted">{customer.email}{customer.phone ? ` · ${customer.phone}` : ''}</span></div>
              <button className="btn ghost" onClick={() => setCustomer(null)}>{t('change_customer', 'Changer')}</button>
            </div>
          ) : creating ? (
            <>
              <CustomerForm compact onCreated={(c) => { setCustomer(c); setCreating(false); reloadCustomers(); }} />
              <button className="btn ghost" onClick={() => setCreating(false)}>Annuler</button>
            </>
          ) : (
            <>
              <div className="os-search"><Icon name="search" size={14} />
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('search_placeholder', 'Rechercher nom, email, téléphone…')} /></div>
              <ul className="os-list">
                {matches.map((c) => (
                  <li key={c.id}><button onClick={() => setCustomer(c)}><strong>{c.name}</strong> <span className="muted">{c.email}</span></button></li>
                ))}
                {customers && !matches.length && <li className="muted">{t('no_customer', 'Aucun client trouvé.')}</li>}
              </ul>
              <button className="btn" onClick={() => setCreating(true)}><Icon name="plus" size={14} /> {t('new_customer', 'Nouveau client')}</button>
            </>
          )}
        </section>
        <section className="os-card">
          <h4 className="eyebrow">{t('step_products', '2 · Produits')}</h4>
          {prodError && <p className="os-error">{prodError}</p>}
          <div className="os-products">
            {(products ?? []).map((p) => (
              <div key={p.id} className={`os-product ${cart[p.id] ? 'in' : ''}`}>
                <button className="os-product-name" onClick={() => add(p.id, 1)}>{p.name}</button>
                <span className="mono">{usd(p.price_usd)}{p.unit ? <small> / {p.unit}</small> : null}</span>
                <div className="os-qty">
                  <button onClick={() => add(p.id, -1)} disabled={!cart[p.id]} aria-label="Retirer"><Icon name="minus" size={13} /></button>
                  <span className="mono">{cart[p.id] ?? 0}</span>
                  <button onClick={() => add(p.id, 1)} aria-label="Ajouter"><Icon name="plus" size={13} /></button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
      <aside className="os-cart">
        <h4 className="eyebrow">{t('step_cart', '3 · Panier')}</h4>
        {lines.length ? (
          <ul>{lines.map((l) => <li key={l.id}><span>{l.qty} × {l.name}</span><span className="mono">{usd(l.qty * l.price_usd)}</span></li>)}</ul>
        ) : <p className="muted">{t('empty_cart', 'Panier vide.')}</p>}
        <div className="os-total">
          <span>{t('total', 'Total')}</span><strong className="mono">{usd(total)}</strong>
          <span className="muted">≈ {cdf(toCdf(total, rate))} <small>(taux {rate})</small></span>
        </div>
        <label className="os-check"><input type="checkbox" checked={send} onChange={(e) => setSend(e.target.checked)} /> {t('send_invoice', 'Envoyer la facture par email')}</label>
        {error && <p className="os-error">{error}</p>}
        <button className="btn accent os-pay" disabled={!customer || !lines.length || busy} onClick={checkout}>
          {busy ? 'Encaissement…' : t('checkout', 'Encaisser')}</button>
        {!customer && <small className="muted">{t('choose_customer_hint', 'Choisissez un client pour encaisser.')}</small>}
      </aside>
    </div>
  );
}

/* ---------- Clients ---------- */
export function Customers() {
  const [rows, error, reload] = useLoad(api.customers);
  const t = useLabels('clients');
  const extraFields = useSpec('clients').customer_fields ?? [];
  return (
    <AppRoot app="clients">
    <div className="os-pane os-split">
      <div>
        {error && <p className="os-error">{error}</p>}
        <DataTable rows={rows} empty={t('empty', 'Aucun client.')} columns={[
          { key: 'name', label: t('col_name', 'Nom') },
          { key: 'email', label: t('col_email', 'Email') },
          { key: 'phone', label: t('col_phone', 'Téléphone'), render: (c) => c.phone || '—' },
          // colonnes des champs supplémentaires, si le backend renvoie `extra`
          ...extraFields.filter((x) => (rows ?? []).some((c) => c.extra?.[x.key]))
            .map((x) => ({ key: `extra.${x.key}`, label: x.label || x.key, render: (c) => c.extra?.[x.key] || '—' })),
          { key: 'purchases', label: t('col_purchases', 'Achats'), align: 'right', render: (c) => c.purchases ?? 0 },
          { key: 'total_spent_usd', label: t('col_total', 'Total dépensé'), align: 'right', render: (c) => <span className="mono">{usd(c.total_spent_usd)}</span> },
        ]} />
      </div>
      <section className="os-card"><h4 className="eyebrow">{t('new_customer', 'Nouveau client')}</h4><CustomerForm onCreated={reload} /></section>
    </div>
    </AppRoot>
  );
}

/* ---------- Ventes & factures ---------- */
export function Sales({ open }) {
  const [rows, error, reload] = useLoad(api.sales);
  const t = useLabels('ventes');
  return (
    <AppRoot app="ventes">
    <div className="os-pane">
      <div className="os-actions top"><span className="muted small">{t('hint', 'Cliquez une vente pour ouvrir sa facture.')}</span>
        <button className="btn ghost" onClick={reload}>{t('refresh', 'Actualiser')}</button></div>
      {error && <p className="os-error">{error}</p>}
      <DataTable rows={rows} empty={t('empty', "Aucune vente pour l'instant.")} onRowClick={(s) => openInvoice(open, s)} columns={[
        { key: 'invoice_number', label: t('col_invoice', 'Facture'), render: (s) => <span className="mono">{s.invoice_number}</span> },
        { key: 'customer_name', label: t('col_customer', 'Client') },
        { key: 'total_usd', label: t('col_total_usd', 'Total USD'), align: 'right', render: (s) => <span className="mono">{usd(s.total_usd)}</span> },
        { key: 'total_cdf', label: t('col_total_cdf', 'Total CDF'), align: 'right', render: (s) => <span className="mono">{cdf(s.total_cdf)}</span> },
        { key: 'created_at', label: t('col_date', 'Date'), render: (s) => date(s.created_at) },
        { key: 'invoice_status', label: t('col_status', 'Statut'), render: (s) => <StatusBadge status={s.invoice_status} /> },
      ]} />
    </div>
    </AppRoot>
  );
}

/* ---------- Facture (iframe) ---------- */
export function Invoice({ sale }) {
  const url = api.invoiceUrl(sale.id);
  const t = useLabels('ventes');
  return (
    <AppRoot app="ventes" className="fill">
    <div className="os-invoice">
      <div className="os-actions top">
        <span className="mono small">{sale.invoice_number}</span>
        <a className="btn ghost" href={url} target="_blank" rel="noreferrer"><Icon name="external" size={13} /> {t('open_tab', 'Ouvrir dans un onglet')}</a>
      </div>
      <iframe title={`Facture ${sale.invoice_number}`} src={url} />
    </div>
    </AppRoot>
  );
}

/* ---------- Automatisation ---------- */
// Ordonne les nœuds selon les arêtes (chaîne), à défaut l'ordre du tableau.
function chain(wf) {
  const nodes = wf?.nodes ?? [];
  const edges = wf?.edges ?? [];
  const targets = new Set(edges.map((e) => e.target));
  const out = [];
  let cur = nodes.find((n) => !targets.has(n.id));
  while (cur && !out.includes(cur)) {
    out.push(cur);
    const next = edges.find((e) => e.source === cur.id);
    cur = next && nodes.find((n) => n.id === next.target);
  }
  return [...out, ...nodes.filter((n) => !out.includes(n))];
}

export function Automation() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.automation().then(setData).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);
  const install = async () => {
    setBusy(true); setError(null);
    try { await api.installAutomation(); await load(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const wf = data?.workflow;
  const t = useLabels('automatisation');
  return (
    <AppRoot app="automatisation">
    <div className="os-pane">
      <p className="os-lead">{t('lead', "Chaque vente encaissée déclenche les workflows enregistrés contenant le bloc « Nouvelle vente (ERP) » ; s'il n'y en a aucun, le workflow par défaut ci-dessous s'exécute.")}</p>
      {error && <p className="os-error">{error}</p>}
      {!data && !error && <p className="muted">Chargement…</p>}
      {wf && (
        <section className="os-card">
          <h4 className="eyebrow">{wf.name} · {data.workflow_id ? 'enregistré' : 'par défaut, non enregistré'}</h4>
          <ol className="os-chain">
            {chain(wf).map((n) => (
              <li key={n.id} className={`kind-${n.type}`}>
                <span className="os-chain-ico"><Icon name={n.type} size={16} /></span>
                <span><strong>{n.id}</strong><small className="mono">{n.type}</small></span>
              </li>
            ))}
          </ol>
        </section>
      )}
      <div className="os-actions">
        <button className="btn dark" onClick={install} disabled={busy}><Icon name="save" size={14} /> {busy ? 'Installation…' : t('install', 'Installer dans le Studio')}</button>
        {data?.workflow_id && <a className="btn" href="#/studio"><Icon name="external" size={14} /> {t('open_studio', 'Ouvrir dans le Studio')}</a>}
      </div>
    </div>
    </AppRoot>
  );
}
