import { GalleryModal } from "./GalleryModal";

interface Props {
  src: string;
  kind?: "image" | "video";
  onClose: () => void;
}

export function ImageViewer({ src, kind = "image", onClose }: Props) {
  return (
    <GalleryModal
      items={[{ src, kind }]}
      startIndex={0}
      onClose={onClose}
    />
  );
}
