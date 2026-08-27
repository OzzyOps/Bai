import { Navigate, Route, Routes } from 'react-router-dom';

import { RecordsPage } from './routes/RecordsPage';
import { QueuePage } from './routes/QueuePage';
import { RecordDetailPage } from './routes/RecordDetailPage';

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/records" replace />} />
      <Route path="/records" element={<RecordsPage />} />
      <Route path="/records/:id" element={<RecordDetailPage />} />
      <Route path="/queue" element={<QueuePage />} />
    </Routes>
  );
}
