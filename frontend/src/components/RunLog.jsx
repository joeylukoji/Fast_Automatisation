import { useStore } from '../store';

export default function RunLog() {
  const result = useStore((s) => s.runResult);

  return (
    <div className="panel">
      <h2>Journal d'exécution</h2>
      {!result && <p className="muted">Aucune exécution pour l'instant. Utilisez « Simuler » pour tester sans risque.</p>}
      {result && (
        <>
          <p className="muted">
            {result.dry_run ? 'Simulation' : 'Exécution réelle'} — {result.status === 'success' ? 'réussie' : 'échouée'}
          </p>
          <ol className="steps">
            {result.steps.map((s) => (
              <li key={s.node_id} className={`st-${s.status}`}>
                <strong>{s.node_id}</strong> — {s.status}
                {s.simulated ? ' (simulé)' : ''} {s.duration_ms ? `· ${s.duration_ms} ms` : ''}
                {s.error && <div className="err">{s.error}</div>}
                {s.output && <pre>{JSON.stringify(s.output, null, 2)}</pre>}
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
