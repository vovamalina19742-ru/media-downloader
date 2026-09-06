# ⚡ Media Downloader Desktop (v2.6)

> **High-Performance Multi-Threaded Video & Stream Harvester with Zero-Cost AI Summarizer & DPI Network Stream Sniffer.**
> *Built with FastAPI (Python) + React (TypeScript/Tailwind CSS) + Rust-First Architecture.*

---

## 🚀 Key Features

* **🔍 DPI Network Stream Sniffer (nDPI Inspired):** Deep inspects complex web pages, embedded players, and scripts to intercept hidden `.m3u8` (HLS), `.mpd` (MPEG-DASH), and direct MP4 streams without running heavy browser automation.
* **🧠 Zero-Cost AI Summarizer & Transcript Extractor:** Lightning-fast subtitle extraction (YouTube VTT/JSON3/SRT) without downloading full video files. Generates structured TL;DR summaries, interactive clickable timestamps, and one-click Markdown export (`Copy MD` / `*_summary.md`) for Obsidian, Notion, and Telegram.
* **🏎️ Adaptive Backpressure 2.0:** Real-time RAM & disk monitoring with automatic buffer-to-disk spillover prevention.
* **🌐 HLS (.m3u8) / DASH (.mpd) Harvester:** Fast multi-threaded chunk downloading with atomic stream reassembly.
* **🛡️ Security Guardrails:** Strict Path Traversal validation (`canonicalize`), 0 telemetry leaks, and non-destructive operations.
* **⚡ Hardware Node Offloading:** Wake-on-LAN remote worker integration for heavy 24/7 queue processing via Atomic SFTP.
* **🔒 100% Privacy:** No ads, no cloud telemetry, open-source.

---

## 🛠️ Installation & Setup

### 1. Backend (Python 3.11+)
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend (Node.js 18+)
```bash
cd frontend
npm install
npm run dev
```

---

## 📜 License
MIT License. Open Source & Privacy-First.
