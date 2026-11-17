import { useEffect, useState } from "react";
import { api } from "../../api/client";

interface PaymentRequestItem {
  id: number;
  park_id: number;
  park_name: string;
  amount_usd: string;
  months: number;
  status: "pending" | "confirmed" | "rejected";
  requested_at: string;
  confirmed_at: string | null;
}

const STATUS_LABEL: Record<string, string> = {
  pending: "Ожидает",
  confirmed: "Подтверждена",
  rejected: "Отклонена",
};

const STATUS_CLASS: Record<string, string> = {
  pending: "badge-pending",
  confirmed: "badge-completed",
  rejected: "badge-rejected",
};

export function SuperPaymentsPage() {
  const [requests, setRequests] = useState<PaymentRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [confirming, setConfirming] = useState<PaymentRequestItem | null>(null);

  function reload() {
    setLoading(true);
    const q = filter === "pending" ? "?status=pending" : "";
    api
      .get<PaymentRequestItem[]>(`/super/payments${q}`)
      .then(setRequests)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
  }, [filter]);

  async function confirmWithAmount(
    req: PaymentRequestItem,
    amount: number | null
  ) {
    try {
      await api.post(`/super/payments/${req.id}/confirm`, {
        amount_usd: amount,
      });
      setConfirming(null);
      reload();
    } catch (e: any) {
      setError(e.message || "Не удалось подтвердить");
    }
  }

  async function reject(req: PaymentRequestItem) {
    try {
      await api.post(`/super/payments/${req.id}/reject`);
      reload();
    } catch (e: any) {
      setError(e.message || "Не удалось отклонить");
    }
  }

  return (
    <div className="page">
      <div
        className="row"
        style={{ justifyContent: "space-between", marginBottom: 12 }}
      >
        <h1 className="page-title" style={{ margin: 0 }}>
          Оплаты
        </h1>
      </div>

      <div className="filter-bar">
        <button
          className={`chip ${filter === "pending" ? "active" : ""}`}
          onClick={() => setFilter("pending")}
        >
          Ожидают
        </button>
        <button
          className={`chip ${filter === "all" ? "active" : ""}`}
          onClick={() => setFilter("all")}
        >
          Все
        </button>
      </div>

      {error && (
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      )}
      {loading && <div className="empty">Загрузка</div>}

      {!loading && !error && requests.length === 0 && (
        <div className="empty">
          {filter === "pending"
            ? "Нет ожидающих оплат"
            : "Платежей ещё не было"}
        </div>
      )}

      <div className="col" style={{ gap: 12 }}>
        {requests.map((r) => (
          <div key={r.id} className="card" style={{ padding: 12 }}>
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
                <div style={{ fontWeight: 600, fontSize: 15 }}>
                  {r.park_name}
                </div>
                <div className="muted" style={{ fontSize: 12 }}>
                  Парк ID {r.park_id}
                </div>
              </div>
              <span className={`badge ${STATUS_CLASS[r.status]}`}>
                {STATUS_LABEL[r.status]}
              </span>
            </div>

            <div
              className="row"
              style={{ gap: 12, fontSize: 13, color: "var(--text-secondary)" }}
            >
              <span>{r.months === 1 ? "1 месяц" : "3 месяца"}</span>
              <span style={{ fontWeight: 600, color: "var(--text)" }}>
                {formatMoney(r.amount_usd)}
              </span>
            </div>

            <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
              Создана {formatDateTime(r.requested_at)}
              {r.confirmed_at &&
                ` · Подтверждена ${formatDateTime(r.confirmed_at)}`}
            </div>

            {r.status === "pending" && (
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => reject(r)}
                  style={{ flex: 1, padding: "10px 14px", fontSize: 14 }}
                >
                  Отклонить
                </button>
                <button
                  className="btn"
                  onClick={() => setConfirming(r)}
                  style={{ flex: 2, padding: "10px 14px", fontSize: 14 }}
                >
                  Подтвердить
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {confirming && (
        <ConfirmPaymentModal
          request={confirming}
          onClose={() => setConfirming(null)}
          onConfirm={(amount) => confirmWithAmount(confirming, amount)}
        />
      )}
    </div>
  );
}

function ConfirmPaymentModal({
  request,
  onClose,
  onConfirm,
}: {
  request: PaymentRequestItem;
  onClose: () => void;
  onConfirm: (amount: number | null) => void;
}) {
  const [amount, setAmount] = useState<string>(request.amount_usd);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    setSubmitting(true);
    const num = amount === "" ? null : Number(amount);
    await onConfirm(num);
    setSubmitting(false);
  }

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />
        <h2 style={{ margin: "0 0 4px", fontSize: 22 }}>Подтвердить оплату</h2>
        <div className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
          {request.park_name} · {request.months === 1 ? "1 месяц" : "3 месяца"}
        </div>

        <label className="label">Сумма, $</label>
        <input
          className="input"
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          style={{ marginBottom: 16 }}
        />

        <div className="muted" style={{ fontSize: 12, marginBottom: 16 }}>
          После подтверждения подписка парка продлится на {request.months}{" "}
          {request.months === 1 ? "месяц" : "месяца"}.
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <button
            className="btn btn-secondary"
            onClick={onClose}
            style={{ flex: 1 }}
          >
            Отмена
          </button>
          <button
            className="btn"
            onClick={submit}
            disabled={submitting}
            style={{ flex: 2 }}
          >
            {submitting ? "…" : "Подтвердить"}
          </button>
        </div>
      </div>
    </div>
  );
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 $";
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 2 }) + " $";
}

function formatDateTime(d: string): string {
  const dt = new Date(d);
  return dt.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}