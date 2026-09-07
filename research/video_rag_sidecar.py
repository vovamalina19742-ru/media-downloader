#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video_rag_sidecar.py — Media-Downloader Local Video RAG Sidecar
Performs zero-cloud semantic search over video stream transcripts and generates fast FFmpeg slice downloads.
"""

import os
import sys
import json
from typing import Dict, Any, List

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from video_rag_indexer import VideoRagEngine
except ImportError:
    from video_rag_indexer import VideoRagEngine


def query_video_moments(video_id: str, title: str, source_url: str, subtitles: List[Dict[str, Any]], query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Finds exact timestamp ranges for a given query and returns FFmpeg slice commands.
    """
    engine = VideoRagEngine()
    index = engine.build_index_from_transcript(video_id, title, source_url, subtitles)
    matches = engine.search(index, query, top_k=top_k)

    return {
        "video_id": video_id,
        "title": title,
        "query": query,
        "duration_sec": index.duration_sec,
        "matches_count": len(matches),
        "results": [
            {
                "chunk_id": m.chunk.chunk_id,
                "similarity_score": m.similarity_score,
                "timestamp": m.chunk.timestamp_display,
                "start_sec": m.chunk.start_time_sec,
                "end_sec": m.chunk.end_time_sec,
                "text": m.chunk.transcript_text,
                "visual": m.chunk.visual_description,
                "ffmpeg_slice_cmd": m.ffmpeg_slice_cmd
            }
            for m in matches
        ]
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_text = sys.argv[1]
        # Demo sample
        sample_subs = [
            {"start": 120.0, "end": 185.0, "text": "Вводный обзор безопасности."},
            {"start": 1240.0, "end": 1315.0, "text": "Уязвимость нулевого дня zero-day в ядре Linux через eBPF."},
            {"start": 2540.0, "end": 2620.0, "text": "Бенчмарк производительности Rust vs C++ в сетевом ядре."}
        ]
        res = query_video_moments("demo", "Demo Video", "https://stream.host/video.m3u8", sample_subs, query_text)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("Usage: python video_rag_sidecar.py \"поисковый запрос\"")
