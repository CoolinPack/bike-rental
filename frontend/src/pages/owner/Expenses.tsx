import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { BikeItem } from "../../types";

interface ExpenseItem {
  id: number;
  park_id: number;
  bike_id: number;
  plate_number: string;
  model: string;
  category: string;
  amount: string;
  description: string | null;
  expense_date: string;
  created_at: string;
}

export function OwnerExpensesPage() {
  const [bikes, setBikes] = useState<BikeItem[]>([]);
  const [expenses, setExpenses] = useState<ExpenseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  function reload() {
    setLoading(true);
    Promise.all([
      api.get<{ items: BikeItem[] }>("/owner/bikes"),
      api.get<{ items: ExpenseItem[] }>("/owner/expenses"),
    ])
      .then(([b, e]) => {
        setBikes(b.items);
        setExpenses(e.items);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
  }, []);

  return (
    <div className="page">
      <h1 className="page-title" style={{ margin: "0 0 8px" }}>
        Расходы
      </h1>

      {bikes.length === 0 && (
        <div className="empty">
          Сначала добавьте байк в гараж, чтобы записывать расходы.
        </div>
      )}

      {loading && <div className="empty">Загрузка</div>}
      {error && (
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      )}

      {!loading && !error && bikes.length > 0 && expenses.length === 0 && (
        <div className="empty">Расходов пока нет</div>
      )}

      <div className="col" style={{ gap: 10 }}>
        {expenses.map((e) => (
          <div key={e.id} className="card" style={{ padding: 12 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 8,
                marginBottom: 4,
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 15 }}>
                  {e.category}
                </div>
                <div className="muted" style={{ fontSize: 12 }}>
                  {e.model} · {e.plate_number}
                </div>
              </div>
              <div style={{ fontWeight: 700 }}>{formatMoney(e.amount)}</div>
            </div>
            {e.description && (
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                {e.description}
              </div>
            )}
            <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
              {formatDate(e.expense_date)}
            </div>
          </div>
        ))}
      </div>

      {formOpen && (
        <ExpenseFormModal
          bikes={bikes}
          onClose={() => setFormOpen(false)}
          onSaved={() => {
            setFormOpen(false);
            reload();
          }}
        />
      )}

      <button
        className="fab"
        onClick={() => setFormOpen(true)}
        disabled={bikes.length === 0}
        title="Добавить расход"
        style={bikes.length === 0 ? { opacity: 0.4, pointerEvents: "none" } : {}}
        aria-label="Добавить расход"
      >
        <svg viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </div>
  );
}

function ExpenseFormModal({
  bikes,
  onClose,
  onSaved,
}: {
  bikes: BikeItem[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [bikeId, setBikeId] = useState(bikes[0]?.id ?? 0);
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [expenseDate, setExpenseDate] = useState(todayISO());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    if (!bikeId) return setError("Выберите байк");
    if (!category.trim()) return setError("Напишите на что расход");
    if (!amount.trim()) return setError("Введите сумму");

    setSubmitting(true);
    try {
      await api.post("/owner/expenses", {
        bike_id: bikeId,
        category: category.trim(),
        amount: Number(amount),
        description: description.trim() || null,
        expense_date: expenseDate,
      });
      onSaved();
    } catch (e: any) {
      setError(e.message || "Не удалось добавить");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />
        <h2 style={{ margin: "0 0 16px", fontSize: 22 }}>Новый расход</h2>

        <label className="label">Байк</label>
        <select
          className="input"
          value={bikeId}
          onChange={(e) => setBikeId(Number(e.target.value))}
          style={{ marginBottom: 10 }}
        >
          {bikes.map((b) => (
            <option key={b.id} value={b.id}>
              {b.model} ({b.plate_number})
            </option>
          ))}
        </select>

        <label className="label">На что расход</label>
        <input
          className="input"
          placeholder="Замена масла, аккумулятор, бензин…"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Сумма, VND</label>
        <input
          className="input"
          type="number"
          placeholder="50000"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Дата</label>
        <input
          className="input"
          type="date"
          value={expenseDate}
          onChange={(e) => setExpenseDate(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Описание (необязательно)</label>
        <textarea
          className="input"
          placeholder="Детали"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          style={{ minHeight: 60, marginBottom: 16, resize: "vertical" }}
        />

        {error && (
          <div style={{ color: "var(--danger)", marginBottom: 12 }}>
            {error}
          </div>
        )}

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
            {submitting ? "Сохранение…" : "Добавить"}
          </button>
        </div>
      </div>
    </div>
  );
}

function todayISO(): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.toISOString().slice(0, 10);
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
