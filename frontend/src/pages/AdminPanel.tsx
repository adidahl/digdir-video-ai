import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Heading, Tabs, Button, Textfield, Card, Select } from "@digdir/designsystemet-react";
import Header from "../components/layout/Header";
import { useUploadVideo, useVideos } from "../hooks/useVideos";
import { SecurityLevel } from "../types/video";
import { videosAPI } from "../api/videos";

export default function AdminPanel() {
  const { t } = useTranslation();
  
  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [securityLevel, setSecurityLevel] = useState<SecurityLevel>(SecurityLevel.INTERNAL);
  
  const uploadMutation = useUploadVideo();
  const { data: videos, refetch } = useVideos();
  const [reprocessing, setReprocessing] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleReprocess = async (videoId: string) => {
    try {
      setReprocessing(videoId);
      await videosAPI.reprocess(videoId);
      await refetch();
    } catch (error) {
      console.error("Reprocess error:", error);
      alert("Failed to restart processing. Please try again.");
    } finally {
      setReprocessing(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) return;

    try {
      await uploadMutation.mutateAsync({
        file,
        title,
        description,
        security_level: securityLevel,
      });
      
      // Reset form
      setFile(null);
      setTitle("");
      setDescription("");
      setSecurityLevel(SecurityLevel.INTERNAL);
      
      // Refetch videos
      refetch();
    } catch (error) {
      console.error("Upload error:", error);
    }
  };

  return (
    <div>
      <Header />
      
      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem" }}>
        <Heading level={1} size="lg" style={{ marginBottom: "2rem" }}>
          {t("admin.title")}
        </Heading>
        
        <Tabs defaultValue="upload">
          <Tabs.List>
            <Tabs.Tab value="upload">{t("video.upload")}</Tabs.Tab>
            <Tabs.Tab value="videos">{t("admin.videos")}</Tabs.Tab>
            <Tabs.Tab value="users">{t("admin.users")}</Tabs.Tab>
          </Tabs.List>
          
          <Tabs.Panel value="upload" style={{ padding: "2rem 0" }}>
            <Card style={{ padding: "2rem" }}>
              <Heading level={2} size="md" style={{ marginBottom: "1rem" }}>
                {t("video.upload")}
              </Heading>
              
              <form onSubmit={handleUpload} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <div>
                  <label style={{ display: "block", marginBottom: "0.5rem" }}>
                    {t("video.selectFile")}
                  </label>
                  <input
                    type="file"
                    accept="video/*"
                    onChange={handleFileChange}
                    required
                  />
                </div>
                
                <Textfield
                  label={t("video.title")}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
                
                <Textfield
                  label={t("video.description")}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
                
                <Select
                  label={t("video.securityLevel")}
                  value={securityLevel}
                  onChange={(e) => setSecurityLevel(e.target.value as SecurityLevel)}
                >
                  <option value={SecurityLevel.PUBLIC}>Public</option>
                  <option value={SecurityLevel.INTERNAL}>Internal</option>
                  <option value={SecurityLevel.CONFIDENTIAL}>Confidential</option>
                  <option value={SecurityLevel.SECRET}>Secret</option>
                </Select>
                
                <Button type="submit" disabled={!file || uploadMutation.isPending}>
                  {uploadMutation.isPending ? t("common.loading") : t("video.uploadButton")}
                </Button>
              </form>
            </Card>
          </Tabs.Panel>
          
          <Tabs.Panel value="videos" style={{ padding: "2rem 0" }}>
            <Heading level={2} size="md" style={{ marginBottom: "1rem" }}>
              {t("admin.videos")}
            </Heading>
            
            {videos && videos.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {videos.map((video) => (
                  <Card key={video.id} style={{ padding: "1rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ flex: 1 }}>
                        <Heading level={3} size="sm">{video.title}</Heading>
                        <p style={{ margin: "0.5rem 0", color: "#666" }}>
                          {t("video.status")}: {video.status}
                        </p>
                        {video.description && <p>{video.description}</p>}
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleReprocess(video.id)}
                        disabled={reprocessing === video.id}
                      >
                        {reprocessing === video.id ? "Reprocessing..." : 
                          video.status === "completed" ? "Reprocess" : "Restart Processing"}
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <p>No videos found</p>
            )}
          </Tabs.Panel>
          
          <Tabs.Panel value="users" style={{ padding: "2rem 0" }}>
            <Heading level={2} size="md" style={{ marginBottom: "1rem" }}>
              {t("admin.users")}
            </Heading>
            <p>User management interface coming soon...</p>
          </Tabs.Panel>
        </Tabs>
      </div>
    </div>
  );
}

