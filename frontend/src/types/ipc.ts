export interface MediaFormat {
  format_id: string;
  resolution: string;
  ext: 'mp4' | 'mkv' | 'webm' | 'mp3' | 'm4a';
  vcodec?: string;
  acodec?: string;
  filesize_approx_mb?: number;
  fps?: number;
}

export interface AnalyzeUrlOutput {
  status: 'success' | 'error';
  url: string;
  title?: string;
  thumbnail_url?: string;
  duration_sec?: number;
  available_formats?: MediaFormat[];
  is_hls_dash?: boolean;
  error_code?: 'INVALID_URL' | 'WAF_BLOCKED' | 'DRM_PROTECTED' | 'NETWORK_TIMEOUT';
  error_message?: string;
}

export interface DownloadTaskProgress {
  task_id: string;
  url: string;
  title: string;
  status: 'pending' | 'waking_node' | 'downloading' | 'merging_ffmpeg' | 'sftp_transferring' | 'completed' | 'failed';
  progress_percent: number;
  speed_mbps: number;
  downloaded_bytes: number;
  total_bytes: number;
  eta_sec: number;
  current_node: 'local' | '192.168.100.22';
  ram_spillover_active: boolean;
  sftp_atomic_file?: string;
  error_message?: string;
}

export interface QueueTelemetryOutput {
  active_tasks: DownloadTaskProgress[];
  completed_tasks_count: number;
  local_ram_usage_percent: number;
  remote_node_status: 'offline' | 'waking' | 'online' | 'sleeping';
  remote_node_ping_ms?: number;
}
