import { useStore } from '../store';

function Field({ name, schema, value, onChange }) {
  const label = schema.title ?? name;
  if (schema.enum) {
    return (
      <label>
        {label}
        <select value={value ?? schema.default ?? ''} onChange={(e) => onChange(e.target.value)}>
          {schema.enum.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </label>
    );
  }
  return (
    <label>
      {label}
      <textarea rows={2} value={value ?? ''} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

export default function NodePanel() {
  const selectedId = useStore((s) => s.selectedId);
  const node = useStore((s) => s.nodes.find((n) => n.id === s.selectedId));
  const spec = useStore((s) => s.specs.find((x) => x.type === node?.data.kind));
  const updateParams = useStore((s) => s.updateParams);
  const deleteNode = useStore((s) => s.deleteNode);

  if (!node || !spec) {
    return (
      <div className="panel">
        <h2>Paramètres</h2>
        <p className="muted">Sélectionnez un bloc pour modifier ses paramètres.</p>
      </div>
    );
  }

  const props = Object.entries(spec.params_schema.properties ?? {});
  return (
    <div className="panel">
      <h2>{spec.label}</h2>
      <p className="muted">{spec.description}</p>
      {props.length === 0 && <p className="muted">Aucun paramètre.</p>}
      {props.map(([name, schema]) => (
        <Field
          key={name}
          name={name}
          schema={schema}
          value={node.data.params[name]}
          onChange={(v) => updateParams(selectedId, { ...node.data.params, [name]: v })}
        />
      ))}
      <p className="muted small">Utilisez {'{{id_bloc.champ}}'} pour réutiliser la sortie d'un autre bloc.</p>
      <button className="secondary" onClick={() => deleteNode(selectedId)}>
        Supprimer le bloc
      </button>
    </div>
  );
}
