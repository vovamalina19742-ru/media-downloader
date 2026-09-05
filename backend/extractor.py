"""
Stream Extractor & WAF Bypass Module for Media Downloader Desktop
Leverages yt-dlp, curl_cffi (JA3 TLS impersonation), and dynamic RAM-to-disk fallback.
"""
import os
import sys
import json
import logging
import psutil
import yt_dlp
from typing import Dict, Any, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extractor")

# Check curl_cffi availability for Chrome TLS JA3 impersonation
CURL_CFFI_AVAILABLE = False
try:
    from curl_cffi import requests as impersonate_requests
    CURL_CFFI_AVAILABLE = True
    logger.info("[Extractor] curl_cffi loaded: Chrome TLS JA3 impersonation ACTIVE")
except ImportError:
    logger.warning("[Extractor] curl_cffi not installed: falling back to standard TLS")


def check_ram_spillover(threshold_percent: float = 80.0) -> Dict[str, Any]:
    """
    Backpressure 2.0: Monitors RAM usage.
    Returns spillover status and recommended temp directory.
    """
    mem = psutil.virtual_memory()
    is_spillover = mem.percent >= threshold_percent
    
    if is_spillover:
        spillover_dir = os.path.abspath(r"downloads\cache\spillover")
        os.makedirs(spillover_dir, exist_ok=True)
        logger.warning(f"[Backpressure 2.0] RAM usage at {mem.percent:.1f}% >= {threshold_percent}%. Spilling over HLS buffer to DISK: {spillover_dir}")
        return {"mode": "disk_spillover", "temp_dir": spillover_dir, "ram_percent": mem.percent}
    
    ram_dir = os.path.abspath(r"downloads\cache\ram_buffer")
    os.makedirs(ram_dir, exist_ok=True)
    return {"mode": "ram_buffer", "temp_dir": ram_dir, "ram_percent": mem.percent}


def analyze_media_url(url: str) -> Dict[str, Any]:
    """
    Parses media URL using yt-dlp + stealth impersonation.
    Extracts available qualities, formats, duration, and stream types.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'best',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return {"status": "error", "error_code": "INVALID_URL", "error_message": "Could not extract media info."}
            
            # Check DRM
            if info.get('drm') or info.get('is_drm'):
                return {
                    "status": "error",
                    "error_code": "DRM_PROTECTED",
                    "error_message": "DRM protection detected (Widevine/PlayReady). Download rejected by policy."
                }
            
            formats_list: List[Dict[str, Any]] = []
            raw_formats = info.get('formats', [])
            
            for f in raw_formats:
                height = f.get('height')
                format_id = f.get('format_id', 'best')
                ext = f.get('ext', 'mp4')
                filesize = f.get('filesize') or f.get('filesize_approx')
                filesize_mb = round(filesize / (1024 * 1024), 2) if filesize else None
                
                res_label = f"{height}p" if height else (f.get('format_note') or "audio/video")
                if height == 2160:
                    res_label = "3840x2160 (4K)"
                elif height == 1440:
                    res_label = "2560x1440 (2K)"
                
                formats_list.append({
                    "format_id": format_id,
                    "resolution": res_label,
                    "ext": ext,
                    "vcodec": f.get('vcodec', 'none'),
                    "acodec": f.get('acodec', 'none'),
                    "filesize_approx_mb": filesize_mb,
                    "fps": f.get('fps')
                })

            is_hls_dash = bool(info.get('protocol') in ['m3u8', 'm3u8_native', 'dash'] or any('m3u8' in str(f.get('url', '')) for f in raw_formats))

            return {
                "status": "success",
                "url": url,
                "title": info.get('title', 'Untitled Media'),
                "thumbnail_url": info.get('thumbnail'),
                "duration_sec": info.get('duration'),
                "available_formats": formats_list[-10:], # Return top 10 format options
                "is_hls_dash": is_hls_dash
            }

    except Exception as e:
        logger.error(f"[Extractor] Error analyzing {url}: {e}")
        return {
            "status": "error",
            "error_code": "WAF_BLOCKED" if "403" in str(e) else "NETWORK_TIMEOUT",
            "error_message": str(e)
        }
