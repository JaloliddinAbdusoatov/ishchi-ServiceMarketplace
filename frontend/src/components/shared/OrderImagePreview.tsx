import { useEffect, useState } from "react";
import { apiClient } from "@/services/apiClient";
import { useAuthStore } from "@/stores/authStore";

export function OrderImagePreview({ orderId, imageId, alt }: {
  orderId: string; imageId: string; alt: string;
}) {
  const revision = useAuthStore((state) => state.sessionRevision);
  const [image, setImage] = useState<{ url: string; revision: number } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | undefined;
    setImage(null);
    apiClient.get(`/orders/${orderId}/images/${imageId}/content/`, {
      responseType: "blob", signal: controller.signal,
    }).then((response) => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(response.data);
      setImage({ url: objectUrl, revision });
    }).catch(() => { /* Keep the alt text when the image is inaccessible. */ });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [orderId, imageId, revision]);
  return <img src={image?.revision === revision ? image.url : undefined}
    alt={alt} className="h-32 w-full rounded-lg object-cover border" />;
}
