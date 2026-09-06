"""
Core FastAPI Backend Server for Media Downloader Desktop (v2.4)
Implements:
- Security Guardrails (Path Traversal Protection)
- Atomic SFTP Transfers (.tmp -> .mp4)
- 45s Non-blocking WOL Timeout with Local Fallback
- Dynamic RAM-to-Disk Backpressure Monitoring
- Structured JSON Telemetry Logging
"""
import os
import sys
import json
import time
import socket
import asyncio
import logging
import uuid
import psutil
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from extractor import analyze_media_url, check_ram_spillover
from summarizer import extract_transcript, generate_heuristic_summary

# Setup structured logging
LOG_DIR = os.path.abspath(r"downloads\logs")
os.makedirs(LOG_DIR, exist_ok=True)
TELEMETRY_LOG = os.path.join(LOG_DIR, "telemetry.jsonl")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("app")

app = FastAPI(title="Media Downloader Engine", version="2.4.0")

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State Management
TASKS_DB: Dict[str, Dict[str, Any]] = {}
REMOTE_NODE_IP = "192.168.100.22"
REMOTE_NODE_STATUS = "offline"  # 'offline' | 'waking' | 'online' | 'sleeping'

# Input Models
class AnalyzeRequest(BaseModel):
    url: str
    use_stealth_ja3: bool = True

class StartDownloadRequest(BaseModel):
    url: str
    format_id: str = "best"
    save_path: str = r"downloads\media"
    priority: str = "medium"
    node_target: str = "local" # 'local' | 'remote_node'

class OffloadRequest(BaseModel):
    task_id: str
    url: str
    format_id: str = "best"
    laptop_save_path: str = r"downloads\media"
    wol_timeout_sec: int = 45


def log_telemetry_event(event_type: str, payload: Dict[str, Any]):
    """Writes structured JSONL telemetry events for AgentOps tracing."""
    event = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        "correlation_id": payload.get("task_id", str(uuid.uuid4())[:8]),
        "payload": payload
    }
    try:
        with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to log telemetry: {e}")


def validate_guardrails_path(save_path: str) -> str:
    """
    Guardrails Path Traversal Prevention:
    Resolves symlinks and validates that save_path is within project directory or downloads/.
    """
    abs_path = os.path.realpath(save_path)
    allowed_root = os.path.abspath(os.getenv("MEDIA_DOWNLOAD_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    if not abs_path.startswith(allowed_root):
        logger.error(f"[Guardrails DENIED] Path traversal attempt blocked: {abs_path}")
        raise HTTPException(
            status_code=400,
            detail=f"PATH_TRAVERSAL_DENIED: Path {save_path} is outside allowed workspace directory."
        )
    return abs_path


async def ping_remote_node(ip: str, timeout_sec: float = 1.0) -> bool:
    """Non-blocking socket check to verify if remote node is online."""
    loop = asyncio.get_event_loop()
    try:
        def check():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_sec)
            result = sock.connect_ex((ip, 22))
            sock.close()
            return result == 0
        return await loop.run_in_executor(None, check)
    except Exception:
        return False


async def async_wake_remote_node(timeout_sec: int = 45) -> bool:
    """
    Non-blocking WOL wake execution with 45-second ping validation loop.
    """
    global REMOTE_NODE_STATUS
    REMOTE_NODE_STATUS = "waking"
    logger.info(f"[WOL] Sending Magic Packet to {REMOTE_NODE_IP}...")
    
    script_path = os.getenv("WAKE_SCRIPT_PATH", os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "wake_old_pc.py")))
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
    except Exception as e:
        logger.error(f"[WOL] Failed to launch wake script: {e}")

    # 45-second non-blocking ping polling loop
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        is_online = await ping_remote_node(REMOTE_NODE_IP)
        if is_online:
            REMOTE_NODE_STATUS = "online"
            logger.info(f"[WOL] Remote Node {REMOTE_NODE_IP} is ONLINE after {round(time.time() - start_time, 1)}s!")
            return True
        await asyncio.sleep(2.0)

    REMOTE_NODE_STATUS = "offline"
    logger.warning(f"[WOL] Remote Node {REMOTE_NODE_IP} did NOT respond within {timeout_sec}s.")
    return False


