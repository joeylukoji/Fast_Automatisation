// Conversion entre le schéma Kernel (source de vérité) et le format React Flow.
import dagre from '@dagrejs/dagre';

export const NODE_SIZE = 100; // nœud carré, façon n8n
const GAP_X = 120;

export function layout(nodes, edges) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', nodesep: 90, ranksep: GAP_X });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_SIZE, height: NODE_SIZE + 40 }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const { x, y } = g.node(n.id);
    return { ...n, position: { x: x - NODE_SIZE / 2, y: y - NODE_SIZE / 2 } };
  });
}

export const edgeId = (source, handle, target) => `e-${source}-${handle ?? 'out'}-${target}`;

export function toFlow(workflow) {
  const nodes = workflow.nodes.map((n) => ({
    id: n.id, type: 'kernel', position: { x: 0, y: 0 }, data: { kind: n.type, params: n.params ?? {} },
  }));
  const edges = workflow.edges.map((e) => ({
    id: edgeId(e.source, e.branch, e.target), type: 'kernel', source: e.source, target: e.target,
    sourceHandle: e.branch ?? null,
  }));
  return { nodes: layout(nodes, edges), edges };
}

export function fromFlow(name, nodes, edges) {
  return {
    name,
    nodes: nodes.map((n) => ({ id: n.id, type: n.data.kind, params: n.data.params ?? {} })),
    edges: edges.map((e) => ({
      source: e.source, target: e.target,
      branch: e.sourceHandle === 'true' || e.sourceHandle === 'false' ? e.sourceHandle : null,
    })),
  };
}

export { GAP_X };
