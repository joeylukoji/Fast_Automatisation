import { Handle, Position } from '@xyflow/react';
import { useStore } from '../store';

const STATUS_LABEL = { success: 'OK', error: 'Erreur', skipped: 'Ignoré' };

export default function KernelNode({ id, data, selected }) {
  const spec = useStore((s) => s.specs.find((x) => x.type === data.kind));
  const step = useStore((s) => s.runResult?.steps.find((x) => x.node_id === id));
  const status = step?.status;

  return (
    <div className={`knode ${selected ? 'selected' : ''} ${status ? `st-${status}` : ''}`}>
      {!spec?.is_trigger && <Handle type="target" position={Position.Left} />}
      <div className="knode-title">{spec?.label ?? data.kind}</div>
      <div className="knode-id">{id}</div>
      {step && (
        <div className="knode-status">
          {STATUS_LABEL[status]}
          {step.simulated ? ' (simulé)' : ''}
        </div>
      )}
      {spec?.branching ? (
        <>
          <Handle type="source" id="true" position={Position.Right} style={{ top: '30%' }} />
          <Handle type="source" id="false" position={Position.Right} style={{ top: '70%' }} />
          <span className="branch-label t">oui</span>
          <span className="branch-label f">non</span>
        </>
      ) : (
        <Handle type="source" position={Position.Right} />
      )}
    </div>
  );
}
