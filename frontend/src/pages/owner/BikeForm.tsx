import { useRef, useState } from "react";
import { api } from "../../api/client";
import { BikeItem } from "../../types";
import { useAuth } from "../../store/auth";
import { GalleryModal } from "../../components/GalleryModal";

interface Props {
  mode: "create" | "edit";
  bike?: BikeItem;
  onClose: () => void;
  onSaved: () => void;
}

const MAX_PHOTOS = 5;
const MAX_VIDEOS = 1;

export function OwnerBikeForm({ mode, bike, onClose, onSaved }: Props) {
  const { me } = useAuth();
  const [plate, setPlate] = useState(bike?.plate_number ?? "");
  const [model, setModel] = useState(bike?.model ?? "");
  const [engineCc, setEngineCc] = useState(
    bike?.engine_cc !== null && bike?.engine_cc !== undefined
      ? String(bike.engine_cc)
      : ""
  );
  const [dailyPrice, setDailyPrice] = useState(bike?.daily_price ?? "");
  const [price3, setPrice3] = useState(bike?.price_3_days ?? "");
  const [price7, setPrice7] = useState(bike?.price_7_days ?? "");
  const [price14, setPrice14] = useState(bike?.price_14_days ?? "");
  const [price30, setPrice30] = useState(bike?.price_30_days ?? "");
  const [color, setColor] = useState(bike?.color ?? "");
  const [description, setDescription] = useState(bike?.description ?? "");
  const [mileage, setMileage] = useState(
    bike ? String(bike.mileage_km) : "0"
  );
  const [status, setStatus] = useState<"available" | "rented" | "maintenance">(
    (bike?.status as any) ?? "available"
  );

  // photo items: либо уже сохранённый URL (строка), либо File (в режиме create до загрузки)
  const [photos, setPhotos] = useState<(string | File)[]>(
    bike?.photos ?? []
  );
  const [videos, setVideos] = useState<(string | File)[]>(
    bike?.videos ?? []
  );
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [galleryStart, setGalleryStart] = useState<number | null>(null);

  const fileInput = useRef<HTMLInputElement>(null);
  const bikeId = bike?.id;

  async function submit() {
    setError(null);
    if (!plate.trim()) return setError("Укажите номер байка");
    if (!model.trim()) return setError("Укажите модель");
    if (!dailyPrice.trim()) return setError("Укажите цену за день");

    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("plate_number", plate.trim());
      fd.append("model", model.trim());
      if (engineCc.trim()) fd.append("engine_cc", engineCc.trim());
      fd.append("daily_price", dailyPrice.trim());
      if (price3.trim()) fd.append("price_3_days", price3.trim());
      if (price7.trim()) fd.append("price_7_days", price7.trim());
      if (price14.trim()) fd.append("price_14_days", price14.trim());
      if (price30.trim()) fd.append("price_30_days", price30.trim());
      if (color.trim()) fd.append("color", color.trim());
      if (description.trim()) fd.append("description", description.trim());
      fd.append("mileage_km", mileage.trim() || "0");
      fd.append("status", status);

      if (mode === "create") {
        photos.forEach((p) => {
          if (p instanceof File) fd.append("photos", p);
        });
        videos.forEach((v) => {
          if (v instanceof File) fd.append("videos", v);
        });
        await api.upload<{ id: number }>(
          "/owner/bikes",
          fd,
          me?.park_id ? { park_id: me.park_id } : undefined
        );
      } else {
        await api.patch(
          `/owner/bikes/${bikeId}`,
          {
            plate_number: plate.trim(),
            model: model.trim(),
            engine_cc: engineCc.trim() ? Number(engineCc) : null,
            daily_price: Number(dailyPrice),
            price_3_days: price3.trim() ? Number(price3) : null,
            price_7_days: price7.trim() ? Number(price7) : null,
            price_14_days: price14.trim() ? Number(price14) : null,
            price_30_days: price30.trim() ? Number(price30) : null,
            color: color.trim() || null,
            description: description.trim() || null,
            mileage_km: Number(mileage) || 0,
            status,
          },
          me?.park_id ? { park_id: me.park_id } : undefined
        );
      }

      onSaved();
    } catch (e: any) {
      setError(e.message || "Не удалось сохранить");
    } finally {
      setSubmitting(false);
    }
  }

  async function removeBike() {
    if (!bikeId) return;
    if (!confirm("Удалить байк? Действие нельзя отменить.")) return;
    setError(null);
    setSubmitting(true);
    try {
      await api.delete(
        `/owner/bikes/${bikeId}`,
        me?.park_id ? { park_id: me.park_id } : undefined
      );
      onSaved();
    } catch (e: any) {
      setError(e.message || "Не удалось удалить");
    } finally {
      setSubmitting(false);
    }
  }

  // ============ РАБОТА С ФОТО ============

  async function handleFiles(files: FileList) {
    if (!bikeId) {
      // Режим создания: просто добавляем файлы в локальный массив
      const fileArr = Array.from(files);
      const images = fileArr.filter((f) => f.type.startsWith("image/"));
      const vids = fileArr.filter((f) => f.type.startsWith("video/"));

      setPhotos((prev) => {
        const room = MAX_PHOTOS - prev.length;
        return [...prev, ...images.slice(0, room)];
      });
      setVideos((prev) => {
        const room = MAX_VIDEOS - prev.length;
        return [...prev, ...vids.slice(0, room)];
      });
      return;
    }

    // Режим редактирования: сразу грузим
    setUploading(true);
    setError(null);
    try {
      const fileArr = Array.from(files);
      const images = fileArr.filter((f) => f.type.startsWith("image/"));
      const vids = fileArr.filter((f) => f.type.startsWith("video/"));

      for (const img of images) {
        if (photos.length >= MAX_PHOTOS) break;
        const fd = new FormData();
        fd.append("file", img);
        const res = await api.upload<{ photos: string[] }>(
          `/owner/bikes/${bikeId}/photos`,
          fd,
          me?.park_id ? { park_id: me.park_id } : undefined
        );
        setPhotos(res.photos);
      }
      for (const v of vids) {
        if (videos.length >= MAX_VIDEOS) break;
        const fd = new FormData();
        fd.append("file", v);
        const res = await api.upload<{ videos: string[] }>(
          `/owner/bikes/${bikeId}/videos`,
          fd,
          me?.park_id ? { park_id: me.park_id } : undefined
        );
        setVideos(res.videos);
      }
    } catch (e: any) {
      setError(e.message || "Не удалось загрузить файлы");
    } finally {
      setUploading(false);
    }
  }

  async function removePhotoItem(idx: number) {
    const item = photos[idx];
    if (item instanceof File) {
      setPhotos((prev) => prev.filter((_, i) => i !== idx));
      return;
    }
    if (!bikeId) return;
    setUploading(true);
    try {
      const res = await api.delete<{ photos: string[] }>(
        `/owner/bikes/${bikeId}/photos`,
        { url: item, ...(me?.park_id ? { park_id: me.park_id } : {}) }
      );
      setPhotos(res.photos);
    } catch (e: any) {
      setError(e.message || "Не удалось удалить фото");
    } finally {
      setUploading(false);
    }
  }

  async function removeVideoItem(idx: number) {
    const item = videos[idx];
    if (item instanceof File) {
      setVideos((prev) => prev.filter((_, i) => i !== idx));
      return;
    }
    if (!bikeId) return;
    setUploading(true);
    try {
      const res = await api.delete<{ videos: string[] }>(
        `/owner/bikes/${bikeId}/videos`,
        { url: item, ...(me?.park_id ? { park_id: me.park_id } : {}) }
      );
      setVideos(res.videos);
    } catch (e: any) {
      setError(e.message || "Не удалось удалить видео");
    } finally {
      setUploading(false);
    }
  }

  // Drag and drop порядок фото
  function onDragStart(idx: number) {
    setDraggedIdx(idx);
  }

  function onDropPhoto(idx: number) {
    if (draggedIdx === null || draggedIdx === idx) {
      setDraggedIdx(null);
      return;
    }
    setPhotos((prev) => {
      const next = [...prev];
      const [moved] = next.splice(draggedIdx, 1);
      next.splice(idx, 0, moved);
      return next;
    });
    setDraggedIdx(null);
  }


  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />
        <h2 style={{ margin: "0 0 16px", fontSize: 22 }}>
          {mode === "create" ? "Новый байк" : "Редактирование"}
        </h2>

        {photos.length > 0 && (
          <div className="media-preview-hero">
            <img
              src={
                photos[0] instanceof File
                  ? URL.createObjectURL(photos[0])
                  : photos[0]
              }
              alt="Главное фото"
            />
            <div className="media-preview-hero-label">Главное фото</div>
          </div>
        )}

        <label className="label">Номер</label>
        <input
          className="input"
          placeholder="AB123CD"
          value={plate}
          onChange={(e) => setPlate(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Модель</label>
        <input
          className="input"
          placeholder="Yamaha MT-07"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Кубы (cc)</label>
        <input
          className="input"
          type="number"
          placeholder="125"
          value={engineCc}
          onChange={(e) => setEngineCc(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Цена за день, VND</label>
        <input
          className="input"
          type="number"
          placeholder="500000"
          value={dailyPrice}
          onChange={(e) => setDailyPrice(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <div className="section-title" style={{ marginTop: 8 }}>Цена за день в зависимости от срока</div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          Укажите стоимость одного дня для каждого готового периода. Если клиент выберет произвольное количество дней, применяется базовая цена.
        </div>
        {[
          ["3 дня", price3, setPrice3],
          ["7 дней", price7, setPrice7],
          ["14 дней", price14, setPrice14],
          ["30 дней", price30, setPrice30],
        ].map(([label, value, setter]: any) => (
          <div key={label} style={{ marginBottom: 8 }}>
            <label className="label">{label}, VND / день</label>
            <input className="input" type="number" min="0" placeholder="Цена за день"
              value={value} onChange={(e) => setter(e.target.value)} />
          </div>
        ))}

        <label className="label">Цвет</label>
        <input
          className="input"
          placeholder="black"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Описание</label>
        <textarea
          className="input"
          placeholder="Коротко о байке"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          style={{ minHeight: 60, marginBottom: 10, resize: "vertical" }}
        />

        <label className="label">Пробег, км</label>
        <input
          className="input"
          type="number"
          value={mileage}
          onChange={(e) => setMileage(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <label className="label">Статус</label>
        <div className="option-list" style={{ marginBottom: 16 }}>
          <OptionRadio
            name="status"
            label="Свободен"
            checked={status === "available"}
            onChange={() => setStatus("available")}
          />
          <OptionRadio
            name="status"
            label="В аренде"
            checked={status === "rented"}
            onChange={() => setStatus("rented")}
          />
          <OptionRadio
            name="status"
            label="На ТО"
            checked={status === "maintenance"}
            onChange={() => setStatus("maintenance")}
          />
        </div>

        <div className="section-title" style={{ marginTop: 8 }}>
          Медиа
        </div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          Фото {photos.length}/{MAX_PHOTOS} · Видео {videos.length}/{MAX_VIDEOS}
          . Перетащите фото, чтобы изменить порядок.
        </div>

        <div className="media-grid">
          {photos.map((src, idx) => {
            const url =
              src instanceof File ? URL.createObjectURL(src) : src;
            return (
              <div
                key={`p-${idx}`}
                className="media-grid-item"
                draggable={true}
                onDragStart={() => onDragStart(idx)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => onDropPhoto(idx)}
                onClick={() => setGalleryStart(idx)}
                style={{
                  outline:
                    draggedIdx === idx
                      ? "2px solid var(--accent)"
                      : undefined,
                }}
              >
                <img src={url} alt="" />
                {idx === 0 && (
                  <span className="media-grid-badge">Главное</span>
                )}
                <button
                  className="media-grid-remove"
                  onClick={() => removePhotoItem(idx)}
                  disabled={uploading}
                >
                  ×
                </button>
              </div>
            );
          })}
          {videos.map((src, idx) => {
            const url =
              src instanceof File ? URL.createObjectURL(src) : src;
            return (
              <div
                key={`v-${idx}`}
                className="media-grid-item media-grid-video"
                onClick={() => setGalleryStart(photos.length + idx)}
              >
                <video src={url} />
                <span className="media-grid-badge">Видео</span>
                <button
                  className="media-grid-remove"
                  onClick={() => removeVideoItem(idx)}
                  disabled={uploading}
                >
                  ×
                </button>
              </div>
            );
          })}
          {photos.length < MAX_PHOTOS && videos.length < MAX_VIDEOS ? (
            <button
              className="media-grid-add"
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              type="button"
            >
              <span style={{ fontSize: 24 }}>+</span>
              <span style={{ fontSize: 11 }}>Медиа</span>
            </button>
          ) : photos.length < MAX_PHOTOS ? (
            <button
              className="media-grid-add"
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              type="button"
            >
              <span style={{ fontSize: 24 }}>+</span>
              <span style={{ fontSize: 11 }}>Фото</span>
            </button>
          ) : videos.length < MAX_VIDEOS ? (
            <button
              className="media-grid-add"
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              type="button"
            >
              <span style={{ fontSize: 24 }}>+</span>
              <span style={{ fontSize: 11 }}>Видео</span>
            </button>
          ) : null}
        </div>
        <input
          ref={fileInput}
          type="file"
          accept="image/*,video/*"
          multiple
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
            e.target.value = "";
          }}
        />

        {uploading && (
          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            Загрузка…
          </div>
        )}

        {error && (
          <div style={{ color: "var(--danger)", margin: "12px 0" }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
          {mode === "edit" && (
            <button
              className="btn btn-danger"
              onClick={removeBike}
              disabled={submitting || uploading}
              style={{ flex: "1 1 100%", padding: "10px 14px" }}
            >
              Удалить байк
            </button>
          )}
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
            disabled={submitting || uploading}
            style={{ flex: 2 }}
          >
            {submitting
              ? "Сохранение…"
              : mode === "create"
              ? "Создать"
              : "Сохранить"}
          </button>
        </div>

        {submitting && (
          <div style={{ position: "fixed", inset: 0, zIndex: 10000, background: "rgba(0,0,0,.68)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", flexDirection: "column", gap: 12 }}>
            <div className="bike-save-spinner" />
            <strong>{mode === "create" ? "Создаём карточку байка…" : "Сохраняем изменения…"}</strong>
            <span style={{ fontSize: 12, opacity: .8 }}>Пожалуйста, не закрывайте приложение</span>
          </div>
        )}

        {galleryStart !== null && (
          <GalleryModal
            items={[
              ...photos.map((p) => ({
                src: p instanceof File ? URL.createObjectURL(p) : p,
                kind: "image" as const,
              })),
              ...videos.map((v) => ({
                src: v instanceof File ? URL.createObjectURL(v) : v,
                kind: "video" as const,
              })),
            ]}
            startIndex={galleryStart}
            onClose={() => setGalleryStart(null)}
          />
        )}
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
