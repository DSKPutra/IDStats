import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { DatasetProvider } from '@/context/DatasetContext'
import { HistoryProvider } from '@/context/HistoryContext'
import { Dashboard } from '@/pages/Dashboard'
import { MethodRoute } from '@/pages/MethodRoute'
import { NotFound } from '@/pages/NotFound'

const ReportPage = lazy(() => import('@/pages/Report').then((m) => ({ default: m.ReportPage })))

export default function App() {
  return (
    <DatasetProvider>
      <HistoryProvider>
        <BrowserRouter>
          <Routes>
            <Route
              path="laporan"
              element={
                <Suspense fallback={<p className="p-10 text-center">Menyiapkan laporan…</p>}>
                  <ReportPage />
                </Suspense>
              }
            />
            <Route element={<AppShell />}>
              <Route index element={<Dashboard />} />
              <Route path=":categoryId/:methodId" element={<MethodRoute />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </HistoryProvider>
    </DatasetProvider>
  )
}
