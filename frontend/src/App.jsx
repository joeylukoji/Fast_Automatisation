import { useRoute } from './router';
import Landing from './pages/Landing.jsx';
import Studio from './pages/Studio.jsx';
import Apps from './pages/Apps.jsx';

export default function App() {
  const route = useRoute();
  if (route.startsWith('/studio')) return <Studio />;
  if (route.startsWith('/apps')) return <Apps />;
  return <Landing />;
}
