#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cdn_edge_discovery.py — Media Downloader Phase 0 CDN Mirror & Edge Node Discovery
"""

import os
import sys
import json
from typing import Dict, Any, List

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from subdomain_recon import SubdomainRecon
except ImportError:
    from subdomain_recon import SubdomainRecon


def discover_fastest_cdn_mirrors(service_domain: str, max_threads: int = 15) -> Dict[str, Any]:
    """
    Discovers all CDN edge nodes and ranks them by network latency for multi-threaded media acceleration.
    """
    recon = SubdomainRecon(max_threads=max_threads)
    result = recon.scan(service_domain, probe_live=True)

    cdn_nodes = [
        r for r in result.records 
        if (r.category == "media_cdn" or any(kw in r.subdomain for kw in ["cdn", "edge", "stream", "video"])) and r.is_live
    ]

    # Sort by response time (fastest first)
    cdn_nodes.sort(key=lambda x: x.response_time_ms if x.response_time_ms is not None else 9999)

    return {
        "domain": service_domain,
        "total_cdn_mirrors_found": len(cdn_nodes),
        "fastest_mirror": cdn_nodes[0].subdomain if cdn_nodes else None,
        "mirrors": [
            {
                "subdomain": node.subdomain,
                "ip_addresses": node.ip_addresses,
                "latency_ms": node.response_time_ms,
                "http_status": node.http_status
            }
            for node in cdn_nodes
        ]
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_domain = sys.argv[1]
        res = discover_fastest_cdn_mirrors(target_domain)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("Usage: python cdn_edge_discovery.py <streaming_service.com>")
