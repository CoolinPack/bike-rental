import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { BookingItem } from "../../types";

type Status = "pending" | "active" | "completed" | "cancelled" | "rejected";

const STATUS_LABEL: Record<Status, string> = {
  pending: "Ожидает",
  active: "Активна",
  completed: "Завершена",
  cancelled: "Отменена",
  rejected: "Отклонена",
};

const STATUS_CLASS: Record<Status, string> = {
  pending: "badge-pending",
  active: "badge-active",
  completed: "badge-completed",
  cancelled: "badge-cancelled",
  rejected: "badge-rejected",
};

export function ClientHistoryPage() {
  const [bookings, setBookings] = useState<BookingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actingId, setActingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  function reload() {
    setLoading(true);
    api
      .get<{ items: BookingItem[] }>("/client/bookings")
      .then((r) => setBookings(r.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
  }, []);

  async function cancel(id: number) {
    if (!confirm("Отменить заявку?")) return;
    setActingId(id);
    setActionError(null);
    try {
      await api.post(`/client/bookings/${id}/cancel`);
      reload();
    } catch (e: any) {
      setActionError(e.message || "Не удалось отменить");
    } finally {
      setActingId(null);
    }
  }

  async function complete(id: number) {
    if (!confirm("Завершить аренду? Байк вернётся владельцу.")) return;
    setActingId(id);
    setActionError(null);
    try {
      await api.post(`/client/bookings/${id}/complete`);
      reload();
    } catch (e: any) {
      setActionError(e.message || "Не удалось завершить");
    } finally {
      setActingId(null);
    }
  }

  if (loading) return <div className="page"><div className="empty">Загрузка</div></div>;
  if (error)
    return (
      <div className="page">
        <h1 className="page-title">История</h1>
        <div className="empty" style={{ color: "var(--danger)" }}>{error}</div>
      </div>
    );

  return (
    <div className="page">
      <h1 className="page-title">История</h1>

      {actionError && (
        <div
          className="card"
          style={{
            background: "rgba(255,69,58,0.1)",
            borderColor: "rgba(255,69,58,0.3)",
            marginBottom: 12,
            color: "var(--danger)",
          }}
        >
          {actionError}
        </div>
      )}

      {bookings.length === 0 && (
        <div className="empty">
          Пока заявок нет. Загляните в каталог, чтобы забронировать байк.
        </div>
      )}

      <div className="col" style={{ gap: 12 }}>
        {bookings.map((b) => (
          <BookingCard
            key={b.id}
            booking={b}
            acting={actingId === b.id}
            onCancel={() => cancel(b.id)}
            onComplete={() => complete(b.id)}
          />
        ))}
      </div>
    </div>
  );
}

function BookingCard({
  booking,
  acting,
  onCancel,
  onComplete,
}: {
  booking: BookingItem;
  acting: boolean;
  onCancel: () => void;
  onComplete: () => void;
}) {
  const status = booking.status as Status;
  const canCancel = status === "pending" || status === "active";
  const canComplete = status === "active";
  const photo = booking.photos?.[0];
  const durationText = formatDuration(booking.start_date, booking.end_date);

  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ display: "flex", gap: 12 }}>
        {photo ? (
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: 10,
              overflow: "hidden",
              background: "var(--surface-3)",
              flexShrink: 0,
            }}
          >
            <img
              src={photo}
              alt={booking.model}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </div>
        ) : (
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: 10,
              background: "var(--surface-3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 24,
              color: "var(--text-tertiary)",
              flexShrink: 0,
            }}
          >
            Байк
          </div>
        )}

        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 8,
            }}
          >
            <div
              style={{
                fontWeight: 600,
                fontSize: 15,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {booking.model}
            </div>
            <span className={`badge ${STATUS_CLASS[status]}`}>
              {STATUS_LABEL[status]}
            </span>
          </div>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            Аренда на {durationText}
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
            {formatDate(booking.start_date)} — {formatDate(booking.end_date)}
          </div>
          <div style={{ fontWeight: 700, fontSize: 15, marginTop: 6 }}>
            {formatMoney(booking.total_price)}
          </div>
        </div>
      </div>

      {(canCancel || canComplete) && (
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          {canCancel && (
            <button
              className="btn btn-secondary"
              onClick={onCancel}
              disabled={acting}
              style={{ flex: 1, padding: "10px 14px", fontSize: 14 }}
            >
              {acting ? "…" : "Отменить"}
            </button>
          )}
          {canComplete && (
            <button
              className="btn"
              onClick={onComplete}
              disabled={acting}
              style={{ flex: 1, padding: "10px 14px", fontSize: 14 }}
            >
              {acting ? "…" : "Завершить"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function formatDate(d: string): string {
  const dt = new Date(d + "T00:00:00");
  return dt.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 VND";
  return n.toLocaleString("ru-RU") + " VND";
}

function formatDuration(startStr: string, endStr: string): string {
  const start = new Date(startStr + "T00:00:00Z").getTime();
  const end = new Date(endStr + "T00:00:00Z").getTime();
  const days = Math.max(1, Math.round((end - start) / 86400000) + 1);

  if (days < 30) {
    return daysWord(days);
  }

  const months = Math.floor(days / 30);
  const remDays = days - months * 30;

  if (remDays === 0) {
    return monthsWord(months);
  }

  return `${monthsWord(months)} ${daysWord(remDays)}`;
}

function daysWord(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  let word = "дней";
  if (mod10 === 1 && mod100 !== 11) word = "день";
  else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20))
    word = "дня";
  return `${n} ${word}`;
}

function monthsWord(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  let word = "месяцев";
  if (mod10 === 1 && mod100 !== 11) word = "месяц";
  else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20))
    word = "месяца";
  return `${n} ${word}`;
}
