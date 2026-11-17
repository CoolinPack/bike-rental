import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useAuth } from "../../store/auth";

interface OwnerProfile {
  park_id: number;
  name: string;
  owner_telegram_id: number;
  subscription_plan: string;
  subscription_expires_at: string | null;
  days_left: number;
  is_expired: boolean;
  bikes_limit: number;
  bikes_count: number;
  is_active: boolean;
}

const SUPPORT_URL = "https://t.me/your_support_username";

export function OwnerProfilePage() {
  const { me } = useAuth();
  const [profile, setProfile] = useState<OwnerProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<OwnerProfile>("/owner/me")
      .then(setProfile)
      .catch((e) => setError(e.message));
  }, []);

  if (error)
    return (
      <div className="page">
        <h1 className="page-title">Профиль</h1>
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      </div>
    );

  if (!profile)
    return (
      <div className="page">
        <div className="empty">Загрузка</div>
      </div>
    );

  const isPro = profile.subscription_plan === "pro";

  return (
    <div className="page">
      <h1 className="page-title">Профиль</h1>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              background: "var(--accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 22,
              fontWeight: 700,
              color: "#fff",
              flexShrink: 0,
            }}
          >
            {(me?.user.first_name || me?.user.username || "?")
              .charAt(0)
              .toUpperCase()}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 16 }}>
              {me?.user.first_name || me?.user.username || "—"}
            </div>
            {me?.user.username && (
              <div className="muted" style={{ fontSize: 13 }}>
                @{me.user.username}
              </div>
            )}
            <div className="muted" style={{ fontSize: 13 }}>
              {profile.name}
            </div>
          </div>
        </div>
      </div>

      <div className="section-title">Подписка</div>

      <div
        className="card"
        style={{
          marginBottom: 12,
          borderColor: profile.is_expired
            ? "rgba(255,69,58,0.3)"
            : "var(--border)",
          background: profile.is_expired
            ? "rgba(255,69,58,0.06)"
            : "var(--surface)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 8,
          }}
        >
          <div>
            <div style={{ fontWeight: 600, fontSize: 16 }}>
              {isPro ? "Про" : "Старт"} — {isPro ? "49$" : "17$"} / мес
            </div>
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              {profile.bikes_count} из {profile.bikes_limit} байков
            </div>
          </div>
          <span
            className={`badge ${
              profile.is_expired
                ? "badge-maintenance"
                : profile.days_left <= 7
                ? "badge-pending"
                : "badge-active"
            }`}
          >
            {profile.is_expired
              ? "Истекла"
              : `Осталось ${profile.days_left} дн.`}
          </span>
        </div>

        {profile.subscription_expires_at && (
          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            До {formatDate(profile.subscription_expires_at)}
          </div>
        )}

        {!isPro && (
          <button
            className="btn"
            style={{ width: "100%", marginTop: 12 }}
            onClick={() => {
              window.open(SUPPORT_URL, "_blank");
            }}
          >
            Повысить до Про — 49$
          </button>
        )}
      </div>

      <div className="section-title">Тарифы</div>

      <div className="col" style={{ gap: 12, marginBottom: 16 }}>
        <div
          className="card"
          style={{
            borderColor: !isPro ? "var(--accent)" : "var(--border)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 16 }}>Старт</div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>17$ / мес</div>
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              color: "var(--text-secondary)",
              fontSize: 14,
              lineHeight: 1.7,
            }}
          >
            <li>До 10 байков</li>
            <li>Каталог и брони</li>
            <li>Базовые расходы</li>
            <li>История заявок</li>
          </ul>
        </div>

        <div
          className="card"
          style={{
            borderColor: isPro ? "var(--accent)" : "var(--border)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 16 }}>Про</div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>49$ / мес</div>
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              color: "var(--text-secondary)",
              fontSize: 14,
              lineHeight: 1.7,
            }}
          >
            <li>До 20 байков</li>
            <li>Расширенная аналитика</li>
            <li>Умные уведомления (масло, ремонт)</li>
            <li>Приоритетная поддержка</li>
          </ul>
        </div>
      </div>

      <div className="section-title">Поддержка</div>

      <button
        className="btn btn-secondary"
        onClick={() => window.open(SUPPORT_URL, "_blank")}
        style={{ width: "100%" }}
      >
        Связаться с поддержкой
      </button>
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
