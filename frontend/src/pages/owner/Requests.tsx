import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";

interface OwnerBookingItem {
  id: number;
  park_id: number;
  bike_id: number;
  plate_number: string;
  model: string;
  photos: string[];
  start_date: string;
  end_date: string;
  total_price: string;
  status: "pending" | "active" | "completed" | "cancelled" | "rejected";
  created_at: string;
  client_name: string | null;
  client_phone: string | null;
  client_username: string | null;
  deposit_comment: string | null;
  client_telegram_id: number;
}

type Tab = "pending" | "active" | "completed";

const TAB_LABEL: Record<Tab, string> = {
  pending: "Ожидают",
  active: "Активные",
  completed: "Завершённые",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Ожидает",
  active: "Активна",
  completed: "Завершена",
  cancelled: "Отменена",
  rejected: "Отклонена",
};

export function OwnerRequestsPage() {
  const [tab, setTab] = useState<Tab>("pending");
  const [all, setAll] = useState<OwnerBookingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<number | null>(null);
  const [selected, setSelected] = useState<OwnerBookingItem | null>(null);

  function reload() {
    setLoading(true);
    api
      .get<{ items: OwnerBookingItem[] }>("/owner/requests")
      .then((r) => setAll(r.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
  }, []);

  const grouped = useMemo(() => {
    const pending: OwnerBookingItem[] = [];
    const active: OwnerBookingItem[] = [];
    const completed: OwnerBookingItem[] = [];
    for (const b of all) {
      if (b.status === "pending") pending.push(b);
      else if (b.status === "active") active.push(b);
      else completed.push(b);
    }
    return { pending, active, completed };
  }, [all]);

  async function accept(id: number) {
    if (!confirm("Подтвердить заявку? Байк будет отмечен как арендованный.")) return;
    setActing(id);
    try {
      await api.post(`/owner/requests/${id}/accept`);
      reload();
      setSelected(null);
    } catch (e: any) {
      setError(e.message || "Не удалось принять");
    } finally {
      setActing(null);
    }
  }

  async function complete(id: number) {
    if (!confirm("Завершить аренду и вернуть байк в гараж?")) return;
    setActing(id);
    try {
      await api.post(`/client/bookings/${id}/complete`);
      reload();
      setSelected(null);
    } catch (e: any) {
      setError(e.message || "Не удалось завершить");
    } finally {
      setActing(null);
    }
  }

  async function reject(id: number, reason: string) {
    setActing(id);
    try {
      await api.post(`/owner/requests/${id}/reject`, { reason });
      reload();
      setSelected(null);
    } catch (e: any) {
      setError(e.message || "Не удалось отклонить");
    } finally {
      setActing(null);
    }
  }

  const current =
    tab === "pending"
      ? grouped.pending
      : tab === "active"
      ? grouped.active
      : grouped.completed;

  return (
    <div className="page">
      <h1 className="page-title">Заявки</h1>

      <div className="filter-bar" style={{ marginBottom: 12 }}>
        <button
          className={`chip ${tab === "pending" ? "active" : ""}`}
          onClick={() => setTab("pending")}
        >
          Ожидают ({grouped.pending.length})
        </button>
        <button
          className={`chip ${tab === "active" ? "active" : ""}`}
          onClick={() => setTab("active")}
        >
          Активные ({grouped.active.length})
        </button>
        <button
          className={`chip ${tab === "completed" ? "active" : ""}`}
          onClick={() => setTab("completed")}
        >
          Завершённые
        </button>
      </div>

      {error && (
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      )}
      {loading && <div className="empty">Загрузка</div>}

      {!loading && current.length === 0 && (
        <div className="empty">
          {tab === "pending"
            ? "Нет новых заявок"
            : tab === "active"
            ? "Нет активных аренд"
            : "Завершённых пока нет"}
        </div>
      )}

      <div className="col" style={{ gap: 10 }}>
        {current.map((b) => (
          <PreviewCard
            key={b.id}
            booking={b}
            onClick={() => setSelected(b)}
          />
        ))}
      </div>

      {selected && (
        <DetailsModal
          booking={selected}
          tab={tab}
          acting={acting === selected.id}
          onClose={() => setSelected(null)}
          onAccept={() => accept(selected.id)}
          onReject={(reason) => reject(selected.id, reason)}
          onComplete={() => complete(selected.id)}
        />
      )}
    </div>
  );
}

function PreviewCard({
  booking,
  onClick,
}: {
  booking: OwnerBookingItem;
  onClick: () => void;
}) {
  const photo = booking.photos?.[0];
  return (
    <div className="card" style={{ padding: 10 }} onClick={onClick}>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        {photo ? (
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 8,
              overflow: "hidden",
              background: "var(--surface-3)",
              flexShrink: 0,
            }}
          >
            <img
              src={photo}
              alt=""
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </div>
        ) : (
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 8,
              background: "var(--surface-3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-tertiary)",
              flexShrink: 0,
            }}
          >
            Байк
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{booking.model}</div>
          <div className="muted" style={{ fontSize: 12 }}>
            {formatDate(booking.start_date)} → {formatDate(booking.end_date)}
          </div>
        </div>
        <span
          className={`badge ${
            booking.status === "pending"
              ? "badge-pending"
              : booking.status === "active"
              ? "badge-active"
              : "badge-completed"
          }`}
        >
          {STATUS_LABEL[booking.status]}
        </span>
      </div>
    </div>
  );
}

