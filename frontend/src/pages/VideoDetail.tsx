import { useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Heading, Card, Paragraph } from "@digdir/designsystemet-react";
import Header from "../components/layout/Header";
import VideoPlayer from "../components/video/VideoPlayer";
import { useVideo, useVideoSegments } from "../hooks/useVideos";

export default function VideoDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const startTime = parseInt(searchParams.get("t") || "0", 10);

  const { data: video, isLoading: videoLoading } = useVideo(id!);
  const { data: segments, isLoading: segmentsLoading } = useVideoSegments(id!);

  if (videoLoading || segmentsLoading) {
    return (
      <div>
        <Header />
        <div style={{ padding: "2rem" }}>{t("common.loading")}</div>
      </div>
    );
  }

  if (!video) {
    return (
      <div>
        <Header />
        <div style={{ padding: "2rem" }}>Video not found</div>
      </div>
    );
  }

  return (
    <div>
      <Header />
      
      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem" }}>
        <Heading level={1} size="lg" style={{ marginBottom: "1rem" }}>
          {video.title}
        </Heading>
        
        {video.description && (
          <Paragraph style={{ marginBottom: "1rem" }}>{video.description}</Paragraph>
        )}
        
        <div style={{ marginBottom: "2rem" }}>
          <VideoPlayer videoId={id!} startTime={startTime} />
        </div>
        
        <Heading level={2} size="md" style={{ marginBottom: "1rem" }}>
          Transcript
        </Heading>
        
        {segments && segments.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {segments.map((segment) => (
              <Card key={segment.id} style={{ padding: "1rem" }}>
                <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.875rem", color: "#666" }}>
                  {Math.floor(segment.start_time)}s - {Math.floor(segment.end_time)}s
                </p>
                <p>{segment.text}</p>
              </Card>
            ))}
          </div>
        ) : (
          <p>No transcript available</p>
        )}
      </div>
    </div>
  );
}

