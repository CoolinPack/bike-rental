import { useEffect, useMemo, useRef, useState } from "react";
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

  // Create object URLs once per selected File and release them when previews change.
  const previewMedia = useMemo(() => {
    const created: string[] = [];
    const resolve = (item: string | File) => {
      if (item instanceof File) {
        const url = URL.createObjectURL(item);
        created.push(url);
        return url;
      }
      return item;
    };
    return {
      photos: photos.map(resolve),
      videos: videos.map(resolve),
      created,
    };
  }, [photos, videos]);

  useEffect(() => {
    return () => previewMedia.created.forEach((url) => URL.revokeObjectURL(url));
  }, [previewMedia]);

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
    const selected = Array.from(files);
    const allowedImage = new Set(["image/jpeg", "image/png", "image/webp"]);
    const allowedVideo = new Set(["video/mp4", "video/quicktime", "video/webm"]);
    const images = selected.filter((f) => allowedImage.has(f.type));
    const vids = selected.filter((f) => allowedVideo.has(f.type));
    const unsupported = selected.length - images.length - vids.length;
    const oversizedImages = images.filter((f) => f.size > 10 * 1024 * 1024);
    const oversizedVideos = vids.filter((f) => f.size > 50 * 1024 * 1024);
    const validImages = images.filter((f) => f.size <= 10 * 1024 * 1024);
    const validVideos = vids.filter((f) => f.size <= 50 * 1024 * 1024);
    const remainingPhotos = Math.max(0, MAX_PHOTOS - photos.length);
    const remainingVideos = Math.max(0, MAX_VIDEOS - videos.length);
    const acceptedImages = validImages.slice(0, remainingPhotos);
    const acceptedVideos = validVideos.slice(0, remainingVideos);

    const warnings: string[] = [];
    if (unsupported) warnings.push("Некоторые файлы имеют неподдерживаемый формат");
    if (oversizedImages.length) warnings.push("Фото должны быть не больше 10 МБ");
    if (oversizedVideos.length) warnings.push("Видео должно быть не больше 50 МБ");
    if (validImages.length > remainingPhotos) warnings.push("Можно добавить максимум 5 фото");
    if (validVideos.length > remainingVideos) warnings.push("Можно добавить максимум 1 видео");

    setError(warnings.length ? warnings.join(". ") + "." : null);
    if (!acceptedImages.length && !acceptedVideos.length) return;

    if (!bikeId) {
      setPhotos((prev) => [...prev, ...acceptedImages]);
      setVideos((prev) => [...prev, ...acceptedVideos]);
      return;
    }

    setUploading(true);
    try {
      for (const img of acceptedImages) {
        const fd = new FormData();
        fd.append("file", img);
        const res = await api.upload<{ photos: string[] }>(
          `/owner/bikes/${bikeId}/photos`,
          fd,
          me?.park_id ? { park_id: me.park_id } : undefined
        );
        setPhotos(res.photos);
      }
      for (const video of acceptedVideos) {
        const fd = new FormData();
        fd.append("file", video);
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
              src={previewMedia.photos[0]}
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
          Базовая цена действует 1–2 дня. Для более долгого срока выбирается тариф соответствующего диапазона; сумма = цена за день × число дней.
        </div>
        {[
          ["3–6 дней", price3, setPrice3],
          ["7–13 дней", price7, setPrice7],
          ["14–29 дней", price14, setPrice14],
          ["30+ дней", price30, setPrice30],
        ].map(([label, value, setter]: any) => (
          <div key={label} style={{ marginBottom: 8 }}>
            <label className="label">{label}, VND / день</label>
            <input className="input" type="number" min="0"
              value={value} onChange={(e) => setter(e.target.value)} placeholder={label === "3–6 дней" ? "450000" : label === "7–13 дней" ? "420000" : label === "14–29 дней" ? "400000" : "350000"} />
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
          {photos.map((_, idx) => {
            const url = previewMedia.photos[idx];
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
          {videos.map((_, idx) => {
            const url = previewMedia.videos[idx];
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
          accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.webm,image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
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
              ...previewMedia.photos.map((src) => ({
                src,
                kind: "image" as const,
              })),
              ...previewMedia.videos.map((src) => ({
                src,
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
