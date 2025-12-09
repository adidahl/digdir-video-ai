export enum SecurityLevel {
  PUBLIC = "public",
  INTERNAL = "internal",
  CONFIDENTIAL = "confidential",
  SECRET = "secret",
}

export enum VideoStatus {
  UPLOADING = "uploading",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
}

export interface Video {
  id: string;
  title: string;
  description?: string;
  organization_id: string;
  uploaded_by: string;
  security_level: SecurityLevel;
  status: VideoStatus;
  duration?: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface VideoSegment {
  id: string;
  video_id: string;
  segment_id: number;
  start_time: number;
  end_time: number;
  text: string;
}

export interface SearchResult {
  video: Video;
  segment: VideoSegment;
  score: number;
  url: string;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  security_level_filter?: SecurityLevel[];
}

