import { useRoute } from './router';
import Landing from './pages/Landing.jsx';
import Studio from './pages/Studio.jsx';

export default function App() {
  const route = useRoute();
  return route.startsWith('/studio') ? <Studio /> : <Landing />;
}
