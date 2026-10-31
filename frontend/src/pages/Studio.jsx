import { useEffect, useState } from 'react';
import { Background, BackgroundVariant, Controls, MiniMap, ReactFlow, ReactFlowProvider, useReactFlow } from '@xyflow/react';
import Icon from '../icons.jsx';
import { useStore } from '../store';
import KernelNode from '../studio/KernelNode.jsx';
import KernelEdge, { EdgeMarkers } from '../studio/KernelEdge.jsx';
import NodeCreator from '../studio/NodeCreator.jsx';
import Ndv from '../studio/Ndv.jsx';
import LogPanel from '../studio/LogPanel.jsx';

const nodeTypes = { kernel: KernelNode };
const edgeTypes = { kernel: KernelEdge };
const SOURCE = { gemma: 'Gemma 4', local: 'Modèle local', mock: 'Démo (mock)' };
const EXAMPLES = [
  'Vérifie https://monsite.fr : si 200 Telegram, sinon mail à ops@exemple.fr',
  'Récupère https://news.site/rss, résume-le et envoie-le sur Telegram',
  'Résume ce texte et envoie-le par mail à equipe@exemple.fr',
];

function PromptDock() {
  const [prompt, setPrompt] = useState('');
  const busy = useStore((s) => s.busy);
  const gen = useStore((s) => s.generation);
  const generate = useStore((s) => s.generate);
  const submit = (e) => { e.preventDefault(); if (prompt.trim()) generate(prompt.trim()); };
  return (
    <div className="k-dock">
      <form onSubmit={submit}>
        <Icon name="llm" size={16} className="k-dock-icon" />
        <input value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={busy !== null}
          placeholder="Décrivez votre automatisation en français…" aria-label="Description de l'automatisation" />
        <button className="btn dark" disabled={busy !== null || !prompt.trim()}>
          {busy === 'generate' ? 'Génération…' : 'Générer'} <Icon name="arrow" size={14} />
        </button>
      </form>
      {gen && (
        <div className="k-dock-meta mono">
          {SOURCE[gen.source] ?? gen.source}
          {gen.intent && <> · intention <b>{gen.intent}</b> · confiance {Math.round(gen.confidence * 100)} %</>}
          {gen.attempts > 1 && <> · réparé en {gen.attempts} tentatives</>}
        </div>
      )}
      {!gen && (
        <div className="k-dock-examples">
          {EXAMPLES.map((x) => <button key={x} type="button" className="chip" onClick={() => setPrompt(x)}>{x}</button>)}
        </div>
      )}
    </div>
  );
}

