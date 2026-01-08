<div align="center">
  <a href="https://github.com/saim-honey388/smart-rfp-system">
    <img src="docs/images/logo-placeholder.png" alt="Logo" width="120" height="120">
  </a>

  <h1 align="center">Smart RFP System</h1>

  <p align="center">
    <strong>AI-Powered Procurement & Proposal Management</strong>
    <br />
    <br />
    <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" /></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" /></a>
    <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
    <a href="https://tailwindcss.com/"><img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind" /></a>
    <br />
    <br />
    <a href="#-demo"><strong>Explore the Demo »</strong></a>
    ·
    <a href="WORKFLOW.md"><strong>Read Docs »</strong></a>
    ·
    <a href="#-feedback"><strong>Report Bug »</strong></a>
  </p>
</div>

<br />

> [!NOTE]
> **Mission Statement**: To transform manual, error-prone procurement processes into instant, data-driven decisions using state-of-the-art AI.

<div align="center">
  <img src="docs/images/dashboard-hero.png" alt="Dashboard Preview" width="100%" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
</div>

---

## ⚡ Why Smart RFP?

Procurement teams are drowning in PDFs. **Smart RFP** parses them for you.

*   🤖 **Zero Data Entry**: Drag, drop, and let AI extract costs, timelines, and credentials.
*   ⚖️ **True Comparisons**: Don't just compare prices. Compare *value* against your unique requirements.
*   📊 **Visual Insights**: See the winners clearly with radar charts and dynamic scoring tables.

---

## 🎨 Key Features

| Feature | Description |
| :--- | :--- |
| **📄 PDF Extraction** | Instantly parse messy vendor proposals into structured JSON. |
| **🧠 Intelligent Scoring** | Vendors are graded (0-100) on custom dimensions like *Security* or *Sustainability*. |
| **📈 Dynamic Reports** | Generate beautiful Radar & Bar charts to visualize the "Best Fit" vendor. |
| **🚀 Real-Time Dashboard** | Track all your open RFPs, active bids, and draft projects in one place. |
| **🔒 Role-Based Access** | Secure environment for sensitive procurement data. |

---

## 🛠️ The Stack

Built with performance and scalability in mind.

### **Frontend**
![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)
![ApexCharts](https://img.shields.io/badge/ApexCharts-FF4560?style=flat-square&logo=apexcharts&logoColor=white)

### **Backend**
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![AI Models](https://img.shields.io/badge/AI_Models-FF6F00?style=flat-square&logo=openai&logoColor=white)

---

## 🚀 Quick Start

Get up and running in minutes. See [WORKFLOW.md](WORKFLOW.md) for the full tour.

### 1. Backend (Python)
```bash
pip install -r requirements.txt
python -m apps.api.main
```

### 2. Frontend (React)
```bash
cd apps/client
npm install
npm run dev
```

### 3. Environment Setup (Required)
Create a `.env` file in the project root with the following configuration:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# AI Model Configuration (defaults shown)
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Optional: Fallback to Groq if OpenAI unavailable
GROQ_API_KEY=your-groq-api-key  # Optional fallback
USE_FALLBACK_PROVIDER=false     # Set to 'true' to force fallback
```

> [!IMPORTANT]
> The system uses **OpenAI GPT-4o** for AI extraction and **text-embedding-3-large** for document embeddings. You must provide a valid `OPENAI_API_KEY` for the system to function.

---

## 📸 Gallery

<div align="center">

| | |
|:-------------------------:|:-------------------------:|
| <img width="1604" alt="Create RFP" src="docs/images/create-rfp.png"> <br /> **Smart RFP Creation** | <img width="1604" alt="Analysis" src="docs/images/proposal-analysis.png"> <br /> **AI Proposal Analysis** |
| <img width="1604" alt="Comparison" src="docs/images/comparison.png"> <br /> **Side-by-Side Review** | <img width="1604" alt="Charts" src="docs/images/radar-chart.png"> <br /> **Decision Charts** |

</div>

---

## 📞 Contact

**Saim Khalid**
*   Email: [saim.khalid983@gmail.com](mailto:saim.khalid983@gmail.com)
*   GitHub: [saim-honey388](https://github.com/saim-honey388)

---
