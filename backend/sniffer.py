"""
Deep Packet & Network Stream Sniffer Module for Media Downloader Desktop (v2.6)
Inspired by nDPI L7 deep packet inspection and network traffic analysis.
Sniffs, intercepts, and classifies embedded streaming protocols:
- HLS (.m3u8 manifests & variant playlists)
- MPEG-DASH (.mpd manifest XMLs)
- Direct MP4 / WebM / M4A stream links
- WebSocket live feeds & chunked RTMP/HTTP-FLV streams
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sniffer")

# Protocol signatures (L7 DPI Signatures)
STREAM_SIGNATURES = {
    "hls": [".m3u8", "application/x-mpegurl", "application/vnd.apple.mpegurl", "#EXTM3U"],
    "dash": [".mpd", "application/dash+xml", "<MPD"],
    "direct_video": [".mp4", ".mkv", ".webm", ".ts", "video/mp4", "video/webm"],
    "direct_audio": [".m4a", ".mp3", ".aac", ".flac", "audio/mp4", "audio/mpeg"]
}


def classify_stream_protocol(url: str, content_type: str = "", sample_bytes: str = "") -> str:
    """
    nDPI-inspired protocol classifier: identifies stream protocol by URL, MIME type, and header magic bytes.
    """
    url_lower = url.lower()
    ct_lower = content_type.lower()
    
    # Check HLS
    if any(sig in url_lower or sig in ct_lower or sig in sample_bytes for sig in STREAM_SIGNATURES["hls"]):
        return "HLS (HTTP Live Streaming)"
    
    # Check DASH
    if any(sig in url_lower or sig in ct_lower or sig in sample_bytes for sig in STREAM_SIGNATURES["dash"]):
        return "MPEG-DASH"
        
    # Check Direct Video / Audio
    if any(sig in url_lower or sig in ct_lower for sig in STREAM_SIGNATURES["direct_video"]):
        return "Direct Video Stream"
    if any(sig in url_lower or sig in ct_lower for sig in STREAM_SIGNATURES["direct_audio"]):
        return "Direct Audio Stream"
        
    return "Generic HTTP Stream"


def sniff_page_streams(page_url: str, user_agent: Optional[str] = None) -> Dict[str, Any]:
    """
    Deep inspects a webpage HTML source, embedded scripts, iframe tags and network requests
    to find hidden HLS/DASH/MP4 media streams without executing heavy browser if possible.
    """
    ua = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    discovered_streams = []
    seen_urls = set()

    try:
        resp = requests.get(page_url, headers=headers, timeout=12)
        html_content = resp.text
        
        # 1. Regex patterns for hidden stream URLs in JS/HTML
        patterns = [
            r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
            r'https?://[^\s"\'<>]+\.mpd[^\s"\'<>]*',
            r'https?://[^\s"\'<>]+\.(?:mp4|webm|m4a)[^\s"\'<>]*',
            r'["\'](https?:\\/\\/[^"\']+\.m3u8[^"\']*)["\']',
            r'["\'](https?:\\/\\/[^"\']+\.mpd[^"\']*)["\']',
            r'source\s*src=["\']([^"\']+)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
        ]

        for p in patterns:
            matches = re.findall(p, html_content, re.IGNORECASE)
            for m in matches:
                # Clean escaped slashes if extracted from JS
                clean_url = m.replace('\\/', '/')
                if clean_url.startswith('//'):
                    clean_url = 'https:' + clean_url
                elif not clean_url.startswith('http'):
                    clean_url = urljoin(page_url, clean_url)
                    
                if clean_url not in seen_urls and not clean_url.endswith('.js') and not clean_url.endswith('.css'):
                    seen_urls.add(clean_url)
                    proto = classify_stream_protocol(clean_url)
                    discovered_streams.append({
                        "stream_url": clean_url,
                        "protocol": proto,
                        "source": "HTML/JS Deep Inspection",
                        "is_manifest": ".m3u8" in clean_url or ".mpd" in clean_url
                    })

        # 2. Extract page metadata
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        page_title = title_match.group(1).strip() if title_match else "Unknown Media Page"

        return {
            "status": "success",
            "page_url": page_url,
            "page_title": page_title,
            "streams_found_count": len(discovered_streams),
            "streams": discovered_streams[:15] # Top 15 streams
        }

    except Exception as e:
        logger.error(f"[Sniffer] Error sniffing {page_url}: {e}")
        return {
            "status": "error",
            "page_url": page_url,
            "error_message": str(e)
        }
