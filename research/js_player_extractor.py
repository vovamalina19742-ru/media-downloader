#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
js_player_extractor.py — Phase 0 (Spike) Web Player AST Stream Extractor
Extracts .m3u8, .mpd, CDN endpoints, and DRM license URLs from obfuscated player bundles.
"""

import os
import sys
import json
from typing import Dict, Any

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from js_ast_analyzer import JsAstAnalyzer
except ImportError:
    from js_ast_analyzer import JsAstAnalyzer


def extract_player_streams(bundle_content: str, source_name: str = "player.js") -> Dict[str, Any]:
    """
    Extracts all stream manifests and CDN endpoints for Phase 0 Spike validation.
    """
    analyzer = JsAstAnalyzer()
    result = analyzer.analyze_source(bundle_content, filename=source_name)

    return {
        "source": source_name,
        "media_streams": [
            {
                "url": stream.url,
                "type": stream.endpoint_type,
                "source_type": stream.source_type,
                "line": stream.line_number
            }
            for stream in result.media_streams
        ],
        "all_endpoints_count": len(result.endpoints),
        "streams_count": len(result.media_streams)
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        res = extract_player_streams(code, os.path.basename(target_path))
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("Usage: python js_player_extractor.py <path_to_player_bundle.js>")
