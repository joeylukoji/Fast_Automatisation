import { useRef } from 'react';
import Icon from '../icons.jsx';
import { useStore } from '../store';

// Champs de sortie connus par type (utilisés tant qu'aucune exécution n'a eu lieu).
const OUTPUT_FIELDS = {
  trigger_manual: ['text'], http_request: ['status', 'json', 'text'], llm: ['text'], condition: ['result', 'branch'],
};

function DataView({ title, step, empty }) {
  return (
    <section className="ndv-data">
      <header><span className="eyebrow">{title}</span>
        {step && <span className={`pill st-${step.status}`}>{step.status}{step.simulated ? ' · simulé' : ''}</span>}</header>
      {step?.output ? <pre>{JSON.stringify(step.output, null, 2)}</pre>
        : step?.error ? <pre className="err">{step.error}</pre>
          : <p className="muted">{empty}</p>}
    </section>
  );
}

function Field({ name, schema, value, onChange, required, onFocus }) {
  const label = <span className="ndv-label">{schema.title ?? name}{required && <em>*</em>}</span>;
  if (schema.enum) {
    return (
      <label className="ndv-field">{label}
        <select value={value ?? schema.default ?? ''} onChange={(e) => onChange(e.target.value)}>
          {schema.enum.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </label>
    );
  }
  const long = ['text', 'body', 'prompt'].includes(name);
  return (
    <label className="ndv-field">{label}
      {long
        ? <textarea rows={4} value={value ?? ''} onFocus={onFocus} onChange={(e) => onChange(e.target.value)} />
        : <input value={value ?? ''} onFocus={onFocus} onChange={(e) => onChange(e.target.value)} />}
      {schema.description && <small>{schema.description}</small>}
    </label>
  );
}

// Fenêtre de détail d'un nœud, organisée comme n8n : Entrée | Paramètres | Sortie.
export default function Ndv() {
  const id = useStore((s) => s.ndvId);
  const node = useStore((s) => s.nodes.find((n) => n.id === s.ndvId));
  const spec = useStore((s) => s.specs.find((x) => x.type === node?.data.kind));
  const edges = useStore((s) => s.edges);
  const nodes = useStore((s) => s.nodes);
  const runResult = useStore((s) => s.runResult);
  const validationErrors = useStore((s) => s.validationErrors);
  const steps = runResult?.steps ?? [];
  const errors = validationErrors.filter((e) => e.includes(`« ${id} »`));
  const { updateParams, closeNdv, deleteNode } = useStore.getState();
  const focused = useRef(null);
  if (!node || !spec) return null;

  const parents = edges.filter((e) => e.target === id).map((e) => e.source);
  // Tous les ancêtres peuvent être référencés par {{id.champ}}.
  const ancestors = [];
  const visit = (nid) => edges.filter((e) => e.target === nid).forEach((e) => {
    if (!ancestors.includes(e.source)) { ancestors.push(e.source); visit(e.source); }
  });
  visit(id);
  const fields = (nid) => {
    const out = steps.find((s) => s.node_id === nid)?.output;
    const kind = nodes.find((n) => n.id === nid)?.data.kind;
    const keys = out && !out.simulated ? Object.keys(out) : [];
    return keys.length ? keys : OUTPUT_FIELDS[kind] ?? [];
  };
  const insert = (token) => {
    const name = focused.current ?? 'text';
    if (!(name in (spec.params_schema.properties ?? {}))) return;
    updateParams(id, { ...node.data.params, [name]: `${node.data.params[name] ?? ''}${token}` });
  };
  const props = Object.entries(spec.params_schema.properties ?? {});
  const required = spec.params_schema.required ?? [];

  return (
    <div className="ndv-overlay" onMouseDown={(e) => e.target === e.currentTarget && closeNdv()}>
      <div className="ndv">
        <DataView title="Entrée" step={steps.find((s) => s.node_id === parents[0])}
          empty={spec.is_trigger ? 'Un déclencheur ne reçoit pas de données.' : parents.length
            ? 'Testez le workflow pour voir les données reçues.' : 'Aucun nœud ne précède celui-ci.'} />
        <section className="ndv-params">
          <header>
            <span className={`ndv-icon kind-${spec.type}`}><Icon name={spec.type} size={22} /></span>
            <div><h3>{spec.label}</h3><span className="mono muted">{id}</span></div>
            <button className="icon-btn" onClick={closeNdv} title="Fermer"><Icon name="x" /></button>
          </header>
          <p className="muted">{spec.description}</p>
          {errors.map((e) => <p key={e} className="ndv-error"><Icon name="alert" size={14} /> {e}</p>)}
          {props.length === 0 && <p className="muted">Ce nœud n'a pas de paramètre.</p>}
          {props.map(([name, schema]) => (
            <Field key={name} name={name} schema={schema} value={node.data.params[name]} required={required.includes(name)}
              onFocus={() => { focused.current = name; }}
              onChange={(v) => updateParams(id, { ...node.data.params, [name]: v })} />
          ))}
          {ancestors.length > 0 && (
            <div className="ndv-vars">
              <span className="eyebrow">Données disponibles — cliquer pour insérer dans le champ actif</span>
              {ancestors.map((a) => (
                <div key={a} className="ndv-var-row"><span className="mono">{a}</span>
                  {fields(a).map((f) => <button key={f} className="chip" onClick={() => insert(`{{${a}.${f}}}`)}>{f}</button>)}
                </div>
              ))}
            </div>
          )}
          <footer><button className="btn ghost danger-text" onClick={() => deleteNode(id)}><Icon name="trash" size={14} /> Supprimer</button></footer>
        </section>
        <DataView title="Sortie" step={steps.find((s) => s.node_id === id)} empty="Testez le workflow pour voir le résultat de ce nœud." />
      </div>
    </div>
  );
}
