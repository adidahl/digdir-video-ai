import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { videosAPI } from "../api/videos";
import { searchAPI } from "../api/search";
import type { SearchRequest } from "../types/video";

export const useVideos = () => {
  return useQuery({
    queryKey: ["videos"],
    queryFn: videosAPI.list,
  });
};

export const useVideo = (id: string) => {
  return useQuery({
    queryKey: ["video", id],
    queryFn: () => videosAPI.get(id),
    enabled: !!id,
  });
};

export const useVideoSegments = (id: string) => {
  return useQuery({
    queryKey: ["videoSegments", id],
    queryFn: () => videosAPI.getSegments(id),
    enabled: !!id,
  });
};

export const useUploadVideo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      title,
      description,
      security_level,
    }: {
      file: File;
      title: string;
      description?: string;
      security_level?: string;
    }) => videosAPI.upload(file, title, description, security_level),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
    },
  });
};

export const useSearchVideos = () => {
  return useMutation({
    mutationFn: (request: SearchRequest) => searchAPI.search(request),
  });
};

