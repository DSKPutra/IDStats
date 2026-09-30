import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { DatasetProvider } from '@/context/DatasetContext'
import { Dashboard } from '@/pages/Dashboard'
import { MethodRoute } from '@/pages/MethodRoute'
import { NotFound } from '@/pages/NotFound'

export default function App() {
  return (
    <DatasetProvider>
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path=":categoryId/:methodId" element={<MethodRoute />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </DatasetProvider>
  )
}
