import { create } from 'zustand';
import { addEdge, applyEdgeChanges, applyNodeChanges } from '@xyflow/react';
import { api } from './api';
import { fromFlow, toFlow } from './convert';

let counter = 0;

export const useStore = create((set, get) => ({
  specs: [], // catalogue des blocs (GET /api/nodes)
  name: 'Nouveau workflow',
  nodes: [],
  edges: [],
  selectedId: null,
  runResult: null,
  busy: null, // 'generate' | 'run' | null
  error: null,
  info: null,

  async loadSpecs() {
    try {
      set({ specs: await api.nodes() });
    } catch (e) {
      set({ error: `Backend injoignable : ${e.message}` });
    }
  },

  async generate(prompt) {
    set({ busy: 'generate', error: null, info: null, runResult: null });
    try {
      const res = await api.generate(prompt);
      if (!res.workflow) {
        set({ error: `Génération impossible après ${res.attempts} essais : ${res.errors.join(' ; ')}` });
        return;
      }
      const { nodes, edges } = toFlow(res.workflow);
      set({
        name: res.workflow.name,
        nodes,
        edges,
        selectedId: null,
        info: res.attempts > 1 ? `Workflow généré après ${res.attempts} tentatives (réparation automatique).` : 'Workflow généré.',
      });
    } catch (e) {
      set({ error: e.message });
    } finally {
      set({ busy: null });
    }
  },

  // dryRun=true : simulation ; false : exécution réelle (confirmée par l'utilisateur côté UI)
  async run(dryRun) {
    const { name, nodes, edges } = get();
    set({ busy: 'run', error: null, info: null });
    try {
      const result = await api.run(fromFlow(name, nodes, edges), { dryRun, approved: !dryRun });
      set({ runResult: result, error: result.validation_errors.length ? result.validation_errors.join(' ; ') : null });
    } catch (e) {
      set({ error: e.message });
    } finally {
      set({ busy: null });
    }
  },

  addNode(kind) {
    const spec = get().specs.find((s) => s.type === kind);
    const defaults = Object.fromEntries(
      Object.entries(spec?.params_schema?.properties ?? {})
        .filter(([, p]) => p.default !== undefined)
        .map(([k, p]) => [k, p.default]),
    );
    const id = `${kind}_${++counter}`;
    set((s) => ({
      nodes: [
        ...s.nodes,
        { id, type: 'kernel', position: { x: 40 + 30 * counter, y: 40 + 30 * counter }, data: { kind, params: defaults } },
      ],
      selectedId: id,
    }));
  },

  updateParams(id, params) {
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, params } } : n)),
    }));
  },

  deleteNode(id) {
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      edges: s.edges.filter((e) => e.source !== id && e.target !== id),
      selectedId: null,
    }));
  },

  select: (id) => set({ selectedId: id }),
  onNodesChange: (changes) => set((s) => ({ nodes: applyNodeChanges(changes, s.nodes) })),
  onEdgesChange: (changes) => set((s) => ({ edges: applyEdgeChanges(changes, s.edges) })),
  onConnect: (conn) => set((s) => ({ edges: addEdge(conn, s.edges) })),
}));