function DetailsModal({
  booking,
  tab,
  acting,
  onClose,
  onAccept,
  onReject,
  onComplete,
}: {
  booking: OwnerBookingItem;
  tab: Tab;
  acting: boolean;
  onClose: () => void;
  onAccept: () => void;
  onReject: (reason: string) => void;
  onComplete: () => void;
}) {
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState("");
  const photo = booking.photos?.[0];

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />

        <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          {photo ? (
            <div
              style={{
                width: 100,
                height: 100,
                borderRadius: 12,
                overflow: "hidden",
                background: "var(--surface-3)",
                flexShrink: 0,
              }}
            >
              <img
                src={photo}
                alt=""
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            </div>
          ) : (
            <div
              style={{
                width: 100,
                height: 100,
                borderRadius: 12,
                background: "var(--surface-3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-tertiary)",
                flexShrink: 0,
              }}
            >
              Байк
            </div>
          )}
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ margin: "0 0 4px", fontSize: 20 }}>{booking.model}</h2>
            <div className="muted" style={{ fontSize: 13 }}>
              Номер: {booking.plate_number}
            </div>
            <div className="muted" style={{ fontSize: 13 }}>
              {formatDate(booking.start_date)} → {formatDate(booking.end_date)}
            </div>
            <div style={{ fontWeight: 700, marginTop: 4 }}>
              {formatMoney(booking.total_price)}
            </div>
          </div>
        </div>

        <div
          className="card"
          style={{ background: "var(--surface-2)", marginBottom: 12 }}
        >
          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
            Клиент
          </div>
          <div style={{ fontSize: 15, fontWeight: 500 }}>
            {booking.client_name || "—"}
          </div>
          {booking.client_username && (
            <div className="muted" style={{ fontSize: 13 }}>
              @{booking.client_username}
            </div>
          )}
          {booking.client_phone && (
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              {booking.client_phone}
            </div>
          )}
          {booking.deposit_comment && (
            <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
              Залог: {booking.deposit_comment}
            </div>
          )}
        </div>

        {tab === "pending" && !rejectOpen && (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn btn-secondary"
              onClick={() => setRejectOpen(true)}
              disabled={acting}
              style={{ flex: 1 }}
            >
              Отклонить
            </button>
            <button
              className="btn"
              onClick={onAccept}
              disabled={acting}
              style={{ flex: 2 }}
            >
              {acting ? "…" : "Подтвердить"}
            </button>
          </div>
        )}

        {tab === "pending" && rejectOpen && (
          <>
            <label className="label">Причина отклонения</label>
            <textarea
              className="input"
              placeholder="Например: байк уже обещан"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              style={{ minHeight: 60, marginBottom: 12, resize: "vertical" }}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="btn btn-secondary"
                onClick={() => setRejectOpen(false)}
                style={{ flex: 1 }}
              >
                Назад
              </button>
              <button
                className="btn btn-danger"
                onClick={() => onReject(reason.trim())}
                disabled={acting}
                style={{ flex: 2 }}
              >
                Отклонить
              </button>
            </div>
          </>
        )}

        {tab === "active" && (
          <button
            className="btn"
            onClick={onComplete}
            disabled={acting}
            style={{ width: "100%" }}
          >
            {acting ? "…" : "Завершить аренду"}
          </button>
        )}

        <button
          className="btn btn-secondary"
          onClick={onClose}
          style={{ width: "100%", marginTop: 8 }}
        >
          Закрыть
        </button>
      </div>
    </div>
  );
}

function formatDate(d: string): string {
  const dt = new Date(d + "T00:00:00");
  return dt.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
  });
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 VND";
  return n.toLocaleString("ru-RU") + " VND";
}
