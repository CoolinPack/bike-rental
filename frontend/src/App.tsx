import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import {
  IconCatalog,
  IconHistory,
  IconGarage,
  IconExpenses,
  IconRequests,
  IconAnalytics,
  IconProfile,
  IconSummary,
  IconParks,
  IconPayments,
} from "./components/icons";
import { api } from "./api/client";
import { useAuth } from "./store/auth";
import { Me } from "./types";
import { ClientCatalogPage } from "./pages/client/Catalog";
import { ClientHistoryPage } from "./pages/client/History";
import { OwnerGaragePage } from "./pages/owner/Garage";
import { OwnerExpensesPage } from "./pages/owner/Expenses";
import { OwnerAnalyticsPage } from "./pages/owner/Analytics";
import { OwnerRequestsPage } from "./pages/owner/Requests";
import { OwnerProfilePage } from "./pages/owner/Profile";
import { SuperParksPage } from "./pages/superadmin/Parks";
import { SuperSummaryPage } from "./pages/superadmin/Summary";
import { SuperPaymentsPage } from "./pages/superadmin/Payments";

const DEV_INIT_DATA_KEY = "dev_init_data";

function getInitData(): string | null {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.initData) return tg.initData;
  return localStorage.getItem(DEV_INIT_DATA_KEY);
}

function App() {
  const { me, setMe, setInitData } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [devInput, setDevInput] = useState(
    localStorage.getItem(DEV_INIT_DATA_KEY) || ""
  );

  useEffect(() => {
    const initData = getInitData();
    if (!initData) {
      setLoading(false);
      return;
    }
    setInitData(initData);
    (window as any).Telegram?.WebApp?.ready?.();
    (window as any).Telegram?.WebApp?.expand?.();

    api
      .get<Me>("/auth/me")
      .then((data) => setMe(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [setMe, setInitData]);

  if (loading) return <div className="empty">Загрузка…</div>;

  if (!me) {
    return (
      <div className="page">
        <h1 className="page-title">Bike Rental</h1>
        <div className="card col">
          <div className="muted">
            Открой это приложение из Telegram — или вставь тестовый initData.
          </div>
          <textarea
            className="input"
            style={{ minHeight: 100, fontFamily: "monospace", fontSize: 12 }}
            placeholder="auth_date=...&user=...&hash=..."
            value={devInput}
            onChange={(e) => setDevInput(e.target.value)}
          />
          <button
            className="btn"
            onClick={() => {
              localStorage.setItem(DEV_INIT_DATA_KEY, devInput.trim());
              window.location.reload();
            }}
          >
            Войти
          </button>
          {error && <div style={{ color: "var(--danger)" }}>{error}</div>}
        </div>
      </div>
    );
  }

  if (me.role === "client") {
    return (
      <Routes>
        <Route
          element={
            <Layout
              tabs={[
                { to: "/catalog", label: "Каталог", icon: <IconCatalog /> },
                { to: "/history", label: "История", icon: <IconHistory /> },
              ]}
            />
          }
        >
          <Route path="/catalog" element={<ClientCatalogPage />} />
          <Route path="/history" element={<ClientHistoryPage />} />
          <Route path="*" element={<Navigate to="/catalog" replace />} />
        </Route>
      </Routes>
    );
  }

  if (me.role === "owner") {
    return (
      <Routes>
        <Route
          element={
            <Layout
              tabs={[
                { to: "/garage", label: "Гараж", icon: <IconGarage /> },
                { to: "/expenses", label: "Расходы", icon: <IconExpenses /> },
                { to: "/requests", label: "Заявки", icon: <IconRequests /> },
                { to: "/analytics", label: "Аналитика", icon: <IconAnalytics /> },
                { to: "/profile", label: "Профиль", icon: <IconProfile /> },
              ]}
            />
          }
        >
          <Route path="/garage" element={<OwnerGaragePage />} />
          <Route path="/expenses" element={<OwnerExpensesPage />} />
          <Route path="/requests" element={<OwnerRequestsPage />} />
          <Route path="/analytics" element={<OwnerAnalyticsPage />} />
          <Route path="/profile" element={<OwnerProfilePage />} />
          <Route path="*" element={<Navigate to="/garage" replace />} />
        </Route>
      </Routes>
    );
  }

  // super_admin
  return (
    <Routes>
      <Route
        element={
          <Layout
            tabs={[
              { to: "/summary", label: "Сводка", icon: <IconSummary /> },
              { to: "/parks", label: "Парки", icon: <IconParks /> },
              { to: "/payments", label: "Оплаты", icon: <IconPayments /> },
            ]}
          />
        }
      >
        <Route path="/summary" element={<SuperSummaryPage />} />
        <Route path="/parks" element={<SuperParksPage />} />
        <Route path="/payments" element={<SuperPaymentsPage />} />
        <Route path="*" element={<Navigate to="/summary" replace />} />
      </Route>
    </Routes>
  );
}

export default App;