function OpenDialog() {
  const list = useStore((s) => s.savedList);
  const { open, remove } = useStore.getState();
  if (!list) return null;
  return (
    <div className="ndv-overlay" onMouseDown={(e) => e.target === e.currentTarget && useStore.setState({ savedList: null })}>
      <div className="k-dialog">
        <header><h3>Workflows enregistrés</h3>
          <button className="icon-btn" onClick={() => useStore.setState({ savedList: null })}><Icon name="x" /></button></header>
        {list.length === 0 && <p className="muted">Aucun workflow enregistré pour l'instant.</p>}
        <ul className="k-saved">
          {list.map((r) => (
            <li key={r.id}>
              <button className="k-saved-open" onClick={() => open(r)}>
                <strong>{r.workflow.name}</strong>
                <span className="mono muted">{r.workflow.nodes.length} nœuds · {new Date(r.updated_at).toLocaleString('fr-FR')}</span>
              </button>
              <button className="icon-btn" title="Supprimer" onClick={() => remove(r.id)}><Icon name="trash" size={15} /></button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ConfirmRun({ onClose }) {
  const run = useStore((s) => s.run);
  return (
    <div className="ndv-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="k-dialog">
        <header><h3>Exécuter pour de vrai ?</h3></header>
        <p>Les nœuds Telegram, Gmail et Requête HTTP vont <b>réellement</b> envoyer des messages ou des requêtes.
          Vérifiez d'abord le résultat avec « Tester le workflow ».</p>
        <footer>
          <button className="btn ghost" onClick={onClose}>Annuler</button>
          <button className="btn danger" onClick={() => { onClose(); run(false); }}>J'approuve, exécuter</button>
        </footer>
      </div>
    </div>
  );
}

function Header() {
  const name = useStore((s) => s.name);
  const dirty = useStore((s) => s.dirty);
  const workflowId = useStore((s) => s.workflowId);
  const busy = useStore((s) => s.busy);
  const hasNodes = useStore((s) => s.nodes.length > 0);
  const errors = useStore((s) => s.validationErrors);
  const health = useStore((s) => s.health);
  const { rename, save, loadList, newWorkflow, run, tidy } = useStore.getState();
  const [confirm, setConfirm] = useState(false);
  return (
    <header className="k-header">
      <a href="#/" className="brand"><span className="logo-mark" /> <span className="brand-name">Kernel</span></a>
      <span className="k-sep" />
      <input className="k-name" value={name} onChange={(e) => rename(e.target.value)} aria-label="Nom du workflow" />
      <span className="mono muted small">{!workflowId ? 'non enregistré' : dirty ? 'modifié' : 'enregistré'}</span>
      {hasNodes && (errors.length
        ? <span className="pill st-error" title={errors.join('\n')}><Icon name="alert" size={12} /> {errors.length} problème{errors.length > 1 ? 's' : ''}</span>
        : <span className="pill st-success"><Icon name="check" size={12} /> valide</span>)}
      <div className="k-header-right">
        {health && <span className="mono muted small" title="Générateur utilisé par le backend">
          {SOURCE[health.generator] ?? 'aucun générateur'}{health.fallback ? ' · secours local' : ''}</span>}
        <button className="btn ghost" onClick={newWorkflow}>Nouveau</button>
        <button className="btn ghost" onClick={loadList}><Icon name="folder" size={14} /> Ouvrir</button>
        <button className="btn ghost" onClick={tidy} disabled={!hasNodes}>Ranger</button>
        <button className="btn ghost" onClick={save} disabled={!hasNodes || busy !== null}><Icon name="save" size={14} /> Enregistrer</button>
        <button className="btn accent" onClick={() => run(true)} disabled={!hasNodes || busy !== null}>
          <Icon name="flask" size={14} /> {busy === 'run' ? 'Test…' : 'Tester le workflow'}</button>
        <button className="btn danger" onClick={() => setConfirm(true)} disabled={!hasNodes || busy !== null}>
          <Icon name="play" size={13} /> Exécuter</button>
      </div>
      {confirm && <ConfirmRun onClose={() => setConfirm(false)} />}
    </header>
  );
}

function Canvas() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const logOpen = useStore((s) => s.logOpen);
  const { onNodesChange, onEdgesChange, onConnect, openCreator } = useStore.getState();
  const { fitView } = useReactFlow();
  // Recadre quand le journal s'ouvre/se ferme ou qu'un nouveau graphe arrive.
  useEffect(() => { const t = setTimeout(() => fitView({ padding: 0.35, maxZoom: 1.1, duration: 250 }), 60); return () => clearTimeout(t); },
    [logOpen, nodes.length, fitView]);
  return (
    <div className="k-canvas">
      <EdgeMarkers />
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect}
        defaultEdgeOptions={{ type: 'kernel' }} connectionLineStyle={{ stroke: 'var(--rust)', strokeWidth: 2 }}
        fitView fitViewOptions={{ padding: 0.35, maxZoom: 1.1 }} minZoom={0.3} maxZoom={1.8}
        deleteKeyCode={['Backspace', 'Delete']} proOptions={{ hideAttribution: true }}>
        <Background variant={BackgroundVariant.Dots} gap={20} size={1.3} color="var(--dot)" />
        <Controls showInteractive={false} position="bottom-left" />
        {nodes.length > 3 && <MiniMap pannable zoomable position="bottom-right" nodeColor="#d6d3d1" maskColor="rgba(253,252,248,.7)" />}
      </ReactFlow>
      {nodes.length === 0 && (
        <button className="k-empty" onClick={() => openCreator({})}>
          <span className="k-empty-box"><Icon name="plus" size={30} stroke={1.2} /></span>
          <span>Ajouter la première étape…</span>
          <small className="muted">ou décrivez l'automatisation dans la barre ci-dessus</small>
        </button>
      )}
      <button className="k-fab" title="Ajouter un nœud" onClick={() => openCreator({})}><Icon name="plus" size={20} /></button>
    </div>
  );
}

export default function Studio() {
  const init = useStore((s) => s.init);
  const error = useStore((s) => s.error);
  const info = useStore((s) => s.info);
  const clearError = useStore((s) => s.clearError);
  useEffect(() => { init(); }, [init]);
  return (
    <div className="studio">
      <Header />
      <div className="k-main">
        <ReactFlowProvider>
          <Canvas />
          <PromptDock />
          <NodeCreator />
        </ReactFlowProvider>
        {error && <div className="k-toast err" onClick={clearError}><Icon name="alert" size={15} /> {error}</div>}
        {info && !error && <div className="k-toast ok"><Icon name="check" size={15} /> {info}</div>}
      </div>
      <LogPanel />
      <Ndv />
      <OpenDialog />
    </div>
  );
}
