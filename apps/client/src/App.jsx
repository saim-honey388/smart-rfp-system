import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import {
  Dashboard,
  CreateRFP,
  OpenRFPs,
  RFPDetail,
  ProposalDetail,
  Comparison,
  Documents,
  Settings
} from './pages';

import { RFPProvider } from './context/RFPContext';
import { ToastProvider } from './components/Toast';

function App() {
  return (
    <RFPProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="create-rfp/:id?" element={<CreateRFP />} />
              <Route path="open-rfps" element={<OpenRFPs />} />
              <Route path="rfp/:id" element={<RFPDetail />} />
              <Route path="proposal/:id" element={<ProposalDetail />} />
              <Route path="comparisons" element={<Comparison />} />
              <Route path="documents" element={<Documents />} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </RFPProvider>
  );
}

export default App;