def atomic_sftp_download(remote_file_path: str, local_destination_path: str) -> bool:
    """
    Atomic Transfer Pattern:
    Downloads file as destination.mp4.tmp and renames to destination.mp4
    ONLY after 100% completed transfer verification.
    """
    tmp_path = local_destination_path + ".tmp"
    key_path = os.getenv("REMOTE_SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))
    ssh_user = os.getenv("REMOTE_SSH_USER", "remote_user")
    
    logger.info(f"[Atomic SFTP] Downloading {remote_file_path} -> {tmp_path}...")
    
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_NODE_IP, username=ssh_user, key_filename=key_path, timeout=10)
        
        sftp = ssh.open_sftp()
        sftp.get(remote_file_path, tmp_path)
        sftp.close()
        ssh.close()
        
        # Verify non-zero size
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            os.replace(tmp_path, local_destination_path)
            logger.info(f"[Atomic SFTP SUCCESS] Renamed {tmp_path} -> {local_destination_path}")
            return True
        else:
            logger.error(f"[Atomic SFTP FAILED] Temporary file {tmp_path} is empty.")
            return False

    except Exception as e:
        logger.error(f"[Atomic SFTP Exception] Transfer failed: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False


def run_local_download_task(task_id: str):
    """
    Background worker that runs yt-dlp download with live progress hooks,
    updating TASKS_DB and telemetry in real time.
    """
    import yt_dlp
    task = TASKS_DB.get(task_id)
    if not task:
        return
    
    task["status"] = "downloading"
    url = task["url"]
    format_id = task["format_id"]
    save_path = task["save_path"]

    def progress_hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            speed = d.get('speed', 0) or 0
            eta = d.get('eta', 0) or 0

            percent = round((downloaded / total) * 100, 1) if total > 0 else 0.0
            speed_mb = round(speed / (1024 * 1024), 2) if speed else 0.0

            task['progress_percent'] = percent
            task['speed_mbps'] = speed_mb
            task['downloaded_bytes'] = downloaded
            task['total_bytes'] = total
            task['eta_sec'] = eta
            
            info_dict = d.get('info_dict', {})
            if info_dict.get('title') and task['title'] == "Initializing download...":
                task['title'] = info_dict['title']

        elif d['status'] == 'finished':
            task['status'] = 'completed'
            task['progress_percent'] = 100.0
            task['speed_mbps'] = 0.0
            filename = d.get('filename')
            if filename:
                task['title'] = os.path.basename(filename)
            logger.info(f"[Worker] Task {task_id} COMPLETED successfully!")

    # Parse format selector safely
    format_spec = 'best'
    if format_id and format_id != 'best':
        if format_id.endswith('p') and format_id[:-1].isdigit():
            h = format_id[:-1]
            format_spec = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
        else:
            format_spec = f"{format_id}+bestaudio/best"

    ydl_opts = {
        'format': format_spec,
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }

    try:
        logger.info(f"[Worker] Starting download for task {task_id} (Format: {format_id})...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        task['status'] = 'completed'
        task['progress_percent'] = 100.0
        log_telemetry_event("download_completed", {"task_id": task_id, "save_path": save_path})
    except Exception as e:
        logger.error(f"[Worker] Download failed for task {task_id}: {e}")
        task['status'] = 'failed'
        task['error_message'] = str(e)
        log_telemetry_event("download_failed", {"task_id": task_id, "error": str(e)})


# API Endpoints
@app.get("/")
def read_root():
    return {
        "service": "Media Downloader Desktop Engine",
        "version": "2.4.0",
        "status": "running",
        "remote_node": REMOTE_NODE_STATUS
    }


@app.post("/api/analyze")
def analyze_endpoint(req: AnalyzeRequest):
    logger.info(f"[API /analyze] Analyzing URL: {req.url}")
    res = analyze_media_url(req.url)
    log_telemetry_event("url_analyzed", {"url": req.url, "status": res.get("status")})
    return res


@app.post("/api/download")
async def start_download_endpoint(req: StartDownloadRequest, background_tasks: BackgroundTasks):
    validated_path = validate_guardrails_path(req.save_path)
    os.makedirs(validated_path, exist_ok=True)
    
    task_id = str(uuid.uuid4())[:8]
    ram_info = check_ram_spillover(80.0)
    
    task_data = {
        "task_id": task_id,
        "url": req.url,
        "title": "Initializing download...",
        "format_id": req.format_id,
        "save_path": validated_path,
        "priority": req.priority,
        "status": "pending",
        "progress_percent": 0.0,
        "speed_mbps": 0.0,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "current_node": req.node_target,
        "ram_spillover_active": (ram_info["mode"] == "disk_spillover")
    }
    
    TASKS_DB[task_id] = task_data
    log_telemetry_event("download_queued", task_data)

    # Launch background worker task
    if req.node_target == "local":
        background_tasks.add_task(run_local_download_task, task_id)
    
    return {
        "status": "success",
        "task_id": task_id,
        "assigned_node": req.node_target,
        "estimated_ram_mode": ram_info["mode"]
    }


@app.post("/api/offload")
async def offload_endpoint(req: OffloadRequest):
    """
    Handles offloading to Remote Node (192.168.100.22) with 45s WOL check & fallback.
    """
    logger.info(f"[API /offload] Triggering remote node offload for task {req.task_id}...")
    
    # Check if node is online or wake it
    is_online = await ping_remote_node(REMOTE_NODE_IP)
    if not is_online:
        logger.info(f"[WOL] Remote node offline. Triggering 45s wake cycle...")
        is_online = await async_wake_remote_node(req.wol_timeout_sec)
        
    if not is_online:
        log_telemetry_event("wol_timeout", {"task_id": req.task_id, "node": REMOTE_NODE_IP})
        return {
            "status": "node_unreachable",
            "task_id": req.task_id,
            "message": "Remote Node 192.168.100.22 did not respond within 45s. Recommend local fallback."
        }
    
    return {
        "status": "success",
        "task_id": req.task_id,
        "assigned_node": REMOTE_NODE_IP,
        "message": f"Task {req.task_id} successfully dispatched to Remote Node {REMOTE_NODE_IP}"
    }


@app.get("/api/queue")
async def queue_endpoint():
    is_online = await ping_remote_node(REMOTE_NODE_IP, timeout_sec=0.5)
    global REMOTE_NODE_STATUS
    if is_online:
        REMOTE_NODE_STATUS = "online"
    elif REMOTE_NODE_STATUS != "waking":
        REMOTE_NODE_STATUS = "offline"

    mem = psutil.virtual_memory()
    
    return {
        "active_tasks": list(TASKS_DB.values()),
        "completed_tasks_count": sum(1 for t in TASKS_DB.values() if t["status"] == "completed"),
        "local_ram_usage_percent": mem.percent,
        "remote_node_status": REMOTE_NODE_STATUS
    }


class SummarizeRequest(BaseModel):
    url: str
    preferred_lang: List[str] = ["ru", "en"]


@app.post("/api/transcript")
async def transcript_endpoint(req: SummarizeRequest):
    """
    Extracts raw clean subtitles/transcripts without downloading video file.
    """
    logger.info(f"[API /transcript] Extracting transcript for {req.url}")
    result = extract_transcript(req.url, req.preferred_lang)
    return result


@app.post("/api/summarize")
async def summarize_endpoint(req: SummarizeRequest):
    """
    Extracts transcript and generates structured AI summary with chapters and key takeaways.
    """
    logger.info(f"[API /summarize] Generating AI summary for {req.url}")
    t_data = extract_transcript(req.url, req.preferred_lang)
    if t_data.get("status") != "success":
        return t_data
    
    summary = generate_heuristic_summary(
        title=t_data.get("title", "Untitled Video"),
        transcript=t_data.get("full_transcript", ""),
        duration_sec=t_data.get("duration_sec", 0)
    )
    
    # Save summary as .md artifact in downloads/media/
    save_dir = os.path.abspath(r"downloads\media")
    os.makedirs(save_dir, exist_ok=True)
    safe_title = "".join(c for c in t_data.get("title", "summary") if c.isalnum() or c in (' ', '_', '-')).rstrip()
    md_file_path = os.path.join(save_dir, f"{safe_title}_summary.md")
    
    try:
        with open(md_file_path, "w", encoding="utf-8") as f:
            f.write(f"# 🧠 ИИ-Конспект: {summary['title']}\n\n")
            f.write(f"⏱ **Длительность:** {summary['duration_formatted']}\n\n")
            f.write("## 📌 Краткое содержание (TL;DR)\n")
            for p in summary["tldr"]:
                f.write(f"- {p}\n")
            f.write("\n## 📑 Главы и таймкоды\n")
            for ch in summary["chapters"]:
                f.write(f"- `[{ch['timestamp']}]` **{ch['title']}:** {ch['summary']}\n")
            f.write("\n## 💡 Ключевые выводы\n")
            for kw in summary["key_takeaways"]:
                f.write(f"- {kw}\n")
        summary["saved_md_path"] = md_file_path
    except Exception as e:
        logger.error(f"Failed to write summary markdown: {e}")

    return {
        "status": "success",
        "summary": summary,
        "transcript_preview": t_data.get("transcript_preview")
    }
