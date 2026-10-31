import { useMemo, useState } from 'react';
import Icon from '../icons.jsx';
import { useStore } from '../store';

const GROUPS = [
  { title: 'Déclencheurs', test: (s) => s.is_trigger },
  { title: 'Intelligence artificielle', test: (s) => s.type === 'llm' },
  { title: 'Logique', test: (s) => s.branching },
  { title: 'Actions', test: () => true },
];

// Panneau latéral d'ajout de nœud (« Que se passe-t-il ensuite ? »).
export default function NodeCreator() {
  const creator = useStore((s) => s.creator);
  const specs = useStore((s) => s.specs);
  const hasTrigger = useStore((s) => s.nodes.some((n) => specs.find((x) => x.type === n.data.kind)?.is_trigger));
  const { addNode, closeCreator } = useStore.getState();
  const [q, setQ] = useState('');

  const groups = useMemo(() => {
    const used = new Set();
    const match = (s) => `${s.label} ${s.description} ${s.type}`.toLowerCase().includes(q.toLowerCase());
    return GROUPS.map((g) => {
      const items = specs.filter((s) => !used.has(s.type) && g.test(s) && match(s));
      items.forEach((s) => used.add(s.type));
      return { ...g, items };
    }).filter((g) => g.items.length);
  }, [specs, q]);

  if (!creator) return null;
  const connecting = creator.source || creator.edge;
  return (
    <aside className="k-creator">
      <header>
        <div>
          <span className="eyebrow">{connecting ? 'Étape suivante' : 'Ajouter'}</span>
          <h3>{connecting ? 'Que se passe-t-il ensuite ?' : hasTrigger ? 'Ajouter une étape' : 'Que doit déclencher le workflow ?'}</h3>
        </div>
        <button className="icon-btn" onClick={closeCreator} title="Fermer"><Icon name="x" /></button>
      </header>
      <label className="k-search">
        <Icon name="search" size={15} />
        <input autoFocus placeholder="Rechercher un nœud…" value={q} onChange={(e) => setQ(e.target.value)} />
      </label>
      <div className="k-creator-list">
        {groups.map((g) => (
          <section key={g.title}>
            <h4>{g.title}</h4>
            {g.items.map((s) => (
              <button key={s.type} className={`k-creator-item kind-${s.type}`} onClick={() => addNode(s.type)}
                disabled={s.is_trigger && (hasTrigger || connecting)}>
                <span className="k-creator-icon"><Icon name={s.type} size={20} /></span>
                <span><strong>{s.label}</strong><small>{s.description}</small></span>
              </button>
            ))}
          </section>
        ))}
        {!groups.length && <p className="muted">Aucun nœud ne correspond.</p>}
      </div>
    </aside>
  );
}
