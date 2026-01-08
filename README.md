<div align="center">

# 🚀 Smart RFP System

### AI-Powered Procurement & Proposal Management Platform

[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)

[**Documentation**](WORKFLOW.md) · [**Architecture**](docs/system-architecture.md)

---

[![Watch Demo](docs/images/ezgif.com-animated-gif-maker.gif)](https://drive.google.com/file/d/1p7Qom6bnGoPnj_k_okydY2Aqj_r7k1W0/view?usp=sharing)

*👆 Click to watch full demo*

</div>

---

## 📋 Overview

**Smart RFP System** transforms manual, error-prone procurement processes into instant, data-driven decisions using state-of-the-art AI. Upload vendor proposal PDFs and let AI automatically extract, compare, and visualize contractor data—no manual data entry required.

```mermaid
flowchart TB
    subgraph INPUT["1. Upload"]
        RFP[RFP PDF] --> PROPS[Vendor Proposals]
    end

    subgraph PROCESS["2. AI Processing"]
        PROPS --> EXTRACT[Extract & Embed]
        EXTRACT --> CHROMA[(ChromaDB)]
        CHROMA --> DB[(SQLite)]
    end

    subgraph OUTPUT["3. Results"]
        DB --> COMPARE[Comparison Matrix]
        DB --> REPORT[Comparison Report]
        DB --> CHAT[AI Chat]
    end
```

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **📄 AI PDF Extraction** | Automatically extract contractor details, pricing, timelines, experience, materials, warranties, and line-item breakdowns from proposal PDFs |
| **📋 Dynamic Form Discovery** | AI discovers RFP proposal form structure and extracts matching data from each vendor for apples-to-apples comparison |
| **💬 Proposal Chat Assistant** | Ask natural language questions about any proposal with full context of vendor data and RFP requirements |
| **⚖️ Comparison Matrix** | Side-by-side vendor comparison with automatic column classification and grand total calculations |
| **📊 Visual Analytics** | Radar charts, bar charts, and scoring tables to visualize the "Best Fit" vendor across multiple dimensions |
| **🎯 RFP Lifecycle Dashboard** | Track Open RFPs, Drafts, Saved Comparisons, and recent activity in one unified interface |

---

## 🛠️ Tech Stack

### Frontend
![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)
![ApexCharts](https://img.shields.io/badge/ApexCharts-FF4560?style=flat-square)

### Backend
![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F00?style=flat-square)

### AI Models
| Component | Model | Purpose |
|-----------|-------|---------|
| **Chat & Extraction** | `gpt-4o` | Structured data extraction, proposal chat |
| **Embeddings** | `text-embedding-3-large` | Document vectorization (3072 dimensions) |
| **Fallback** | Groq (optional) | Backup if OpenAI unavailable |

---

## 🚀 Quick Start

### Prerequisites
- **Node.js** v18+
- **Python** v3.10+
- **OpenAI API Key** (required)

### 1. Clone & Setup Backend

```bash
# Clone the repository
git clone https://github.com/saim-honey388/smart-rfp-system.git
cd smart-rfp-system

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Setup Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=sqlite:///./rfp.db
STORAGE_PATH=storage

# Required: OpenAI
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Optional: Fallback
GROQ_API_KEY=gsk-your-groq-key
USE_FALLBACK_PROVIDER=false
```

> [!IMPORTANT]
> A valid `OPENAI_API_KEY` is required for AI extraction and chat features.

### 4. Access the Application

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:5173 |
| **API Docs** | http://localhost:8000/docs |

---

## �️ Architecture

```
/RFP System
├── backend/                    # Python/FastAPI backend
│   ├── main.py                 # Application entrypoint
│   ├── routers/                # API route handlers
│   ├── services/               # Business logic layer
│   │   ├── ingest/             # PDF extraction services
│   │   └── review/             # AI review & scoring
│   └── src/agents/             # AI agent components
├── frontend/                   # React + Vite frontend
│   ├── src/components/         # React components
│   └── src/pages/              # Page components
├── data/chromadb/              # Vector database for embeddings
└── storage/proposals/          # Uploaded proposal PDFs
```

> For complete architecture details, see [`docs/system-architecture.md`](docs/system-architecture.md)

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/rfps` | List all RFPs |
| `POST` | `/api/rfps` | Create new RFP |
| `POST` | `/api/rfps/upload` | Upload RFP PDF |
| `POST` | `/api/proposals/upload` | Upload proposal PDF |
| `POST` | `/api/proposals/{id}/approve` | Approve proposal |
| `POST` | `/api/proposals/{id}/reject` | Reject proposal |
| `GET` | `/api/proposals/{rfp_id}/matrix` | Get comparison matrix |
| `POST` | `/api/chat/proposal` | Chat about a proposal |

> Full API documentation available at `http://localhost:8000/docs` when running locally.

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [**WORKFLOW.md**](WORKFLOW.md) | Complete user journey and demo walkthrough |
| [**System Architecture**](docs/system-architecture.md) | Technical architecture, data models, and API endpoints |

---

## 📞 Contact

**Saim Khalid** – [saim.khalid983@gmail.com](mailto:saim.khalid983@gmail.com)

[![GitHub](https://img.shields.io/badge/GitHub-saim--honey388-181717?style=flat-square&logo=github)](https://github.com/saim-honey388)

---

<div align="center">

*Streamlining procurement decisions with intelligent automation*

</div>
