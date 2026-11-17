import { useEffect, useState } from "react";
import { api } from "../../api/client";

interface ParkRevenue {
  park_id: number;
  name: string;
  total_paid: string;
  last_paid_at: string | null;
  subscription_expires_at: string | null;
  is_active: boolean;
  subscription_plan: string;
  bikes_limit: number;
  is_expired: boolean;
  days_left: number;
}

interface MyRevenue {
  total_confirmed_revenue: string;
  this_month_revenue: string;
  parks_total: number;
  parks_active: number;
  parks_expired: number;
  parks_disabled: number;
  parks: ParkRevenue[];
}

export function SuperSummaryPage() {
  const [data, setData] = useState<MyRevenue | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<MyRevenue>("/super/my-revenue")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error)
    return (
      <div className="page">
        <h1 className="page-title">Сводка</h1>
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      </div>
    );

  if (!data)
    return (
      <div className="page">
        <div className="empty">Загрузка</div>
      </div>
    );

  const sorted = [...data.parks].sort((a, b) => {
    if (a.is_expired !== b.is_expired) return a.is_expired ? -1 : 1;
    if (a.is_active !== b.is_active) return a.is_active ? 1 : -1;
    return a.days_left - b.days_left;
  });

  return (
    <div className="page">
      <h1 className="page-title">Сводка</h1>

      <div className="row" style={{ gap: 12, marginBottom: 12 }}>
        <div className="card" style={{ flex: 1, padding: 16 }}>
          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
            Всего оплачено
          </div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>
            {formatMoney(data.total_confirmed_revenue)}
          </div>
        </div>
        <div className="card" style={{ flex: 1, padding: 16 }}>
          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
            В этом месяце
          </div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "var(--success)",
            }}
          >
            {formatMoney(data.this_month_revenue)}
          </div>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <Stat label="Всего" value={data.parks_total} />
        <Stat label="Активны" value={data.parks_active} color="var(--success)" />
        <Stat
          label="Истекли"
          value={data.parks_expired}
          color={data.parks_expired > 0 ? "var(--danger)" : undefined}
        />
      </div>

      <div className="section-title">Парки</div>

      <div className="col" style={{ gap: 10 }}>
        {sorted.map((p) => (
          <ParkRevenueCard key={p.park_id} park={p} />
        ))}
      </div>
    </div>
  );
}

function ParkRevenueCard({ park }: { park: ParkRevenue }) {
  let statusText = "";
  let statusClass = "";
  if (!park.is_active) {
    statusText = "Отключён";
    statusClass = "badge-cancelled";
  } else if (park.is_expired) {
    statusText = "Истёк";
    statusClass = "badge-maintenance";
  } else if (park.days_left <= 7) {
    statusText = `Осталось ${park.days_left} дн.`;
    statusClass = "badge-pending";
  } else {
    statusText = `${park.days_left} дн.`;
    statusClass = "badge-active";
  }

  return (
    <div className="card" style={{ padding: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 8,
          marginBottom: 6,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{park.name}</div>
          <div className="muted" style={{ fontSize: 12 }}>
            {park.subscription_plan === "pro" ? "Про" : "Старт"} · до{" "}
            {park.bikes_limit} байков
          </div>
        </div>
        <span className={`badge ${statusClass}`}>{statusText}</span>
      </div>

      <div className="row" style={{ gap: 12, fontSize: 13, color: "var(--text-secondary)" }}>
        <span>Оплачено: {formatMoney(park.total_paid)}</span>
        {park.last_paid_at && (
          <span>Последний: {formatDate(park.last_paid_at)}</span>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="card" style={{ padding: 14 }}>
      <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>
        {value}
      </div>
    </div>
  );
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 $";
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 2 }) + " $";
}

function formatDate(d: string): string {
  const dt = new Date(d);
  return dt.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
