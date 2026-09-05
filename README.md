# ⚡ Media Downloader Desktop (v2.4)

> **High-Performance Multi-Threaded Video & Stream Harvester with Adaptive Backpressure & Hardware Offloading.**
> *Built with FastAPI (Python) + React (TypeScript/Tailwind CSS) + Rust-First Architecture.*

---

## 🚀 Key Features

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
