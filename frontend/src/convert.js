// Conversion entre le schéma Kernel (source de vérité) et le format React Flow.
// React Flow ne sert qu'à l'affichage et à l'édition.
import dagre from '@dagrejs/dagre';

const NODE_W = 220;
const NODE_H = 90;

export function layout(nodes, edges) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', nodesep: 40, ranksep: 70 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const { x, y } = g.node(n.id);
    return { ...n, position: { x: x - NODE_W / 2, y: y - NODE_H / 2 } };
  });
}

export function toFlow(workflow) {
  const nodes = workflow.nodes.map((n) => ({
    id: n.id,
    type: 'kernel',
    position: { x: 0, y: 0 },
    data: { kind: n.type, params: n.params ?? {} },
  }));
  const edges = workflow.edges.map((e, i) => ({
    id: `e${i}-${e.source}-${e.target}-${e.branch ?? ''}`,
    source: e.source,
    target: e.target,
    sourceHandle: e.branch ?? null,
  }));
  return { nodes: layout(nodes, edges), edges };
}

export function fromFlow(name, nodes, edges) {
  return {
    name,
    nodes: nodes.map((n) => ({ id: n.id, type: n.data.kind, params: n.data.params ?? {} })),
    edges: edges.map((e) => ({
      source: e.source,
      target: e.target,
      branch: e.sourceHandle === 'true' || e.sourceHandle === 'false' ? e.sourceHandle : null,
    })),
  };
}
