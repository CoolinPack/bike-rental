import { useMemo, useState } from "react";
import { api } from "../../api/client";
import { BikeItem } from "../../types";

interface Props {
  bike: BikeItem;
  onClose: () => void;
  onCreated: () => void;
}

function todayISO(): string {
  // Формируем дату по локальному календарю устройства.
  // toISOString() переводит время в UTC и в UTC+7 может вернуть предыдущий день.
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDaysISO(value: string, count: number): string {
  const d = new Date(value + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + count);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

function diffDays(a: string, b: string): number {
  const da = new Date(a + "T00:00:00Z").getTime();
  const db = new Date(b + "T00:00:00Z").getTime();
  return Math.max(0, Math.round((db - da) / 86400000) + 1);
}

type DepositType = "cash" | "cash_passport";

export function BikeBookingModal({ bike, onClose, onCreated }: Props) {
  const [start, setStart] = useState(todayISO());
  const [end, setEnd] = useState(todayISO());
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [username, setUsername] = useState("");
  const [depositType, setDepositType] = useState<DepositType>("cash");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const days = useMemo(() => diffDays(start, end), [start, end]);
  const appliedDailyPrice = useMemo(() => {
    const tiers: Record<number, string | null | undefined> = {
      3: bike.price_3_days,
      7: bike.price_7_days,
      14: bike.price_14_days,
      30: bike.price_30_days,
    };
    const tier = tiers[days];
    return tier !== undefined && tier !== null && tier !== ""
      ? Number(tier)
      : Number(bike.daily_price);
  }, [bike, days]);
  const total = useMemo(
    () => (appliedDailyPrice * days).toFixed(0),
    [appliedDailyPrice, days]
  );
  const invalidDates = end < start;

  async function submit() {
    setError(null);
    if (invalidDates) {
      setError("Дата окончания раньше начала");
      return;
    }
    if (!name.trim()) {
      setError("Укажите имя");
      return;
    }
    if (!phone.trim()) {
      setError("Укажите телефон");
      return;
    }

    const depositLabel =
      depositType === "cash" ? "Наличные" : "Наличные + паспорт";
    const deposit_comment = comment.trim()
      ? `${depositLabel}. ${comment.trim()}`
      : depositLabel;

    setSubmitting(true);
    try {
      await api.post("/client/bookings", {
        bike_id: bike.id,
        start_date: start,
        end_date: end,
        client_name: name.trim(),
        client_phone: phone.trim(),
        deposit_comment,
      }, { park_id: bike.park_id });
      onCreated();
    } catch (e: any) {
      setError(e.message || "Ошибка при создании заявки");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />

        <h2 style={{ margin: "0 0 4px", fontSize: 22 }}>Бронирование</h2>
        <div className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
          {bike.model} · {bike.plate_number}
        </div>

        <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <label className="label">С</label>
            <input
              className="input"
              type="date"
              min={todayISO()}
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label className="label">По</label>
            <input
              className="input"
              type="date"
              min={start}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
          {[
            { days: 1, label: "1 день", price: bike.daily_price },
            { days: 3, label: "3 дня", price: bike.price_3_days },
            { days: 7, label: "7 дней", price: bike.price_7_days },
            { days: 14, label: "14 дней", price: bike.price_14_days },
            { days: 30, label: "1 месяц", price: bike.price_30_days },
          ].map((item) => (
            <button key={item.days} type="button" className={`chip ${days === item.days ? "active" : ""}`}
              onClick={() => setEnd(addDaysISO(start, item.days - 1))}>
              <span>{item.label}</span>
              <span style={{ display: "inline-flex", gap: 5, alignItems: "baseline", marginLeft: 4 }}>
                {Number(item.price ?? bike.daily_price) < Number(bike.daily_price) && (
                  <span style={{ textDecoration: "line-through", opacity: .6, fontSize: 11 }}>
                    {Number(bike.daily_price).toLocaleString("ru-RU")}
                  </span>
                )}
                <strong>{Number(item.price ?? bike.daily_price).toLocaleString("ru-RU")}</strong>
                <span style={{ fontSize: 10 }}>/ день</span>
              </span>
            </button>
          ))}
        </div>

        <div
          className="card"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <span className="muted">
            {days} {days === 1 ? "день" : days < 5 ? "дня" : "дней"} ×{" "}
            {appliedDailyPrice.toLocaleString("ru-RU")} VND / день
          </span>
          <span style={{ fontSize: 20, fontWeight: 700 }}>{formatMoney(total)}</span>
        </div>

        <label className="label">Имя</label>
        <input
          className="input"
          placeholder="Как к вам обращаться"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Телефон</label>
        <input
          className="input"
          type="tel"
          placeholder="+7 999 123-45-67"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Telegram username</label>
        <input
          className="input"
          placeholder="@username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ marginBottom: 16 }}
        />

        <label className="label">Залог</label>
        <div className="col" style={{ marginBottom: 16 }}>
          <label style={depositOptionStyle(depositType === "cash")}>
            <input
              type="radio"
              name="deposit"
              checked={depositType === "cash"}
              onChange={() => setDepositType("cash")}
              style={{ marginRight: 10 }}
            />
            <span>Наличные</span>
          </label>
          <label style={depositOptionStyle(depositType === "cash_passport")}>
            <input
              type="radio"
              name="deposit"
              checked={depositType === "cash_passport"}
              onChange={() => setDepositType("cash_passport")}
              style={{ marginRight: 10 }}
            />
            <span>Наличные + паспорт</span>
          </label>
        </div>

        <label className="label">Комментарий (необязательно)</label>
        <textarea
          className="input"
          placeholder="Уточнения, сумма залога и т.д."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          style={{ minHeight: 60, marginBottom: 16, resize: "vertical" }}
        />

        {error && (
          <div style={{ color: "var(--danger)", marginBottom: 12 }}>{error}</div>
        )}

        <div style={{ display: "flex", gap: 12 }}>
          <button className="btn btn-secondary" onClick={onClose} style={{ flex: 1 }}>
            Отмена
          </button>
          <button
            className="btn"
            onClick={submit}
            disabled={submitting || invalidDates}
            style={{ flex: 2 }}
          >
            {submitting ? "Отправка…" : "Отправить заявку"}
          </button>
        </div>
      </div>
    </div>
  );
}

function depositOptionStyle(active: boolean): React.CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    padding: "12px 14px",
    borderRadius: 10,
    background: active ? "rgba(10,132,255,0.15)" : "var(--surface)",
    border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
    cursor: "pointer",
    margin: 0,
  };
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 VND";
  return n.toLocaleString("ru-RU") + " VND";
}
