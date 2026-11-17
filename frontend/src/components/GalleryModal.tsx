import { useEffect, useRef, useState } from "react";

interface Item {
  src: string;
  kind: "image" | "video";
}

interface Props {
  items: Item[];
  startIndex?: number;
  onClose: () => void;
}

export function GalleryModal({ items, startIndex = 0, onClose }: Props) {
  const [idx, setIdx] = useState(startIndex);
  const trackRef = useRef<HTMLDivElement>(null);
  const touchStartX = useRef<number | null>(null);
  const touchEndX = useRef<number | null>(null);

  function goTo(newIdx: number) {
    if (newIdx < 0) newIdx = items.length - 1;
    if (newIdx >= items.length) newIdx = 0;
    setIdx(newIdx);
    const track = trackRef.current;
    if (track) {
      const child = track.children[newIdx] as HTMLElement | undefined;
      if (child) {
        track.scrollTo({ left: child.offsetLeft, behavior: "smooth" });
      }
    }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") goTo(idx + 1);
      else if (e.key === "ArrowLeft") goTo(idx - 1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line
  }, [idx]);

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const child = track.children[startIndex] as HTMLElement | undefined;
    if (child) track.scrollLeft = child.offsetLeft;
    // eslint-disable-next-line
  }, [startIndex]);

  function onTouchStart(e: React.TouchEvent) {
    touchStartX.current = e.touches[0].clientX;
  }

  function onTouchMove(e: React.TouchEvent) {
    touchEndX.current = e.touches[0].clientX;
  }

  function onTouchEnd() {
    if (touchStartX.current === null || touchEndX.current === null) return;
    const delta = touchStartX.current - touchEndX.current;
    if (Math.abs(delta) > 50) {
      if (delta > 0) goTo(idx + 1);
      else goTo(idx - 1);
    }
    touchStartX.current = null;
    touchEndX.current = null;
  }

  function onScroll() {
    const track = trackRef.current;
    if (!track) return;
    let nearest = 0;
    let minDistance = Infinity;
    Array.from(track.children).forEach((child, i) => {
      const el = child as HTMLElement;
      const distance = Math.abs(el.offsetLeft - track.scrollLeft);
      if (distance < minDistance) {
        minDistance = distance;
        nearest = i;
      }
    });
    if (nearest !== idx) setIdx(nearest);
  }

  if (items.length === 0) return null;

  return (
    <div className="gallery-modal" onClick={onClose}>
      <button
        className="gallery-modal-close"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        aria-label="Закрыть"
      >
        ×
      </button>

      <div className="gallery-modal-counter">
        {idx + 1} / {items.length}
      </div>

      <div
        className="gallery-modal-track"
        ref={trackRef}
        onClick={(e) => e.stopPropagation()}
        onScroll={onScroll}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        {items.map((item, i) => (
          <div key={i} className="gallery-modal-slide">
            {item.kind === "video" ? (
              <video src={item.src} controls autoPlay={i === idx} />
            ) : (
              <img src={item.src} alt={`Медиа ${i + 1}`} />
            )}
          </div>
        ))}
      </div>

      {items.length > 1 && (
        <div className="gallery-modal-dots">
          {items.map((_, i) => (
            <button
              key={i}
              className={`gallery-modal-dot ${i === idx ? "active" : ""}`}
              onClick={(e) => {
                e.stopPropagation();
                goTo(i);
              }}
              aria-label={`Перейти к ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
