import { useEffect, useRef } from "react";

interface VideoPlayerProps {
  videoId: string;
  startTime?: number;
}

export default function VideoPlayer({ videoId, startTime = 0 }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current && startTime > 0) {
      videoRef.current.currentTime = startTime;
    }
  }, [startTime]);

  // In production, this would fetch the actual video URL from the backend
  const videoUrl = `/api/videos/${videoId}/stream`;

  return (
    <video
      ref={videoRef}
      controls
      style={{ width: "100%", maxWidth: "800px" }}
      src={videoUrl}
    >
      Your browser does not support the video tag.
    </video>
  );
}

