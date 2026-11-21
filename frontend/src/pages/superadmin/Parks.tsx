import { useEffect, useState } from "react";
import { api } from "../../api/client";

interface ParkItem {
  id: number;
  name: string;
  owner_telegram_id: number;
  subscription_plan: "start" | "pro";
  subscription_expires_at: string | null;
  custom_price_usd: string | null;
  discount_percent: string;
  referred_by_park_id: number | null;
  is_active: boolean;
  created_at: string;
  bikes_count: number;
  bookings_count: number;
  revenue_usd: string;
  bot_token_configured: boolean;
}

const PLAN_LABEL: Record<string, string> = {
  start: "Старт",
  pro: "Про",
};

export function SuperParksPage() {
  const [parks, setParks] = useState<ParkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ParkItem | null>(null);
  const [creating, setCreating] = useState(false);

  function reload() {
    setLoading(true);
    api
      .get<{ items: ParkItem[]; total: number }>("/super/parks")
      .then((r) => setParks(r.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
  }, []);

  return (
    <div className="page">
      <h1 className="page-title" style={{ margin: "0 0 8px" }}>
        Парки
      </h1>

      {loading && <div className="empty">Загрузка</div>}
      {error && (
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      )}

      {!loading && !error && parks.length === 0 && (
        <div className="empty">Парков пока нет</div>
      )}

      <div className="col" style={{ gap: 12 }}>
        {parks.map((p) => (
          <ParkCard key={p.id} park={p} onClick={() => setEditing(p)} />
        ))}
      </div>

      {editing && (
        <ParkFormModal
          park={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}

      {creating && (
        <ParkCreateModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            reload();
          }}
        />
      )}

      <button
        className="fab"
        onClick={() => setCreating(true)}
        aria-label="Добавить парк"
      >
        <svg viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </div>
  );
}

function ParkCard({ park, onClick }: { park: ParkItem; onClick: () => void }) {
  const isExpired =
    park.subscription_expires_at === null ||
    new Date(park.subscription_expires_at) < new Date();

  return (
    <div className="card" style={{ padding: 12 }} onClick={onClick}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 8,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 16 }}>{park.name}</div>
          <div className="muted" style={{ fontSize: 13 }}>
            ID {park.id} · Владелец {park.owner_telegram_id}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 4,
            alignItems: "flex-end",
          }}
        >
          <span
            className="badge"
            style={{
              background:
                park.subscription_plan === "pro"
                  ? "rgba(10,132,255,0.18)"
                  : "rgba(255,255,255,0.08)",
              color:
                park.subscription_plan === "pro"
                  ? "var(--accent)"
                  : "var(--text-secondary)",
            }}
          >
            {PLAN_LABEL[park.subscription_plan] ?? park.subscription_plan}
          </span>
          {!park.is_active && (
            <span className="badge badge-cancelled">Выключен</span>
          )}
          {isExpired && park.is_active && (
            <span className="badge badge-maintenance">Истёк</span>
          )}
        </div>
      </div>

      <div
        className="row"
        style={{
          marginTop: 10,
          gap: 16,
          fontSize: 13,
          color: "var(--text-secondary)",
        }}
      >
        <span>Байков: {park.bikes_count}</span>
        <span>Броней: {park.bookings_count}</span>
      </div>

      <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
        Telegram-бот: {park.bot_token_configured ? "токен сохранён" : "не подключён"}
      </div>

      {park.subscription_expires_at && (
        <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
          Подписка до {formatDate(park.subscription_expires_at)}
        </div>
      )}
    </div>
  );
}

interface ParkCreateForm {
  name: string;
  owner_telegram_id: string;
  bot_token: string;
  subscription_plan: "start" | "pro";
  subscription_months: number;
  custom_price_usd: string;
  discount_percent: string;
}

function ParkCreateModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<ParkCreateForm>({
    name: "",
    owner_telegram_id: "",
    bot_token: "",
    subscription_plan: "start",
    subscription_months: 1,
    custom_price_usd: "",
    discount_percent: "0",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    setError(null);
    if (!form.name.trim()) return setError("Введите название парка");
    if (!form.owner_telegram_id.trim() || !/^\d+$/.test(form.owner_telegram_id.trim()))
      return setError("Введите корректный Telegram ID владельца");
    if (!form.bot_token.trim())
      return setError("Введите токен Telegram-бота парка");
    setSubmitting(true);
    try {
      const result = await api.post<{ id: number; bot_configured: boolean; warning?: string | null }>("/super/parks", {
        name: form.name.trim(),
        owner_telegram_id: Number(form.owner_telegram_id),
        bot_token: form.bot_token.trim() || null,
        subscription_plan: form.subscription_plan,
        subscription_months: form.subscription_months,
        custom_price_usd: form.custom_price_usd
          ? Number(form.custom_price_usd)
          : null,
        discount_percent: form.discount_percent
          ? Number(form.discount_percent)
          : 0,
      });
      if (result.warning) {
        window.alert(`Парк создан, но Telegram-бот пока не подключён: ${result.warning}. Токен сохранён; повторите подключение через редактирование парка.`);
      }
      onCreated();
    } catch (e: any) {
      setError(e.message || "Не удалось создать");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />
        <h2 style={{ margin: "0 0 16px", fontSize: 22 }}>Новый парк</h2>

        <label className="label">Название</label>
        <input
          className="input"
          placeholder="Bike Rental Saigon"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Telegram ID владельца</label>
        <input
          className="input"
          placeholder="123456789"
          type="number"
          value={form.owner_telegram_id}
          onChange={(e) =>
            setForm({ ...form, owner_telegram_id: e.target.value })
          }
          style={{ marginBottom: 10 }}
        />

        <label className="label">Токен Telegram-бота</label>
        <input
          className="input"
          placeholder="123456:ABC..."
          type="password"
          autoComplete="new-password"
          value={form.bot_token}
          onChange={(e) => setForm({ ...form, bot_token: e.target.value })}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Подписка</label>
        <div className="option-list" style={{ marginBottom: 12 }}>
          <OptionRadio
            name="plan"
            label="Старт — 17$ / до 10 байков"
            checked={form.subscription_plan === "start"}
            onChange={() => setForm({ ...form, subscription_plan: "start" })}
          />
          <OptionRadio
            name="plan"
            label="Про — 49$ / до 20 байков"
            checked={form.subscription_plan === "pro"}
            onChange={() => setForm({ ...form, subscription_plan: "pro" })}
          />
        </div>

        <label className="label">Срок</label>
        <div className="option-list" style={{ marginBottom: 12 }}>
          <OptionRadio
            name="months"
            label="1 месяц"
            checked={form.subscription_months === 1}
            onChange={() => setForm({ ...form, subscription_months: 1 })}
          />
          <OptionRadio
            name="months"
            label="3 месяца"
            checked={form.subscription_months === 3}
            onChange={() => setForm({ ...form, subscription_months: 3 })}
          />
        </div>

        <label className="label">Индивидуальная цена, $ (необязательно)</label>
        <input
          className="input"
          placeholder="Пусто = стандартная"
          type="number"
          value={form.custom_price_usd}
          onChange={(e) =>
            setForm({ ...form, custom_price_usd: e.target.value })
          }
          style={{ marginBottom: 10 }}
        />

        <label className="label">Скидка, % (необязательно)</label>
        <input
          className="input"
          placeholder="0"
          type="number"
          value={form.discount_percent}
          onChange={(e) =>
            setForm({ ...form, discount_percent: e.target.value })
          }
          style={{ marginBottom: 16 }}
        />

        {error && (
          <div style={{ color: "var(--danger)", marginBottom: 12 }}>{error}</div>
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
            {submitting ? "Создание…" : "Создать"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ParkFormModal({
  park,
  onClose,
  onSaved,
}: {
  park: ParkItem;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(park.name);
  const [ownerTelegramId, setOwnerTelegramId] = useState(String(park.owner_telegram_id));
  const [botToken, setBotToken] = useState("");
  const [customPrice, setCustomPrice] = useState(park.custom_price_usd ?? "");
  const [discount, setDiscount] = useState(park.discount_percent ?? "0");
  const [isActive, setIsActive] = useState(park.is_active);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function save() {
    setError(null);
    setSuccessMsg(null);
    setSubmitting(true);
    try {
      if (!name.trim()) throw new Error("Введите название парка");
      if (!ownerTelegramId.trim() || !/^\d+$/.test(ownerTelegramId.trim())) {
        throw new Error("Введите корректный Telegram ID владельца");
      }
      const payload: Record<string, unknown> = {
        name: name.trim(),
        owner_telegram_id: Number(ownerTelegramId),
        custom_price_usd: customPrice === "" ? null : Number(customPrice),
        discount_percent: Number(discount),
        is_active: isActive,
      };
      if (botToken.trim()) payload.bot_token = botToken.trim();
      const result = await api.patch<{ bot_configured?: boolean; warning?: string | null }>(
        `/super/parks/${park.id}`,
        payload,
      );
      if (result.warning) {
        setError(`Данные сохранены, но бот пока не подключён: ${result.warning}`);
        return;
      }
      setSuccessMsg(botToken.trim() ? "Данные сохранены, Telegram-бот подключён" : "Сохранено");
      onSaved();
    } catch (e: any) {
      setError(e.message || "Не удалось сохранить");
    } finally {
      setSubmitting(false);
    }
  }

  async function changePlan(newPlan: "start" | "pro") {
    if (!confirm(`Сменить тариф на ${newPlan === "pro" ? "Про" : "Старт"}?`)) {
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setSubmitting(true);
    try {
      await api.post(`/super/parks/${park.id}/change-plan`, {
        new_plan: newPlan,
      });
      setSuccessMsg(
        `Тариф изменён на ${newPlan === "pro" ? "Про" : "Старт"}`,
      );
      onSaved();
    } catch (e: any) {
      setError(e.message || "Не удалось сменить тариф");
    } finally {
      setSubmitting(false);
    }
  }

  async function extend(months: 1 | 3) {
    if (!confirm(`Продлить на ${months === 1 ? "1 месяц" : "3 месяца"}?`))
      return;
    setError(null);
    setSuccessMsg(null);
    setSubmitting(true);
    try {
      await api.post(`/super/parks/${park.id}/extend`, { months });
      setSuccessMsg(`Продлено на ${months === 1 ? "месяц" : "3 месяца"}`);
      onSaved();
    } catch (e: any) {
      setError(e.message || "Не удалось продлить");
    } finally {
      setSubmitting(false);
    }
  }

  async function remove() {
    if (
      !confirm(
        `Полностью удалить парк "${park.name}"? Будут удалены его Telegram-привязка, байки, брони, расходы, точки карты и заявки на оплату. Это действие необратимо.`,
      )
    )
      return;
    setSubmitting(true);
    try {
      await api.delete(`/super/parks/${park.id}`);
      onSaved();
    } catch (e: any) {
      setError(e.message || "Не удалось удалить");
    } finally {
      setSubmitting(false);
    }
  }

  const isExpired =
    park.subscription_expires_at === null ||
    new Date(park.subscription_expires_at) < new Date();

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />
        <h2 style={{ margin: "0 0 4px", fontSize: 22 }}>{park.name}</h2>
        <div className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
          ID {park.id} · Владелец {park.owner_telegram_id}
        </div>

        <div className="card col" style={{ marginBottom: 16 }}>
          <InfoRow label="Байков" value={String(park.bikes_count)} />
          <InfoRow
            label="Завершённых броней"
            value={String(park.bookings_count)}
          />
          <InfoRow label="Выручка парка" value={formatMoney(park.revenue_usd)} />
          <InfoRow
            label="Текущий тариф"
            value={park.subscription_plan === "pro" ? "Про" : "Старт"}
          />
          {park.subscription_expires_at && (
            <InfoRow
              label="Подписка до"
              value={formatDate(park.subscription_expires_at)}
              valueColor={isExpired ? "var(--danger)" : undefined}
            />
          )}
        </div>

        <div className="section-title" style={{ marginTop: 8 }}>
          Управление подпиской
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button
            className="btn btn-secondary"
            onClick={() => changePlan("start")}
            disabled={submitting || park.subscription_plan === "start"}
            style={{ flex: 1, padding: "10px 12px", fontSize: 13 }}
          >
            На «Старт»
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => changePlan("pro")}
            disabled={submitting || park.subscription_plan === "pro"}
            style={{ flex: 1, padding: "10px 12px", fontSize: 13 }}
          >
            На «Про»
          </button>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button
            className="btn"
            onClick={() => extend(1)}
            disabled={submitting}
            style={{ flex: 1, padding: "10px 12px", fontSize: 13 }}
          >
            +1 месяц
          </button>
          <button
            className="btn"
            onClick={() => extend(3)}
            disabled={submitting}
            style={{ flex: 1, padding: "10px 12px", fontSize: 13 }}
          >
            +3 месяца
          </button>
        </div>

        <label
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 14px",
            background: "var(--surface)",
            borderRadius: 10,
            marginBottom: 16,
          }}
        >
          <div>
            <div style={{ fontWeight: 500 }}>Парк активен</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {isActive
                ? "Функционал доступен владельцу"
                : "Владелец видит только предупреждение об оплате"}
            </div>
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            <span className="switch-slider" />
          </label>
        </label>

        <label className="label">Название</label>
        <input
          className="input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Telegram ID владельца</label>
        <input
          className="input"
          type="number"
          value={ownerTelegramId}
          onChange={(e) => setOwnerTelegramId(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Новый токен Telegram-бота</label>
        <input
          className="input"
          type="password"
          autoComplete="new-password"
          placeholder={park.bot_token_configured ? "Оставьте пустым, чтобы не менять" : "Вставьте токен бота"}
          value={botToken}
          onChange={(e) => setBotToken(e.target.value)}
          style={{ marginBottom: 6 }}
        />
        <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
          Сейчас: {park.bot_token_configured ? "токен сохранён; для замены вставьте новый" : "токен не подключён"}. Сам токен никогда не показывается.
        </div>

        <label className="label">Индивидуальная цена, $</label>
        <input
          className="input"
          type="number"
          placeholder="Пусто = стандартная"
          value={customPrice}
          onChange={(e) => setCustomPrice(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Скидка, %</label>
        <input
          className="input"
          type="number"
          value={discount}
          onChange={(e) => setDiscount(e.target.value)}
          style={{ marginBottom: 16 }}
        />

        {error && (
          <div style={{ color: "var(--danger)", marginBottom: 12 }}>{error}</div>
        )}
        {successMsg && (
          <div style={{ color: "var(--success)", marginBottom: 12 }}>
            {successMsg}
          </div>
        )}

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            className="btn btn-danger"
            onClick={remove}
            disabled={submitting}
            style={{ flex: 1 }}
          >
            Удалить
          </button>
          <button
            className="btn btn-secondary"
            onClick={onClose}
            style={{ flex: 1 }}
          >
            Отмена
          </button>
          <button
            className="btn"
            onClick={save}
            disabled={submitting}
            style={{ flex: 2 }}
          >
            {submitting ? "Сохранение…" : "Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}

function OptionRadio({
  name,
  label,
  checked,
  onChange,
}: {
  name: string;
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label
      className={`option-radio ${checked ? "checked" : ""}`}
      htmlFor={`${name}-${label}`}
    >
      <input
        id={`${name}-${label}`}
        type="radio"
        name={name}
        checked={checked}
        onChange={onChange}
        style={{ display: "none" }}
      />
      <span className="option-radio-dot" aria-hidden="true">
        {checked && <span className="option-radio-dot-inner" />}
      </span>
      <span className="option-radio-label">{label}</span>
    </label>
  );
}

function InfoRow({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      <span className="muted">{label}</span>
      <span style={{ fontWeight: 500, color: valueColor }}>{value}</span>
    </div>
  );
}

function formatDate(d: string): string {
  const dt = new Date(d);
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
