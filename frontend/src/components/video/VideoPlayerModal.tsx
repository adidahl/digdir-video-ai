import { useEffect, useRef, useState } from "react";
import { Dialog, DialogBlock, Button, Paragraph, Spinner } from "@digdir/designsystemet-react";
import type { MessageSource } from "../../types/chat";

interface VideoPlayerModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: MessageSource | null;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function VideoPlayerModal({ isOpen, onClose, source }: VideoPlayerModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSeekedToTimestamp, setHasSeekedToTimestamp] = useState(false);
  const [initialTimestamp, setInitialTimestamp] = useState<number | null>(null);

  // Handle modal close - stop video playback
  const handleClose = () => {
    const video = videoRef.current;
    if (video) {
      video.pause();
      video.currentTime = 0;
      video.src = "";
    }
    setHasSeekedToTimestamp(false);
    setInitialTimestamp(null);
    onClose();
  };

  useEffect(() => {
    if (isOpen && source) {
      setIsLoading(true);
      setInitialTimestamp(source.timestamp);
      setHasSeekedToTimestamp(false);
      
      // Create video URL with token as query parameter
      // Video elements can't send custom headers, so we use query param
      const token = localStorage.getItem("access_token");
      const url = `${API_BASE_URL}/api/videos/${source.video_id}/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`;
      
      console.log("VideoPlayerModal: Setting video URL:", url);
      console.log("VideoPlayerModal: Source:", source);
      setVideoUrl(url);
    } else {
      // When modal closes, stop video
      const video = videoRef.current;
      if (video) {
        video.pause();
        video.currentTime = 0;
      }
      setVideoUrl(null);
      setIsLoading(false);
      setHasSeekedToTimestamp(false);
      setInitialTimestamp(null);
    }
  }, [isOpen, source]);

  // Handle video loading and seeking - only seek once on initial load
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !source || !isOpen || !initialTimestamp) return;

    const handleLoadedMetadata = () => {
      console.log("VideoPlayerModal: Metadata loaded, duration:", video.duration);
      setIsLoading(false);
      
      // Only seek to timestamp on initial load, not on user interaction
      if (!hasSeekedToTimestamp && initialTimestamp !== null) {
        console.log("VideoPlayerModal: Seeking to initial timestamp:", initialTimestamp);
        video.currentTime = initialTimestamp;
        setHasSeekedToTimestamp(true);
        
        // Try to play
        video.play().then(() => {
          console.log("VideoPlayerModal: Video playing successfully");
        }).catch((err) => {
          console.error("VideoPlayerModal: Error playing video:", err);
          // If autoplay fails, at least seek to the right position
          // User can click play manually
        });
      }
    };

    const handleCanPlay = () => {
      // Only auto-seek if we haven't seeked yet (initial load)
      if (!hasSeekedToTimestamp && initialTimestamp !== null) {
        if (Math.abs(video.currentTime - initialTimestamp) > 1) {
          video.currentTime = initialTimestamp;
          setHasSeekedToTimestamp(true);
        }
      }
    };

    // Track user seeking - if user moves slider, don't auto-seek anymore
    const handleSeeking = () => {
      // If user is seeking manually, mark as seeked
      if (hasSeekedToTimestamp) {
        // User is actively seeking, don't interfere
        return;
      }
    };

    const handleSeeked = () => {
      // After user finishes seeking, allow them to control playback
      setHasSeekedToTimestamp(true);
    };

    const handleError = (e: Event) => {
      setIsLoading(false);
      console.error("Error loading video:", e);
      const error = video.error;
      if (error) {
        console.error("Video error code:", error.code, "Message:", error.message);
      }
    };

    // Only add listeners if video has a source
    if (video.src) {
      video.addEventListener("loadedmetadata", handleLoadedMetadata);
      video.addEventListener("canplay", handleCanPlay);
      video.addEventListener("seeking", handleSeeking);
      video.addEventListener("seeked", handleSeeked);
      video.addEventListener("error", handleError);

      // If metadata is already loaded, seek immediately (only if not seeked yet)
      if (video.readyState >= 1 && !hasSeekedToTimestamp && initialTimestamp !== null) {
        video.currentTime = initialTimestamp;
        setHasSeekedToTimestamp(true);
      }

      return () => {
        video.removeEventListener("loadedmetadata", handleLoadedMetadata);
        video.removeEventListener("canplay", handleCanPlay);
        video.removeEventListener("seeking", handleSeeking);
        video.removeEventListener("seeked", handleSeeked);
        video.removeEventListener("error", handleError);
      };
    }
  }, [videoUrl, source, isOpen, hasSeekedToTimestamp, initialTimestamp]);

  if (!source) return null;

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <Dialog open={isOpen} onClose={handleClose}>
      <DialogBlock heading={source.video_title}>
        <div style={{ marginBottom: "1rem", position: "relative", minHeight: "300px" }}>
          {isLoading && (
            <div style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              zIndex: 10,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "0.5rem"
            }}>
              <Spinner size="medium" />
              <Paragraph style={{ margin: 0, fontSize: "0.875rem", color: "#666" }}>
                Loading video...
              </Paragraph>
            </div>
          )}
          <video
            ref={videoRef}
            src={videoUrl || undefined}
            controls
            preload="metadata"
            style={{
              width: "100%",
              maxHeight: "60vh",
              backgroundColor: "#000",
              opacity: isLoading ? 0.3 : 1,
              display: videoUrl ? "block" : "none",
            }}
            crossOrigin="anonymous"
            onError={(e) => {
              console.error("Video element error:", e);
              setIsLoading(false);
            }}
          />
          {!videoUrl && !isLoading && (
            <div style={{
              padding: "2rem",
              textAlign: "center",
              color: "#666"
            }}>
              <Paragraph>Video URL not available</Paragraph>
            </div>
          )}
        </div>
        
        <div style={{ marginBottom: "1rem" }}>
          <Paragraph>
            <strong>Timestamp:</strong> {formatTime(source.timestamp)}
          </Paragraph>
        </div>
        
        {source.text && (
          <div style={{ 
            padding: "1rem", 
            backgroundColor: "#f5f5f5", 
            borderRadius: "4px",
            marginTop: "1rem"
          }}>
            <Paragraph>
              <strong>Transcript:</strong>
            </Paragraph>
            <Paragraph>{source.text}</Paragraph>
          </div>
        )}
        
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "1.5rem" }}>
          <Button onClick={handleClose}>Close</Button>
        </div>
      </DialogBlock>
    </Dialog>
  );
}

