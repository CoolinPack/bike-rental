import { useState } from "react";
import { BikeItem } from "../../types";
import { api } from "../../api/client";
import { useAuth } from "../../store/auth";
import { GalleryModal } from "../../components/GalleryModal";
import { MediaViewer } from "../../components/MediaViewer";
import { useLockBodyScroll } from "../../components/useDragScroll";

interface Props {
  bike: BikeItem;
  onClose: () => void;
  onEdit: () => void;
}

export function OwnerBikeViewModal({ bike, onClose, onEdit }: Props) {
  const { me } = useAuth();
  useLockBodyScroll();
  const [galleryStart, setGalleryStart] = useState<number | null>(null);
  const licenseRequired = (bike.engine_cc ?? 0) > 50;
  const photos = bike.photos || [];
  const videos = bike.videos || [];
  const hasMedia = photos.length + videos.length > 0;

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div
        className="sheet"
        onClick={(e) => e.stopPropagation()}
        style={{ padding: "8px 0 calc(24px + env(safe-area-inset-bottom))" }}
      >
        <div className="sheet-handle" />

        {hasMedia && (
          <div style={{ marginBottom: 16 }}>
            <MediaViewer
              items={[
                ...photos.map((p) => ({ src: p, kind: "image" as const })),
                ...videos.map((v) => ({ src: v, kind: "video" as const })),
              ]}
              onOpen={setGalleryStart}
              allowSetMain={true}
              onSetMain={async (photoIdx) => {
                if (photoIdx === 0) return;
                try {
                  const newPhotos = [...photos];
                  const [moved] = newPhotos.splice(photoIdx, 1);
                  newPhotos.unshift(moved);
                  await api.post(
                    `/owner/bikes/${bike.id}/photos/reorder`,
                    { photos: newPhotos },
                    me?.park_id ? { park_id: me.park_id } : undefined
                  );
                  window.location.reload();
                } catch (e) {
                  console.error("Не удалось изменить главное фото:", e);
                  alert("Не удалось изменить главное фото");
                }
              }}
            />
          </div>
        )}

        {!hasMedia && (
          <div style={{ padding: "0 16px" }}>
            <div
              className="bike-card-image-empty"
              style={{ marginBottom: 16, borderRadius: 14 }}
            >
              Байк
            </div>
          </div>
        )}

        <div style={{ padding: "0 16px" }}>
          <h2 style={{ margin: "0 0 4px", fontSize: 24 }}>{bike.model}</h2>
          <div className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
            {bike.plate_number}
          </div>

          <div className="card col" style={{ gap: 8, marginBottom: 16 }}>
            <InfoRow
              label="Цена"
              value={`${formatMoney(bike.daily_price)} / день`}
            />
            {bike.engine_cc !== null && (
              <InfoRow label="Объём" value={`${bike.engine_cc} cc`} />
            )}
            {bike.color && <InfoRow label="Цвет" value={bike.color} />}
            {bike.mileage_km > 0 && (
              <InfoRow
                label="Пробег"
                value={`${bike.mileage_km.toLocaleString("ru-RU")} км`}
              />
            )}
            <InfoRow
              label="Права"
              value={licenseRequired ? "Нужны" : "Не нужны"}
              valueColor={licenseRequired ? "var(--danger)" : "var(--success)"}
            />
            <InfoRow
              label="Статус"
              value={
                bike.status === "available"
                  ? "Свободен"
                  : bike.status === "rented"
                  ? "В аренде"
                  : "На ТО"
              }
            />
            {bike.status === "rented" && bike.rented_until && (
              <InfoRow label="Ожидаемый возврат" value={formatDate(bike.rented_until)} />
            )}
          </div>

          {bike.description && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>
                Описание
              </div>
              <div>{bike.description}</div>
            </div>
          )}

          <div style={{ display: "flex", gap: 12 }}>
            <button
              className="btn btn-secondary"
              onClick={onClose}
              style={{ flex: 1 }}
            >
              Закрыть
            </button>
            <button className="btn" onClick={onEdit} style={{ flex: 2 }}>
              Редактировать
            </button>
          </div>
        </div>

        {galleryStart !== null && (
          <GalleryModal
            items={[
              ...photos.map((p) => ({ src: p, kind: "image" as const })),
              ...videos.map((v) => ({ src: v, kind: "video" as const })),
            ]}
            startIndex={galleryStart}
            onClose={() => setGalleryStart(null)}
          />
        )}
      </div>
    </div>
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
      <span style={{ color: valueColor, fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 VND";
  return n.toLocaleString("ru-RU") + " VND";
}
function formatDate(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("ru-RU", {
    day: "2-digit", month: "long", year: "numeric",
  });
}
