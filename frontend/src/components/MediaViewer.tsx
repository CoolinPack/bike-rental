import { useState } from "react";

export interface MediaItem {
 src: string;
 kind: "image" | "video";
}

interface Props {
 items: MediaItem[];
 onOpen?: (idx: number) => void;
 allowSetMain?: boolean;
 onSetMain?: (idx: number) => void;
}

export function MediaViewer({
 items,
 onOpen,
 allowSetMain,
 onSetMain,
}: Props) {
 const [idx, setIdx] = useState(0);
 if (items.length === 0) return null;
 const current = items[idx];
 const isImage = current.kind === "image";

 function prev() {
 setIdx((v) => (v - 1 + items.length) % items.length);
 }
 function next() {
 setIdx((v) => (v + 1) % items.length);
 }

 return (
 <>
 <div
 className="media-single-view"
 onClick={() => onOpen?.(idx)}
 >
 {isImage ? (
 <img src={current.src} alt="" draggable={false} />
 ) : (
 <video src={current.src} controls />
 )}

 {items.length > 1 && (
 <>
 <button
 className="media-single-view-arrow left"
 onClick={(e) => {
 e.stopPropagation();
 prev();
 }}
 aria-label="Назад"
 >
 ‹
 </button>
 <button
 className="media-single-view-arrow right"
 onClick={(e) => {
 e.stopPropagation();
 next();
 }}
 aria-label="Вперёд"
 >
 ›
 </button>
 </>
 )}

 {idx === 0 && (
 <span className="media-single-view-main-badge">Главное</span>
 )}

 {allowSetMain && idx !== 0 && isImage && onSetMain && (
 <button
 className="media-single-view-set-main"
 onClick={(e) => {
 e.stopPropagation();
 onSetMain(idx);
 setIdx(0);
 }}
 >
 Сделать главной
 </button>
 )}
 </div>

 {items.length > 1 && (
 <div className="media-single-view-thumbs">
 {items.map((it, i) => (
 <button
 key={i}
 className={`media-thumb ${i === idx ? "active" : ""}`}
 onClick={() => setIdx(i)}
 aria-label={`Фото ${i + 1}`}
 >
 {it.kind === "image" ? (
 <img src={it.src} alt="" />
 ) : (
 <>
 <video src={it.src} />
 <div className="media-thumb-video">▶</div>
 </>
 )}
 {i === 0 && <div className="media-thumb-main">Главное</div>}
 </button>
 ))}
 </div>
 )}
 </>
 );
}
