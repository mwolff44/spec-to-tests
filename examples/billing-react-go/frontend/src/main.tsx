import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RateCalculator } from './components/RateCalculator';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RateCalculator />
  </StrictMode>,
);
