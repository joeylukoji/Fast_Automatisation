import { Background, Controls, ReactFlow } from '@xyflow/react';
import { useStore } from '../store';
import KernelNode from './KernelNode.jsx';

// Défini hors du composant : un nouvel objet à chaque rendu relancerait React Flow.
const nodeTypes = { kernel: KernelNode };

export default function GraphEditor() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const specs = useStore((s) => s.specs);
  const { onNodesChange, onEdgesChange, onConnect, addNode, select } = useStore.getState();

  return (
    <section className="editor">
      <div className="palette">
        {specs.map((s) => (
          <button key={s.type} className="chip" title={s.description} onClick={() => addNode(s.type)}>
            + {s.label}
          </button>
        ))}
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, node) => select(node.id)}
        onPaneClick={() => select(null)}
        fitView
        deleteKeyCode={['Backspace', 'Delete']}
      >
        <Background />
        <Controls />
      </ReactFlow>
      {nodes.length === 0 && (
        <div className="empty">Décrivez une automatisation ci-dessus, ou ajoutez un bloc depuis la palette.</div>
      )}
    </section>
  );
}
