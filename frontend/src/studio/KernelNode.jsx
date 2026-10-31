import { Handle, Position } from '@xyflow/react';
import Icon from '../icons.jsx';
import { useStore } from '../store';

// Nœud façon n8n : carte carrée avec icône, libellé sous la carte, sorties avec « + » quand elles sont libres.
function Output({ id, nodeId, top, label }) {
  const connected = useStore((s) => s.edges.some((e) => e.source === nodeId && (e.sourceHandle ?? null) === (id ?? null)));
  const openCreator = useStore((s) => s.openCreator);
  return (
    <>
      <Handle type="source" id={id ?? undefined} position={Position.Right} className="k-handle out" style={{ top }} />
      {label && <span className={`k-branch ${id}`} style={{ top }}>{label}</span>}
      {!connected && (
        <div className="k-stub" style={{ top }}>
          <span className="k-stub-line" />
          <button className="k-stub-plus nodrag" title="Ajouter une étape"
            onClick={(e) => { e.stopPropagation(); openCreator({ source: nodeId, handle: id ?? null }); }}>
            <Icon name="plus" size={14} />
          </button>
        </div>
      )}
    </>
  );
}

export default function KernelNode({ id, data, selected }) {
  const spec = useStore((s) => s.specs.find((x) => x.type === data.kind));
  const step = useStore((s) => s.runResult?.steps.find((x) => x.node_id === id));
  const invalid = useStore((s) => s.validationErrors.some((e) => e.includes(`« ${id} »`)));
  const { openNdv, deleteNode } = useStore.getState();
  const status = step?.status;
  const trigger = spec?.is_trigger;

  return (
    <div className={`k-node kind-${data.kind} ${selected ? 'selected' : ''} ${status ? `st-${status}` : ''} ${invalid ? 'invalid' : ''}`}
      onDoubleClick={() => openNdv(id)}>
      <div className="k-toolbar nodrag">
        <button title="Ouvrir" onClick={() => openNdv(id)}><Icon name="play" size={13} /></button>
        <button title="Supprimer" onClick={() => deleteNode(id)}><Icon name="trash" size={13} /></button>
      </div>
      <div className={`k-box ${trigger ? 'trigger' : ''}`}>
        {trigger && <span className="k-bolt"><Icon name="bolt" size={12} /></span>}
        <Icon name={data.kind} size={38} stroke={1.3} className="k-icon" />
        {status === 'success' && <span className={`k-badge ok ${step.simulated ? 'sim' : ''}`} title={step.simulated ? 'Simulé' : 'Réussi'}>
          <Icon name={step.simulated ? 'flask' : 'check'} size={12} stroke={2} /></span>}
        {status === 'error' && <span className="k-badge err" title={step.error}><Icon name="alert" size={12} stroke={2} /></span>}
        {invalid && !status && <span className="k-badge warn" title="Paramètre manquant"><Icon name="alert" size={12} stroke={2} /></span>}
      </div>
      {!trigger && <Handle type="target" position={Position.Left} className="k-handle in" />}
      {spec?.branching ? (
        <>
          <Output id="true" nodeId={id} top="32%" label="vrai" />
          <Output id="false" nodeId={id} top="68%" label="faux" />
        </>
      ) : (
        <Output id={null} nodeId={id} top="50%" />
      )}
      <div className="k-label">
        <span className="k-title">{spec?.label ?? data.kind}</span>
        <span className="k-sub">{id}{status === 'skipped' ? ' · ignoré' : ''}</span>
      </div>
    </div>
  );
}
