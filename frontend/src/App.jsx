import { useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { useStore } from './store';
import PromptBar from './components/PromptBar.jsx';
import GraphEditor from './components/GraphEditor.jsx';
import NodePanel from './components/NodePanel.jsx';
import RunLog from './components/RunLog.jsx';

export default function App() {
  const loadSpecs = useStore((s) => s.loadSpecs);
  const error = useStore((s) => s.error);
  const info = useStore((s) => s.info);

  useEffect(() => {
    loadSpecs();
  }, [loadSpecs]);

  return (
    <div className="app">
      <header className="topbar">
        <h1>Kernel</h1>
        <PromptBar />
      </header>
      {error && <div className="banner error">{error}</div>}
      {info && !error && <div className="banner info">{info}</div>}
      <main className="workspace">
        <ReactFlowProvider>
          <GraphEditor />
        </ReactFlowProvider>
        <aside className="sidebar">
          <NodePanel />
          <RunLog />
        </aside>
      </main>
    </div>
  );
}
