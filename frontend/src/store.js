import { create } from 'zustand';
import { addEdge, applyEdgeChanges, applyNodeChanges } from '@xyflow/react';
import { api } from './api';
import { edgeId, fromFlow, GAP_X, layout, NODE_SIZE, toFlow } from './convert';

let validateTimer = null;

const uniqueId = (kind, nodes) => {
  const base = kind.split('_')[0];
  let i = 1;
  while (nodes.some((n) => n.id === `${base}_${i}`)) i += 1;
  return `${base}_${i}`;
};

const defaultsOf = (spec) => Object.fromEntries(
  Object.entries(spec?.params_schema?.properties ?? {})
    .filter(([, p]) => p.default !== undefined)
    .map(([k, p]) => [k, p.default]),
);

export const useStore = create((set, get) => ({
  specs: [],
  health: null,
  name: 'Nouveau workflow',
  workflowId: null,
  dirty: false,
  nodes: [],
  edges: [],
  runResult: null,
  generation: null, // { source, intent, confidence, attempts }
  validationErrors: [],
  busy: null, // 'generate' | 'run' | 'save' | null
  error: null,
  info: null,
  // Interface
  ndvId: null, // nœud ouvert dans la fenêtre de détail (façon n8n)
  creator: null, // { source, handle } | { edge } | {} : panneau d'ajout de nœud ouvert
  logOpen: false,
  savedList: null,

  async init() {
    try {
      const [specs, health] = await Promise.all([api.nodes(), api.health()]);
      set({ specs, health });
    } catch (e) {
      set({ error: `Backend injoignable : ${e.message}` });
    }
  },

  // ---------- Génération / exécution ----------
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
        name: res.workflow.name, nodes, edges, workflowId: null, dirty: true,
        generation: { source: res.source, intent: res.intent, confidence: res.confidence, attempts: res.attempts },
      });
      get().scheduleValidate();
    } catch (e) {
      set({ error: e.message });
    } finally {
      set({ busy: null });
    }
  },

  async run(dryRun) {
    const { name, nodes, edges, workflowId } = get();
    set({ busy: 'run', error: null, info: null });
    try {
      const result = await api.run(fromFlow(name, nodes, edges), { dryRun, approved: !dryRun, workflowId });
      set({
        runResult: result, logOpen: true,
        error: result.validation_errors.length ? result.validation_errors.join(' ; ') : null,
      });
    } catch (e) {
      set({ error: e.message });
    } finally {
      set({ busy: null });
    }
  },

  scheduleValidate() {
    clearTimeout(validateTimer);
    validateTimer = setTimeout(async () => {
      const { name, nodes, edges } = get();
      if (!nodes.length) return set({ validationErrors: [] });
      try {
        const { errors } = await api.validate(fromFlow(name, nodes, edges));
        set({ validationErrors: errors });
      } catch { /* l'erreur réseau est déjà signalée ailleurs */ }
    }, 350);
  },

  // ---------- Enregistrement ----------
  async save() {
    const { name, nodes, edges, workflowId } = get();
    set({ busy: 'save', error: null });
    try {
      const rec = await api.saveWorkflow(fromFlow(name, nodes, edges), workflowId);
      set({ workflowId: rec.id, dirty: false, info: 'Workflow enregistré.' });
      setTimeout(() => set({ info: null }), 2000);
    } catch (e) {
      set({ error: e.message });
    } finally {
      set({ busy: null });
    }
  },

  async loadList() {
    try { set({ savedList: await api.workflows() }); } catch (e) { set({ error: e.message }); }
  },

  open(record) {
    const { nodes, edges } = toFlow(record.workflow);
    set({ name: record.workflow.name, workflowId: record.id, nodes, edges, dirty: false, runResult: null,
      generation: null, savedList: null });
    get().scheduleValidate();
  },

  newWorkflow() {
    set({ name: 'Nouveau workflow', workflowId: null, nodes: [], edges: [], dirty: false, runResult: null,
      generation: null, validationErrors: [] });
  },

  async remove(id) {
    await api.deleteWorkflow(id);
    if (get().workflowId === id) set({ workflowId: null, dirty: true });
    get().loadList();
  },

  rename: (name) => set({ name, dirty: true }),

  // ---------- Édition du graphe ----------
  touch() { set({ dirty: true, runResult: null }); get().scheduleValidate(); },

  // Ajoute un nœud ; si `creator` porte une source ou une arête, il est branché automatiquement (comme n8n).
  addNode(kind) {
    const { specs, nodes, edges, creator } = get();
    const spec = specs.find((s) => s.type === kind);
    const id = uniqueId(kind, nodes);
    let position = { x: 80 + nodes.length * 40, y: 120 + nodes.length * 20 };
    let newEdges = edges;
    const src = creator?.source && nodes.find((n) => n.id === creator.source);
    if (src) {
      const offsetY = creator.handle === 'true' ? -90 : creator.handle === 'false' ? 90 : 0;
      position = { x: src.position.x + NODE_SIZE + GAP_X, y: src.position.y + offsetY };
      newEdges = [...edges, { id: edgeId(src.id, creator.handle, id), type: 'kernel', source: src.id,
        target: id, sourceHandle: creator.handle ?? null }];
    } else if (creator?.edge) {
      const e = edges.find((x) => x.id === creator.edge);
      const a = nodes.find((n) => n.id === e?.source);
      const b = nodes.find((n) => n.id === e?.target);
      if (e && a && b) {
        position = { x: (a.position.x + b.position.x) / 2, y: (a.position.y + b.position.y) / 2 };
        newEdges = [...edges.filter((x) => x.id !== e.id),
          { id: edgeId(a.id, e.sourceHandle, id), type: 'kernel', source: a.id, target: id, sourceHandle: e.sourceHandle },
          { id: edgeId(id, null, b.id), type: 'kernel', source: id, target: b.id, sourceHandle: null }];
      }
    }
    const node = { id, type: 'kernel', position, data: { kind, params: defaultsOf(spec) } };
    const allNodes = [...nodes, node];
    set({ nodes: creator?.edge ? layout(allNodes, newEdges) : allNodes, edges: newEdges, creator: null, ndvId: id });
    get().touch();
  },

  updateParams(id, params) {
    set((s) => ({ nodes: s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, params } } : n)) }));
    get().touch();
  },

  deleteNode(id) {
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      edges: s.edges.filter((e) => e.source !== id && e.target !== id),
      ndvId: null,
    }));
    get().touch();
  },

  deleteEdge(id) {
    set((s) => ({ edges: s.edges.filter((e) => e.id !== id) }));
    get().touch();
  },

  tidy() { set((s) => ({ nodes: layout(s.nodes, s.edges) })); },

  openCreator: (creator) => set({ creator }),
  closeCreator: () => set({ creator: null }),
  openNdv: (id) => set({ ndvId: id }),
  closeNdv: () => set({ ndvId: null }),
  toggleLog: () => set((s) => ({ logOpen: !s.logOpen })),
  clearError: () => set({ error: null }),

  onNodesChange(changes) {
    set((s) => ({ nodes: applyNodeChanges(changes, s.nodes) }));
    if (changes.some((c) => c.type === 'remove')) get().touch();
  },
  onEdgesChange(changes) {
    set((s) => ({ edges: applyEdgeChanges(changes, s.edges) }));
    if (changes.some((c) => c.type === 'remove')) get().touch();
  },
  onConnect(conn) {
    set((s) => ({ edges: addEdge({ ...conn, type: 'kernel', id: edgeId(conn.source, conn.sourceHandle, conn.target) }, s.edges) }));
    get().touch();
  },
}));
