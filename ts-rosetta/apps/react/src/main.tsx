import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import '@rosetta/core/styles.css';
import App from './App';
import Board from './Board';

// Tiny hash "router": #board shows the live board, anything else the tasks app.
function Root() {
  const [hash, setHash] = useState(location.hash);
  useEffect(() => {
    const onChange = () => setHash(location.hash);
    addEventListener('hashchange', onChange);
    return () => removeEventListener('hashchange', onChange);
  }, []);
  return hash === '#board' ? <Board /> : <App />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
