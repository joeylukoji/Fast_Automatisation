import { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from '@xyflow/react';
import Icon from '../icons.jsx';
import { useStore } from '../store';

// Arête façon n8n : courbe de Bézier, flèche, boutons « insérer » / « supprimer » au survol,
// verte avec le nombre d'éléments après une exécution réussie.
export default function KernelEdge({ id, source, target, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition }) {
  const [hover, setHover] = useState(false);
  const passed = useStore((s) => {
    const a = s.runResult?.steps.find((x) => x.node_id === source);
    const b = s.runResult?.steps.find((x) => x.node_id === target);
    return a?.status === 'success' && b && b.status !== 'skipped';
  });
  const { openCreator, deleteEdge } = useStore.getState();
  // Décale le point d'arrivée pour laisser la place à la flèche.
  const [path, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition, targetX: targetX - 4, targetY, targetPosition, curvature: 0.35,
  });

  return (
    <>
      <g onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
        <BaseEdge id={id} path={path} className={`k-edge ${passed ? 'passed' : ''} ${hover ? 'hover' : ''}`}
          markerEnd={`url(#${passed ? 'k-arrow-ok' : hover ? 'k-arrow-hover' : 'k-arrow'})`} interactionWidth={24} />
      </g>
      <EdgeLabelRenderer>
        <div className={`k-edge-tools nodrag nopan ${hover ? 'show' : ''}`}
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
          {passed && !hover && <span className="k-edge-count">1 élément</span>}
          {hover && (
            <>
              <button title="Insérer une étape" onClick={() => openCreator({ edge: id })}><Icon name="plus" size={13} /></button>
              <button title="Supprimer la connexion" onClick={() => deleteEdge(id)}><Icon name="trash" size={13} /></button>
            </>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export function EdgeMarkers() {
  const marker = (id, cls) => (
    <marker id={id} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="12" markerHeight="12" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" className={cls} />
    </marker>
  );
  return (
    <svg className="k-markers" aria-hidden="true">
      <defs>{marker('k-arrow', 'm-default')}{marker('k-arrow-hover', 'm-hover')}{marker('k-arrow-ok', 'm-ok')}</defs>
    </svg>
  );
}
