import React, { useState, useEffect } from 'react';
import { 
  Download, 
  Search, 
  Server, 
  Laptop, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  Cpu, 
  Zap, 
  HardDrive, 
  RefreshCw, 
  AlertTriangle,
  Play,
  FileVideo
} from 'lucide-react';

import { AnalyzeUrlOutput, MediaFormat, DownloadTaskProgress, QueueTelemetryOutput } from './types/ipc';

const API_BASE = "http://localhost:8000/api";

export function App() {
  const [urlInput, setUrlInput] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeData, setAnalyzeData] = useState<AnalyzeUrlOutput | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<MediaFormat | null>(null);
  const [nodeTarget, setNodeTarget] = useState<'local' | 'remote_node'>('local');
  
  // Telemetry & Queue state
  const [queue, setQueue] = useState<DownloadTaskProgress[]>([]);
  const [ramPercent, setRamPercent] = useState<number>(35.0);
  const [remoteStatus, setRemoteStatus] = useState<'offline' | 'waking' | 'online' | 'sleeping'>('offline');
  
  // WOL Timeout Dialog state
  const [showWolAlert, setShowWolAlert] = useState(false);
  const [unreachableTask, setUnreachableTask] = useState<string | null>(null);

  // Poll Queue & System Status every 2s
  useEffect(() => {
    const fetchQueue = async () => {
      try {
        const res = await fetch(`${API_BASE}/queue`);
        if (res.ok) {
          const data: QueueTelemetryOutput = await res.json();
          setQueue(data.active_tasks);
          setRamPercent(data.local_ram_usage_percent);
          setRemoteStatus(data.remote_node_status);
        }
      } catch (err) {
        // Backend engine not started yet, load mock status for preview
      }
    };

    fetchQueue();
    const interval = setInterval(fetchQueue, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setIsAnalyzing(true);
    setAnalyzeData(null);
    setSelectedFormat(null);

    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput, use_stealth_ja3: true }),
      });
      const data: AnalyzeUrlOutput = await res.json();
      setAnalyzeData(data);
      if (data.available_formats && data.available_formats.length > 0) {
        setSelectedFormat(data.available_formats[data.available_formats.length - 1]);
      }
    } catch (err) {
      // Mock Fallback for UI demonstration if engine is starting
      setAnalyzeData({
        status: 'success',
        url: urlInput,
        title: 'Demo Stream: High Performance 4K Nature Showcase',
        thumbnail_url: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop&q=60',
        duration_sec: 720,
        is_hls_dash: true,
        available_formats: [
          { format_id: '1080p', resolution: '1920x1080', ext: 'mp4', filesize_approx_mb: 240, fps: 60 },
          { format_id: '1440p', resolution: '2560x1440 (2K)', ext: 'mp4', filesize_approx_mb: 580, fps: 60 },
          { format_id: '2160p', resolution: '3840x2160 (4K)', ext: 'mp4', filesize_approx_mb: 1250, fps: 60 }
        ]
      });
      setSelectedFormat({ format_id: '2160p', resolution: '3840x2160 (4K)', ext: 'mp4', filesize_approx_mb: 1250, fps: 60 });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleStartDownload = async () => {
    if (!analyzeData) return;

    const payload = {
      url: analyzeData.url,
      format_id: selectedFormat?.format_id || 'best',
      save_path: 'downloads\\media',
      priority: 'high',
      node_target: nodeTarget
    };

    try {
      if (nodeTarget === 'remote_node') {
        const res = await fetch(`${API_BASE}/offload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task_id: 'task_' + Date.now(), url: analyzeData.url }),
        });
        const result = await res.json();
        if (result.status === 'node_unreachable') {
          setUnreachableTask(analyzeData.url);
          setShowWolAlert(true);
          return;
        }
      } else {
        await fetch(`${API_BASE}/download`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }
    } catch (err) {
      // Add local mock task for GUI preview
      setQueue(prev => [
        {
          task_id: 'task_' + Date.now().toString().slice(-4),
          url: analyzeData.url,
          title: analyzeData.title || 'Media Stream',
          status: nodeTarget === 'remote_node' ? 'sftp_transferring' : 'downloading',
          progress_percent: 42.5,
          speed_mbps: 18.4,
          downloaded_bytes: 450000000,
          total_bytes: 1250000000,
          eta_sec: 38,
          current_node: nodeTarget === 'remote_node' ? '192.168.100.22' : 'local',
          ram_spillover_active: false,
          sftp_atomic_file: 'video.mp4.tmp -> video.mp4'
        },
        ...prev
      ]);
    }
  };

  return (
    <div className="min-h-screen p-6 max-w-7xl mx-auto flex flex-col gap-6">
      
      {/* Header Bar */}
      <header className="glass-panel rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-tr from-indigo-600 to-emerald-500 rounded-xl shadow-lg glow-indigo">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wide text-white flex items-center gap-2">
              Media Downloader <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">v2.4</span>
            </h1>
            <p className="text-xs text-gray-400">Stealth Multi-Threaded Harvester & Compute Node Offloader</p>
          </div>
        </div>

        {/* Live System Telemetry Badges */}
        <div className="flex items-center gap-3">
          {/* Local RAM Monitor */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
            <Cpu className="w-4 h-4 text-indigo-400" />
            <span className="text-gray-400">Laptop RAM:</span>
            <span className={`font-semibold ${ramPercent > 80 ? 'text-amber-400 font-bold' : 'text-emerald-400'}`}>
              {ramPercent.toFixed(1)}%
            </span>
            {ramPercent > 80 && <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1 rounded">Spillover</span>}
          </div>

          {/* Remote Node Badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
            <Server className={`w-4 h-4 ${remoteStatus === 'online' ? 'text-emerald-400' : remoteStatus === 'waking' ? 'text-amber-400 animate-spin' : 'text-gray-500'}`} />
            <span className="text-gray-400">Remote Node (.22):</span>
            <span className={`font-semibold capitalize ${
              remoteStatus === 'online' ? 'text-emerald-400' : remoteStatus === 'waking' ? 'text-amber-400' : 'text-gray-500'
            }`}>
              {remoteStatus}
            </span>
          </div>
        </div>
      </header>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: URL Input & Media Format Selector (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          
          {/* URL Input Box */}
          <div className="glass-panel rounded-2xl p-6 flex flex-col gap-4">
            <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <Search className="w-4 h-4 text-indigo-400" /> Enter Media Link or Playlist
            </h2>

            <form onSubmit={handleAnalyze} className="flex items-center gap-3">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=... or VK, Rutube, .m3u8"
                  className="w-full bg-gray-900/80 border border-gray-700/80 rounded-xl px-4 py-3.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>

              <button
                type="submit"
                disabled={isAnalyzing || !urlInput.trim()}
                className="px-5 py-3.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium rounded-xl text-sm flex items-center gap-2 transition glow-indigo cursor-pointer"
              >
                {isAnalyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
                Analyze
              </button>
            </form>
          </div>

          {/* Analysis Result & Format Selection */}
          {analyzeData && analyzeData.status === 'success' && (
            <div className="glass-panel rounded-2xl p-6 flex flex-col gap-5 border border-indigo-500/20">
              <div className="flex gap-4">
                {analyzeData.thumbnail_url && (
                  <img 
                    src={analyzeData.thumbnail_url} 
                    alt={analyzeData.title}
                    className="w-36 h-24 object-cover rounded-xl border border-gray-700/60 shadow-md"
                  />
                )}
                <div className="flex-1 flex flex-col justify-between">
                  <div>
                    <h3 className="font-semibold text-white text-base line-clamp-2">{analyzeData.title}</h3>
                    <p className="text-xs text-gray-400 mt-1 flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5 text-indigo-400" />
                      {analyzeData.duration_sec ? `${Math.floor(analyzeData.duration_sec / 60)} mins` : 'Live Stream'}
                      {analyzeData.is_hls_dash && <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30">HLS/DASH</span>}
                    </p>
                  </div>
                </div>
              </div>

              {/* Resolution Picker */}
              <div className="flex flex-col gap-2">
                <label className="text-xs text-gray-400 font-medium">Select Output Resolution & Format:</label>
                <div className="grid grid-cols-3 gap-2">
                  {analyzeData.available_formats?.map((fmt) => (
                    <button
                      key={fmt.format_id}
                      onClick={() => setSelectedFormat(fmt)}
                      className={`p-2.5 rounded-xl border text-xs font-medium text-left flex flex-col gap-1 transition ${
                        selectedFormat?.format_id === fmt.format_id
                          ? 'bg-indigo-600/30 border-indigo-500 text-white shadow-md'
                          : 'bg-gray-900/40 border-gray-800 text-gray-400 hover:border-gray-700'
                      }`}
                    >
                      <span className="font-bold text-gray-200">{fmt.resolution}</span>
                      <span className="text-[10px] text-gray-500">{fmt.ext.toUpperCase()} {fmt.filesize_approx_mb ? `~${fmt.filesize_approx_mb} MB` : ''}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Node Target Switcher */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-gray-900/60 border border-gray-800">
                <span className="text-xs text-gray-300 font-medium flex items-center gap-2">
                  <HardDrive className="w-4 h-4 text-indigo-400" /> Execution Compute Node:
                </span>
                
                <div className="flex items-center gap-1 bg-gray-950 p-1 rounded-lg border border-gray-800">
                  <button
                    onClick={() => setNodeTarget('local')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition ${
                      nodeTarget === 'local' ? 'bg-indigo-600 text-white shadow' : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Laptop className="w-3.5 h-3.5" /> Local Laptop
                  </button>
                  <button
                    onClick={() => setNodeTarget('remote_node')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition ${
                      nodeTarget === 'remote_node' ? 'bg-emerald-600 text-white shadow' : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Server className="w-3.5 h-3.5" /> Remote Node (.22)
                  </button>
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={handleStartDownload}
                className="w-full py-3.5 bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 text-white font-bold rounded-xl text-sm shadow-xl flex items-center justify-center gap-2 transition glow-emerald cursor-pointer"
              >
                <Download className="w-5 h-5" />
                Start Download ({nodeTarget === 'remote_node' ? 'Offload to .22' : 'Local'})
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Download Queue & Telemetry (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="glass-panel rounded-2xl p-6 flex flex-col gap-4 min-h-[420px]">
            <h2 className="text-sm font-semibold text-gray-300 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <FileVideo className="w-4 h-4 text-emerald-400" /> Active Queue & Telemetry
              </span>
              <span className="text-[11px] px-2.5 py-1 rounded-lg bg-gray-900 border border-gray-800 text-indigo-300 font-mono">
                📁 D:\Создание программ\downloads\media
              </span>
            </h2>

            {queue.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 border border-dashed border-gray-800 rounded-xl text-gray-500">
                <Download className="w-10 h-10 mb-2 opacity-30 text-indigo-400" />
                <p className="text-sm font-medium">Queue is currently empty</p>
                <p className="text-xs text-gray-600 mt-1">Paste a media URL on the left to start downloading</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3 overflow-y-auto max-h-[500px] pr-1">
                {queue.map((task) => (
                  <div key={task.task_id} className="glass-card rounded-xl p-4 flex flex-col gap-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-xs font-semibold text-gray-200 line-clamp-1">{task.title}</h4>
                        <span className="text-[10px] text-gray-400 flex items-center gap-1.5 mt-0.5">
                          {task.current_node === 'local' ? <Laptop className="w-3 h-3 text-indigo-400" /> : <Server className="w-3 h-3 text-emerald-400" />}
                          Node: {task.current_node}
                        </span>
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                        task.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                        task.status === 'sftp_transferring' ? 'bg-amber-500/20 text-amber-300' : 'bg-indigo-500/20 text-indigo-400'
                      }`}>
                        {task.status.replace('_', ' ')}
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-gray-900 rounded-full h-2 overflow-hidden border border-gray-800">
                      <div 
                        className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-full rounded-full transition-all duration-300"
                        style={{ width: `${task.progress_percent}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-gray-400">
                      <span>{task.speed_mbps} MB/s</span>
                      {task.sftp_atomic_file && (
                        <span className="text-[10px] text-amber-400 font-mono">Atomic: .tmp → .mp4</span>
                      )}
                      <span>{task.progress_percent.toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Remote Node Unreachable Modal Alert */}
      {showWolAlert && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div className="glass-panel rounded-2xl p-6 max-w-md w-full border border-amber-500/40 flex flex-col gap-4 shadow-2xl">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="w-7 h-7" />
              <h3 className="font-bold text-lg text-white">Remote Node Unreachable</h3>
            </div>

            <p className="text-xs text-gray-300 leading-relaxed">
              Remote Node <code className="text-amber-300 bg-gray-900 px-1 py-0.5 rounded">192.168.100.22</code> did not respond to WOL Magic Packet within 45 seconds.
            </p>

            <div className="flex gap-3 mt-2">
              <button
                onClick={() => setShowWolAlert(false)}
                className="flex-1 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold rounded-xl transition"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setNodeTarget('local');
                  setShowWolAlert(false);
                  handleStartDownload();
                }}
                className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl transition glow-indigo"
              >
                Download Locally
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
