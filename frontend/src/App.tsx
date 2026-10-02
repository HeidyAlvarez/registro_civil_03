import { Navigate, Route, Routes } from 'react-router-dom'
import { InternalAiGate } from '@/components/layout/internal-ai-gate'
import { InternalLayout } from '@/components/layout/internal-layout'
import { PublicLayout } from '@/components/layout/public-layout'
import { LoginPage } from '@/pages/auth/login'
import { AiHubPage, AssistantPage } from '@/pages/ia/assistant'
import { DemandPage, ScheduleSuggestionPage } from '@/pages/ia/insights'
import { NotificationsPage } from '@/pages/ia/notifications'
import { AiDashboardPage } from '@/pages/internal/ai-dashboard'
import { InternalAssistantPage } from '@/pages/internal/control-assistant'
import { AppointmentsPage } from '@/pages/internal/appointments'
import { DashboardPage } from '@/pages/internal/dashboard'
import { AuditPage, CatalogManagementPage, FinancialReportPage, ScheduleBlocksPage } from '@/pages/internal/management'
import { ScannerPage } from '@/pages/internal/scanner'
import { AppointmentLookupPage } from '@/pages/public/appointment-lookup'
import { AppointmentWizardPage } from '@/pages/public/appointment-wizard'
import { CatalogPage } from '@/pages/public/catalog'
import { HomePage } from '@/pages/public/home'
import { LocationPage } from '@/pages/public/location'

function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<HomePage />} />
        <Route path="agendar-cita" element={<AppointmentWizardPage />} />
        <Route path="consultar" element={<AppointmentLookupPage />} />
        <Route path="cancelar" element={<AppointmentLookupPage cancel />} />
        <Route path="tramites" element={<CatalogPage />} />
        <Route path="ubicacion" element={<LocationPage />} />
        <Route path="inteligencia" element={<AiHubPage />} />
        <Route path="inteligencia/asistente" element={<AssistantPage />} />
        <Route path="inteligencia/afluencia" element={<DemandPage />} />
        <Route path="inteligencia/horario" element={<ScheduleSuggestionPage />} />
        <Route path="inteligencia/notificaciones" element={<NotificationsPage />} />
      </Route>
      <Route path="acceso" element={<LoginPage />} />
      <Route path="panel" element={<InternalLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="agenda" element={<AppointmentsPage />} />
        <Route path="escaner" element={<ScannerPage />} />
        <Route path="caja" element={<AppointmentsPage mode="cash" />} />
        <Route path="historial" element={<AppointmentsPage mode="history" />} />
        <Route path="bitacora" element={<AuditPage />} />
        <Route path="reporte" element={<FinancialReportPage />} />
        <Route path="horarios" element={<ScheduleBlocksPage />} />
        <Route path="catalogo" element={<CatalogManagementPage />} />
        <Route path="ia" element={<InternalAiGate />}>
          <Route index element={<AiDashboardPage />} />
          <Route path="asistente" element={<InternalAssistantPage />} />
        </Route>
      </Route>
      <Route path="oficial" element={<Navigate to="/panel" replace />} />
      <Route path="capturista" element={<Navigate to="/panel" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
