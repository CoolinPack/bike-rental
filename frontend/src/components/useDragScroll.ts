import { useEffect, useRef } from "react";

export function useDragScroll<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const isDown = useRef(false);
  const startX = useRef(0);
  const startScrollLeft = useRef(0);
  const moved = useRef(false);

  function onMouseDown(e: React.MouseEvent) {
    if (!ref.current) return;
    isDown.current = true;
    moved.current = false;
    startX.current = e.pageX;
    startScrollLeft.current = ref.current.scrollLeft;
  }

  function onMouseMove(e: React.MouseEvent) {
    if (!isDown.current || !ref.current) return;
    e.preventDefault();
    const delta = e.pageX - startX.current;
    if (Math.abs(delta) > 3) moved.current = true;
    ref.current.scrollLeft = startScrollLeft.current - delta;
  }

  function endDrag() {
    isDown.current = false;
  }

  function onClickCapture(e: React.MouseEvent) {
    if (moved.current) {
      e.stopPropagation();
      e.preventDefault();
      moved.current = false;
    }
  }

  return {
    ref,
    handlers: {
      onMouseDown,
      onMouseMove,
      onMouseUp: endDrag,
      onMouseLeave: endDrag,
      onClickCapture,
    },
  };
}

export function useLockBodyScroll() {
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);
}
