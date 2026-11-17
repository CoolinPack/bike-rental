import { useState } from "react";
import { BikeItem } from "../../types";
import { BikeBookingModal } from "./BikeBookingModal";
import { GalleryModal } from "../../components/GalleryModal";
import { MediaViewer } from "../../components/MediaViewer";
import { useDragScroll, useLockBodyScroll } from "../../components/useDragScroll";

interface Props {
  bike: BikeItem;
  onClose: () => void;
  onCreated: () => void;
}

export function BikeDetailsModal({ bike, onClose, onCreated }: Props) {
  useLockBodyScroll();
  const [bookingOpen, setBookingOpen] = useState(false);
  const [galleryStart, setGalleryStart] = useState<number | null>(null);
  const licenseRequired = (bike.engine_cc ?? 0) > 50;
  const notAvailable = bike.status === "maintenance";

  if (bookingOpen) {
    return (
      <BikeBookingModal
        bike={bike}
        onClose={() => setBookingOpen(false)}
        onCreated={onCreated}
      />
    );
  }

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
          </div>

          {bike.description && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>
                Описание
              </div>
              <div>{bike.description}</div>
            </div>
          )}

          {notAvailable && (
            <div
              className="card"
              style={{ background: "rgba(255,159,10,0.1)", marginBottom: 16 }}
            >
              <div style={{ color: "var(--warning)", fontWeight: 600 }}>
                Байк на техобслуживании
              </div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                Бронирование временно недоступно.
              </div>
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
            <button
              className="btn"
              onClick={() => setBookingOpen(true)}
              disabled={notAvailable}
              style={{ flex: 2 }}
            >
              Забронировать
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
