import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import { BikeItem } from "../../types";

interface Summary {
  from_date: string;
  to_date: string;
  revenue: string;
  expenses: string;
  profit: string;
  bookings_count: number;
  avg_ticket: string;
}

interface BikeAnalytics {
  bike_id: number;
  plate_number: string;
  model: string;
  revenue: string;
  expenses: string;
  profit: string;
  profitability_percent: string;
  bookings_count: number;
  rented_days: number;
  idle_days: number;
  utilization_percent: string;
  revenue_per_day: string;
  avg_rental_days: string;
}

interface CategoryAnalytics {
  category: string;
  total: string;
  count: number;
}

interface TimelineItem {
  period: string;
  revenue: string;
  expenses: string;
  bookings_count: number;
}

interface SuspiciousItem {
  bike_id: number;
  model: string;
  plate_number: string;
  category: string;
  recent_count: number;
  prev_count: number;
  message: string;
}

function localDateISO(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function defaultRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 29);
  return {
    from: localDateISO(from),
    to: localDateISO(to),
  };
}

export function OwnerAnalyticsPage() {
  const [{ from, to }, setRange] = useState(defaultRange());
  const [bikeId, setBikeId] = useState<number | null>(null);
  const [bikes, setBikes] = useState<BikeItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [bikeStats, setBikeStats] = useState<BikeAnalytics[]>([]);
  const [categories, setCategories] = useState<CategoryAnalytics[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [suspicious, setSuspicious] = useState<SuspiciousItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showMethodology, setShowMethodology] = useState(false);

  useEffect(() => {
    api
      .get<{ items: BikeItem[] }>("/owner/bikes")
      .then((r) => setBikes(r.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const q: Record<string, any> = { from, to };
    if (bikeId) q.bike_id = bikeId;
    Promise.all([
      api.get<Summary>("/owner/analytics/summary", q),
      api.get<{ items: BikeAnalytics[] }>("/owner/analytics/bikes", { from, to }),
      api.get<{ items: CategoryAnalytics[] }>(
        "/owner/analytics/categories",
        q
      ),
      api.get<{ items: TimelineItem[] }>("/owner/analytics/timeline", {
        ...q,
        granularity: "day",
      }),
      api.get<{ items: SuspiciousItem[] }>("/owner/analytics/suspicious"),
    ])
      .then(([s, b, c, t, sus]) => {
        setSummary(s);
        setBikeStats(b.items);
        setCategories(c.items);
        setTimeline(t.items);
        setSuspicious(sus.items);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [from, to, bikeId]);

  const selectedBikeStats = useMemo(() => {
    if (!bikeId) return null;
    return bikeStats.find((b) => b.bike_id === bikeId) || null;
  }, [bikeId, bikeStats]);

  const filteredSuspicious = useMemo(() => {
    if (!bikeId) return suspicious;
    return suspicious.filter((s) => s.bike_id === bikeId);
  }, [bikeId, suspicious]);

  if (loading && !summary)
    return (
      <div className="page">
        <h1 className="page-title">Аналитика</h1>
        <div className="empty">Загрузка</div>
      </div>
    );

  if (error)
    return (
      <div className="page">
        <h1 className="page-title">Аналитика</h1>
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      </div>
    );

  return (
    <div className="page">
      <h1 className="page-title">Аналитика</h1>

      <button
        className="btn btn-secondary"
        type="button"
        onClick={() => setShowMethodology((value) => !value)}
        style={{ width: "100%", marginBottom: 12 }}
      >
        {showMethodology ? "Скрыть методику расчёта" : "Как считается аналитика?"}
      </button>
      {showMethodology && (
        <div className="card" style={{ marginBottom: 16, fontSize: 13, lineHeight: 1.5 }}>
          <strong>Откуда берутся цифры</strong>
          <ul style={{ paddingLeft: 18, margin: "8px 0 0" }}>
            <li><b>Выручка:</b> сумма total_price завершённых аренд (status = completed), начавшихся в выбранном периоде. Сумма включает продления и относится к дате начала аренды.</li>
            <li><b>Расходы:</b> записи из раздела расходов по дате расхода. При выборе байка учитываются только расходы этого байка.</li>
            <li><b>Прибыль:</b> выручка минус расходы. Это операционная разница, не бухгалтерская чистая прибыль.</li>
            <li><b>Средний чек:</b> выручка, делённая на количество завершённых аренд.</li>
            <li><b>Загрузка байка:</b> дни пересечения активных и завершённых аренд с выбранным периодом, делённые на число календарных дней периода. Ожидающие заявки не считаются арендой.</li>
            <li><b>Средняя аренда:</b> средняя полная длительность завершённых аренд, начавшихся в выбранном периоде.</li>
            <li><b>Предупреждения:</b> ищут повторные расходы одной категории по байку: минимум 2 за последние 30 дней и не более 1 за предыдущие 60 дней. Топливо исключается.</li>
          </ul>
        </div>
      )}

      <div className="row" style={{ gap: 8, marginBottom: 12 }}>
        <div style={{ flex: 1 }}>
          <label className="label">С</label>
          <input
            className="input"
            type="date"
            value={from}
            onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label className="label">По</label>
          <input
            className="input"
            type="date"
            value={to}
            onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))}
          />
        </div>
      </div>

      <label className="label">Байк</label>
      <select
        className="input"
        value={bikeId ?? ""}
        onChange={(e) =>
          setBikeId(e.target.value === "" ? null : Number(e.target.value))
        }
        style={{ marginBottom: 16 }}
      >
        <option value="">Все байки</option>
        {bikes.map((b) => (
          <option key={b.id} value={b.id}>
            {b.model} ({b.plate_number})
          </option>
        ))}
      </select>

      {filteredSuspicious.length > 0 && (
        <>
          <div className="section-title">Предупреждения</div>
          <div className="col" style={{ gap: 10, marginBottom: 16 }}>
            {filteredSuspicious.map((s) => (
              <div
                key={`${s.bike_id}-${s.category}`}
                className="card"
                style={{
                  background: "rgba(255,159,10,0.08)",
                  borderColor: "rgba(255,159,10,0.3)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 6,
                  }}
                >
                  <div style={{ fontWeight: 600 }}>
                    {s.model} · {s.plate_number}
                  </div>
                  <span className="badge badge-pending">{s.category}</span>
                </div>
                <div className="muted" style={{ fontSize: 13 }}>
                  {s.message}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {summary && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
            marginBottom: 16,
          }}
        >
          <Stat
            label="Выручка"
            value={formatMoney(summary.revenue)}
            color="var(--success)"
          />
          <Stat
            label="Расходы"
            value={formatMoney(summary.expenses)}
            color="var(--warning)"
          />
          <Stat
            label="Прибыль"
            value={formatMoney(summary.profit)}
            color="var(--accent)"
            wide
          />
          <Stat label="Завершённых аренд" value={String(summary.bookings_count)} />
          <Stat label="Средний чек" value={formatMoney(summary.avg_ticket)} />
        </div>
      )}

      {selectedBikeStats && (
        <>
          <div className="section-title">Детали байка</div>
          <div className="card" style={{ padding: 14, marginBottom: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 10, fontSize: 15 }}>
              {selectedBikeStats.model} · {selectedBikeStats.plate_number}
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
                fontSize: 14,
              }}
            >
              <Detail label="Выручка" value={formatMoney(selectedBikeStats.revenue)} />
              <Detail label="Расходы" value={formatMoney(selectedBikeStats.expenses)} />
              <Detail
                label="Прибыль"
                value={formatMoney(selectedBikeStats.profit)}
                color="var(--success)"
              />
              <Detail
                label="Маржа"
                value={`${selectedBikeStats.profitability_percent}%`}
              />
              <Detail
                label="Выручка/день"
                value={formatMoney(selectedBikeStats.revenue_per_day)}
              />
              <Detail
                label="Средняя аренда"
                value={`${selectedBikeStats.avg_rental_days} дн.`}
              />
              <Detail
                label="Дней в аренде"
                value={String(selectedBikeStats.rented_days)}
              />
              <Detail
                label="Дней простоя"
                value={String(selectedBikeStats.idle_days)}
              />
              <Detail
                label="Загрузка"
                value={`${selectedBikeStats.utilization_percent}%`}
                wide
              />
            </div>
          </div>
        </>
      )}



      {categories.length > 0 && (
        <>
          <div className="section-title">Расходы по категориям</div>
          <div className="col" style={{ gap: 8, marginBottom: 16 }}>
            {categories.map((c) => (
              <div
                key={c.category}
                className="card"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: 12,
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{c.category}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {c.count} раз
                  </div>
                </div>
                <div style={{ fontWeight: 700 }}>{formatMoney(c.total)}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {timeline.length > 0 && (
        <>
          <div className="section-title">По дням</div>
          <div className="card" style={{ padding: 12, marginBottom: 16 }}>
            {timeline.map((t) => (
              <div
                key={t.period}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "6px 0",
                  fontSize: 13,
                  borderBottom: "1px solid var(--border)",
                }}
              >
                <span className="muted">{formatDate(t.period)}</span>
                <span style={{ color: "var(--success)" }}>
                  +{formatMoney(t.revenue)}
                </span>
                <span style={{ color: "var(--warning)" }}>
                  −{formatMoney(t.expenses)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  color,
  wide,
}: {
  label: string;
  value: string;
  color?: string;
  wide?: boolean;
}) {
  return (
    <div
      className="card"
      style={{ gridColumn: wide ? "1 / -1" : undefined, padding: 14 }}
    >
      <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function Detail({
  label,
  value,
  color,
  wide,
}: {
  label: string;
  value: string;
  color?: string;
  wide?: boolean;
}) {
  return (
    <div style={{ gridColumn: wide ? "1 / -1" : undefined }}>
      <div className="muted" style={{ fontSize: 12 }}>
        {label}
      </div>
      <div style={{ fontWeight: 600, color }}>{value}</div>
    </div>
  );
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 VND";
  return n.toLocaleString("ru-RU") + " VND";
}

function formatDate(d: string): string {
  const dt = new Date(d);
  return dt.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
  });
}
