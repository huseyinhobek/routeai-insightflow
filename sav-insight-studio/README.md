# 🔮 SAV Insight Studio

<div align="center">

![SAV Insight Studio](https://img.shields.io/badge/SAV%20Insight-Studio-8B5CF6?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0ibTEyIDMtMS45MTIgNS44MTNhMiAyIDAgMCAxLTEuMjc1IDEuMjc1TDMgMTJsNS44MTMgMS45MTJhMiAyIDAgMCAxIDEuMjc1IDEuMjc1TDEyIDIxbDEuOTEyLTUuODEzYTIgMiAwIDAgMSAxLjI3NS0xLjI3NUwyMSAxMmwtNS44MTMtMS45MTJhMiAyIDAgMCAxLTEuMjc1LTEuMjc1TDEyIDN6Ii8+PC9zdmc+)
![Version](https://img.shields.io/badge/version-2.0.0-blue?style=for-the-badge)
![License](https://img.shields.io/badge/license-Private-red?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**Enterprise-grade SPSS data analysis platform with AI-powered insights**

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [API Reference](#-api-reference)

</div>

---

## 🧪 Research Workflow

The platform includes a comprehensive Research Workflow system with structured and RAG-based question answering:

- **Structured Mode**: Deterministic SQL aggregation for direct survey questions
- **RAG Mode**: Semantic retrieval over utterances for questions not directly in survey
- **Evidence Contract**: Every answer includes evidence JSON with provenance
- **Guardrails**: Number validation, quantifier policy, template compliance
- **Dataset Versioning**: Thread results remain consistent across dataset updates
- **Audience Membership**: Atomic swap versioning for scalable segmentation
- **Mapping Debug JSON**: Transparent variable mapping rationale

See [Research Workflow Documentation](#research-workflow) for details.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 📊 Data Analysis
- **SAV File Parsing** - Full SPSS (.sav) format support
- **Variable Explorer** - Detailed frequency & statistics
- **Multi-format Export** - Excel, JSON, CSV, Reports

### 🎯 Quality Assessment
- **Completeness Score** - Missing data analysis
- **Validity Score** - Data type & range validation
- **Consistency Score** - Cross-variable checks

</td>
<td width="50%">

### 🤖 AI-Powered Features
- **Smart Filters** - AI-suggested segmentation filters
- **Digital Twin** - Transform survey data to AI-ready format
- **Auto-Detection** - Intelligent variable classification

### 🔄 Twin Transformer
- **Row-by-row processing** - Real-time transformation
- **Pause & Resume** - Control your transformation jobs
- **CSV Export** - Export with smart filter columns

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| 🐳 Docker | 20.0+ |
| 🐘 PostgreSQL | 14+ |
| 🔑 OpenAI API Key | GPT-4/GPT-5 access |

### One-Command Deploy

```bash
# Clone and start
git clone https://github.com/huseyinhobek/sav-insight-studio.git
cd sav-insight-studio
docker-compose up -d --build
```

🌐 Access at: `http://localhost:3000`

---

## 📦 Installation

### Docker Compose (Recommended)

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: sav-insight-backend
    ports:
      - "8002:8000"
    volumes:
      - ./backend:/app
      - sav_uploads:/tmp/sav_uploads
    env_file:
      - ./backend/.env
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/sav_insight
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: sav-insight-frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  sav_uploads:
```

### Environment Configuration

Create `backend/.env`:

```env
# 🗄️ Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/sav_insight

# 🤖 AI Configuration
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# 📁 Storage
UPLOAD_DIR=./uploads

# 🔧 Debug
DEBUG=false
```

---

## 🎨 Application Pages

<table>
<tr>
<td align="center" width="25%">
<h3>📤 Upload</h3>
<p>Drag & drop SAV files with instant validation</p>
</td>
<td align="center" width="25%">
<h3>📊 Overview</h3>
<p>Dataset summary with key metrics</p>
</td>
<td align="center" width="25%">
<h3>📈 Quality Report</h3>
<p>Comprehensive data quality assessment</p>
</td>
<td align="center" width="25%">
<h3>🔍 Variable Explorer</h3>
<p>Deep-dive into each variable</p>
</td>
</tr>
<tr>
<td align="center" width="25%">
<h3>🎯 Smart Filters</h3>
<p>AI-powered segmentation suggestions</p>
</td>
<td align="center" width="25%">
<h3>🔄 Twin Transformer</h3>
<p>Convert to digital twin format</p>
</td>
<td align="center" width="25%">
<h3>📥 Export</h3>
<p>Multiple export formats</p>
</td>
<td align="center" width="25%">
<h3>🕐 History</h3>
<p>Previous analyses & sessions</p>
</td>
</tr>
</table>

---

## 🎯 Smart Filters

The Smart Filter Studio uses AI to suggest optimal segmentation filters for your survey data.

### Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Suggestions** | GPT-powered filter recommendations |
| ✋ **Manual Filters** | Add custom filters by variable |
| ✅ **Multi-Select** | Select multiple variables at once |
| 🏷️ **AI Detection** | Badge shows if variable is AI-suggested |
| 🔄 **Apply/Unapply** | Toggle filters on/off |
| ❌ **Remove** | Delete filters with X button |

### CSV Export with Smart Filters

Smart filters are automatically added to CSV exports with `_sf` suffix:

```csv
product_id,product_name,review_content,age_group_sf,gender_sf,region_sf
PROD-001,Survey 2024,"I am 45 years old...",Males 45-54,Male,Northeast
```

---

## 🔄 Twin Transformer

Transform survey response data into AI-ready digital twin format.

### Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Dataset   │ -> │  Analysis   │ -> │  Settings   │ -> │   Output    │
│   Select    │    │   Review    │    │  Configure  │    │   Export    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Features

- ⚡ **Real-time Processing** - Watch transformations happen live
- ⏸️ **Pause/Resume** - Control long-running jobs
- 🔁 **Retry Failed** - Retry individual rows
- 📊 **Progress Tracking** - Detailed statistics
- 💾 **Auto-Save** - Checkpointing for reliability

---

## 📡 API Reference

### Datasets

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/datasets/upload` | Upload SAV file |
| `GET` | `/api/datasets` | List all datasets |
| `GET` | `/api/datasets/{id}` | Get dataset metadata |
| `DELETE` | `/api/datasets/{id}` | Delete dataset |
| `GET` | `/api/datasets/{id}/quality` | Get quality report |
| `GET` | `/api/datasets/{id}/variables/{var}` | Get variable details |
| `GET` | `/api/datasets/{id}/rows` | Get dataset rows (paginated) |

### Smart Filters

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/smart-filters/generate` | Generate AI filter suggestions |

### Transform

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/transform/analyze-columns` | Analyze columns for transformation |
| `POST` | `/api/transform/start` | Start transformation job |
| `GET` | `/api/transform/status/{job_id}` | Get job status |
| `POST` | `/api/transform/pause/{job_id}` | Pause job |
| `POST` | `/api/transform/resume/{job_id}` | Resume job |
| `GET` | `/api/transform/results/{job_id}` | Get transformation results |
| `POST` | `/api/transform/export/{job_id}` | Export results (JSON/CSV) |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Configuration status |

---

## 🧪 Research Workflow

### Structured vs RAG Mode

The system uses two modes for answering questions:

- **Structured Mode (Mode A)**: For questions directly answerable from survey variables. Uses deterministic SQL aggregation to compute counts, percentages, and statistics. The LLM only narrates the evidence provided.

- **RAG Mode (Mode B)**: For questions not directly in the survey structure. Uses semantic retrieval over utterances (respondent-level natural language sentences) to find relevant quotes and themes.

### Evidence Contract

Every answer includes:
- **Evidence JSON**: Base sample size (base_n), answered count (answered_n), response rate, missing count, categories with counts/percentages, or retrieved citations
- **Provenance**: Variable codes, respondent IDs, question texts
- **Mapping Debug JSON**: Variable mapping rationale, candidate scores, chosen variable, reason for mode selection

### Guardrails

The system includes strict guardrails to prevent hallucinations:
- **Number Validation**: All numbers mentioned in narratives must exist in evidence JSON
- **Quantifier Policy**: Phrases like "majority" (>50%), "overwhelming majority" (>75%), "nearly all" (>90%) are validated against evidence percentages
- **Template Compliance**: LLM output uses restricted JSON templates, not free-form text
- **Quote Validation**: In RAG mode, all quotes must exist in citations with respondent IDs

### Dataset Versioning

Dataset versions increment on upload/merge. Thread results store the dataset version they were created with, ensuring consistency even when datasets are updated. Cache keys include dataset version for automatic invalidation.

### Audience Membership Materialization

Audiences use an atomic swap versioning system for membership:
- Membership is stored in `audience_members` table with version numbers
- Active version is tracked in `audience.active_membership_version`
- Queries JOIN with active version for fast, scalable filtering (avoids expensive IN subqueries)
- New versions are created atomically, old versions cleaned up asynchronously

### Mapping Debug JSON

Each thread result includes `mapping_debug_json` with:
- Candidate variables with scores (semantic, lexical, value label coverage, question family heuristics)
- Chosen variable and rationale
- Threshold used (varies by variable type: demographic 0.80, single-choice 0.75, etc.)
- Mode selection reason

---

## 🗂️ Project Structure

```
sav-insight-studio/
├── 🐍 backend/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   ├── database.py             # PostgreSQL connection
│   ├── models.py               # SQLAlchemy models
│   ├── requirements.txt        # Python dependencies
│   └── services/
│       ├── quality_analyzer.py # Data quality analysis
│       ├── export_service.py   # Export functionality
│       ├── transform_service.py # Twin transformation
│       ├── smart_filter_service.py # AI filter generation
│       └── openai_service.py   # OpenAI integration
│
├── ⚛️ pages/
│   ├── UploadPage.tsx          # File upload
│   ├── DatasetOverview.tsx     # Overview dashboard
│   ├── QualityReport.tsx       # Quality assessment
│   ├── VariableExplorer.tsx    # Variable analysis
│   ├── SmartFilters.tsx        # AI filter studio
│   ├── TwinTransformer.tsx     # Digital twin generator
│   ├── Exports.tsx             # Export page
│   └── PreviousAnalyses.tsx    # History
│
├── 🧩 components/
│   ├── Layout.tsx              # Main layout
│   └── twin/                   # Twin Transformer components
│       ├── ColumnAnalysis.tsx
│       ├── TransformSettings.tsx
│       ├── LiveOutput.tsx
│       ├── RowTransformTable.tsx
│       ├── ResultViewer.tsx
│       └── ExportSettingsModal.tsx
│
├── 🔧 services/
│   ├── apiService.ts           # API client
│   ├── geminiService.ts        # Gemini AI (legacy)
│   └── transformService.ts     # Transform API client
│
├── 📄 types.ts                 # TypeScript definitions
├── 📄 constants.ts             # Application constants
├── 🐳 docker-compose.yml       # Docker configuration
├── 🐳 Dockerfile.frontend      # Frontend Docker image
└── 📄 package.json             # Node.js dependencies
```

---

## 🔧 Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
npm install
npm run dev
```

### Build for Production

```bash
# Frontend
npm run build

# Docker
docker-compose -f docker-compose.yml up -d --build
```

---

## ❗ Troubleshooting

<details>
<summary><b>🔴 Database connection failed</b></summary>

1. Check PostgreSQL is running
2. Verify `DATABASE_URL` in `.env`
3. Ensure database `sav_insight` exists
4. Check network/firewall settings

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"
```
</details>

<details>
<summary><b>🔴 OpenAI API errors</b></summary>

1. Verify `OPENAI_API_KEY` is set
2. Check API key has GPT-4 access
3. Ensure sufficient quota/credits

```bash
# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```
</details>

<details>
<summary><b>🔴 Smart Filters not working</b></summary>

1. Ensure dataset has enough categorical variables
2. Check variables have value labels
3. Verify OpenAI API is configured
4. Check backend logs for errors

```bash
docker logs sav-insight-backend | grep -i "smart\|filter\|error"
```
</details>

<details>
<summary><b>🔴 CSV export missing smart filter values</b></summary>

1. Ensure smart filters are **Applied** (not just added)
2. Check `sourceVars` match actual dataset columns
3. Verify dataset file exists in uploads folder
4. Check backend logs for path issues

```bash
docker logs sav-insight-backend | grep -i "CSV EXPORT"
```
</details>

---

## 🛡️ Security

- 🔒 All API keys stored server-side
- 🔒 CORS configured for production
- 🔒 SQL injection prevention via SQLAlchemy
- 🔒 File upload validation
- 🔒 No sensitive data in logs

---

## 📊 Tech Stack

<div align="center">

| Frontend | Backend | Database | AI |
|:--------:|:-------:|:--------:|:--:|
| ![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=white) | ![FastAPI](https://img.shields.io/badge/FastAPI-0.100-009688?style=flat-square&logo=fastapi&logoColor=white) | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white) | ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?style=flat-square&logo=openai&logoColor=white) |
| ![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript&logoColor=white) | ![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white) | ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white) | ![SPSS](https://img.shields.io/badge/SPSS-Parser-052FAD?style=flat-square) |
| ![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) | ![Docker](https://img.shields.io/badge/Docker-24-2496ED?style=flat-square&logo=docker&logoColor=white) | | |

</div>

---

## 📜 License

This is a **private project**. All rights reserved.

---

<div align="center">

**Built with 💜 by Native AI Team**

[🔝 Back to Top](#-sav-insight-studio)

</div>
