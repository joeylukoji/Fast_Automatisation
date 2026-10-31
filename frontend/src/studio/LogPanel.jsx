import { useState } from 'react';
import Icon from '../icons.jsx';
import { useStore } from '../store';

export default function LogPanel() {
  const result = useStore((s) => s.runResult);
  const open = useStore((s) => s.logOpen);
  const toggle = useStore((s) => s.toggleLog);
  const [sel, setSel] = useState(null);
  const step = result?.steps.find((s) => s.node_id === sel) ?? result?.steps[0];

  return (
    <section className={`k-logs ${open ? 'open' : ''}`}>
      <button className="k-logs-bar" onClick={toggle}>
        <span className="eyebrow">Journal</span>
        {result ? (
          <span className={`pill st-${result.status}`}>
            {result.dry_run ? 'Simulation' : 'Exécution réelle'} · {result.status === 'success' ? 'réussie' : 'échouée'} · {result.steps.length} étapes
          </span>
        ) : <span className="muted">Aucune exécution — « Tester le workflow » simule sans rien envoyer.</span>}
        <Icon name="chevron" className={`k-logs-chev ${open ? 'up' : ''}`} />
      </button>
      {open && result && (
        <div className="k-logs-body">
          <ol>
            {result.validation_errors.map((e) => <li key={e} className="st-error"><Icon name="alert" size={13} /> {e}</li>)}
            {result.steps.map((s) => (
              <li key={s.node_id} className={`st-${s.status} ${step?.node_id === s.node_id ? 'active' : ''}`} onClick={() => setSel(s.node_id)}>
                <span className="dot" /> <span className="mono">{s.node_id}</span>
                <span className="muted">{s.status}{s.simulated ? ' · simulé' : ''}</span>
                <span className="mono muted right">{s.duration_ms} ms</span>
              </li>
            ))}
          </ol>
          <pre>{step ? JSON.stringify(step.output ?? step.error ?? null, null, 2) : ''}</pre>
        </div>
      )}
    </section>
  );
}
