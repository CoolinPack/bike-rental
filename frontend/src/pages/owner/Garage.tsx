import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { BikeItem } from "../../types";
import { OwnerBikeForm } from "./BikeForm";
import { OwnerBikeViewModal } from "./GarageView";

type Status = "available" | "rented" | "maintenance";

const STATUS_LABEL: Record<Status, string> = {
  available: "Свободен",
  rented: "В аренде",
  maintenance: "На ТО",
};

const STATUS_CLASS: Record<Status, string> = {
  available: "badge-available",
  rented: "badge-rented",
  maintenance: "badge-maintenance",
};

interface OwnerProfile {
  park_id: number;
  name: string;
  subscription_plan: string;
  bikes_limit: number;
  bikes_count: number;
  is_expired: boolean;
  days_left: number;
}

export function OwnerGaragePage() {
  const [bikes, setBikes] = useState<BikeItem[]>([]);
  const [profile, setProfile] = useState<OwnerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewing, setViewing] = useState<BikeItem | null>(null);
  const [editing, setEditing] = useState<BikeItem | null>(null);
  const [creating, setCreating] = useState(false);

  function reload() {
    setLoading(true);
    Promise.all([
      api.get<{ items: BikeItem[] }>("/owner/bikes"),
      api.get<OwnerProfile>("/owner/me").catch(() => null),
    ])
      .then(([b, p]) => {
        setBikes(b.items);
        setProfile(p);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
  }, []);

  const atLimit = profile ? bikes.length >= profile.bikes_limit : false;

  return (
    <div className="page">
      <div
        className="row"
        style={{ justifyContent: "space-between", marginBottom: 8 }}
      >
        <h1 className="page-title" style={{ margin: 0 }}>
          Гараж
        </h1>

      </div>

      

      

      {loading && <div className="empty">Загрузка</div>}
      {error && (
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      )}

      {!loading && !error && bikes.length === 0 && (
        <div className="empty">
          Пока нет байков. Добавьте первый — это займёт минуту.
        </div>
      )}

      <div className="bike-grid">
        {bikes.map((bike) => (
          <OwnerBikeCard
            key={bike.id}
            bike={bike}
            onClick={(e) => { e.stopPropagation(); setTimeout(() => setViewing(bike), 0); }}
          />
        ))}
      </div>

      {creating && (
        <OwnerBikeForm
          mode="create"
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            reload();
          }}
        />
      )}

      {viewing && (
        <OwnerBikeViewModal
          bike={viewing}
          onClose={() => setViewing(null)}
          onEdit={() => {
            const b = viewing;
            setViewing(null);
            setEditing(b);
          }}
        />
      )}

      {editing && (
        <OwnerBikeForm
          mode="edit"
          bike={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}

      <button
        className="fab"
        onClick={() => setCreating(true)}
        disabled={atLimit}
        title={atLimit ? "Достигнут лимит тарифа" : "Добавить байк"}
        style={atLimit ? { opacity: 0.4, pointerEvents: "none" } : {}}
        aria-label="Добавить байк"
      >
        <svg viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </div>
  );
}

function OwnerBikeCard({
  bike,
  onClick,
}: {
  bike: BikeItem;
  onClick: (e: React.MouseEvent) => void;
}) {
  const status = bike.status as Status;
  const photo = bike.photos[0];

  return (
    <div className="bike-card" onClick={(e) => onClick(e)}>
      {photo ? (
        <img
          className="bike-card-image"
          src={photo}
          alt={bike.model}
          loading="lazy"
        />
      ) : (
        <div className="bike-card-image-empty">Байк</div>
      )}
      <div className="bike-card-body">
        <h3 className="bike-card-title">{bike.model}</h3>
        <div className="bike-card-meta">
          <span className={`badge ${STATUS_CLASS[status]}`}>
            {STATUS_LABEL[status]}
          </span>
          {bike.engine_cc !== null && <span>{bike.engine_cc} cc</span>}
        </div>
        <div className="bike-card-meta">
          <span className="bike-card-price">
            {formatMoney(bike.daily_price)} <span>/день</span>
          </span>
        </div>
      </div>
    </div>
  );
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 VND";
  return n.toLocaleString("ru-RU") + " VND";
}
