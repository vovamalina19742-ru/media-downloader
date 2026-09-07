# 🗺️ Semantic Code Graph (Graft AST Map): media-downloader
**Stack:** FastAPI + yt-dlp + React/TS + Rust/Tauri Architecture
**Generated:** Auto-synced for Zero-Cost AI Agent Navigation

## ⚡ Core Pipeline Flows (Архитектурные цепочки вызовов)
```mermaid
graph LR
    frontend_index_html["frontend/index.html"] -->|REST / WebSocket IPC calls| backend_app_py["backend/app.py"]
    backend_app_py["backend/app.py"] -->|media metadata extraction| backend_extractor_py["backend/extractor.py"]
    backend_app_py["backend/app.py"] -->|transcript & LangExtract grounding| backend_summarizer_py["backend/summarizer.py"]
    backend_app_py["backend/app.py"] -->|DPI network stream interception| backend_sniffer_py["backend/sniffer.py"]
```

## 📦 Индексированные Модули и Узлы (Nodes)
| Файл / Модуль | Тип | Ключевые методы / Эндпоинты |
| :--- | :--- | :--- |
| `backend/app.py` | Backend Engine | GET /, POST /api/analyze, POST /api/download, POST /api/offload |
| `backend/extractor.py` | Backend Engine | - |
| `backend/sniffer.py` | Backend Engine | - |
| `backend/summarizer.py` | Backend Engine | - |
| `frontend/postcss.config.js` | Frontend Component | - |
| `frontend/tailwind.config.js` | Frontend Component | - |
| `frontend/vite.config.ts` | Frontend Component | - |
| `frontend/src/App.tsx` | Frontend Component | - |
| `frontend/src/main.tsx` | Frontend Component | - |
| `frontend/src/types/ipc.ts` | Frontend Component | - |
