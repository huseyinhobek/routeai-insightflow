<div align="center">

# 🚀 RouteAI InsightFlow

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue?style=for-the-badge&logo=git&logoColor=white)
![License](https://img.shields.io/badge/license-Proprietary-red?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19.2-61DAFB?style=for-the-badge&logo=react&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=for-the-badge&logo=postgresql&logoColor=white)

**Enterprise-grade AI-powered survey data analysis platform**

*Transform raw survey data into actionable insights with cutting-edge AI technology*

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

</div>

## 🌟 Overview

**RouteAI InsightFlow** is a next-generation survey data analysis platform that combines the power of AI, natural language processing, and advanced data science to transform raw survey responses into meaningful, actionable insights. Built for researchers, analysts, and decision-makers who need to extract maximum value from their survey data.

### 🎯 What Makes It Special?

- **🤖 AI-Powered Analysis**: Leverages GPT-4, embeddings, and RAG (Retrieval-Augmented Generation) for intelligent question answering
- **📊 Multi-Modal Insights**: Structured SQL aggregation + semantic search for comprehensive analysis
- **🔄 Digital Twin Transformation**: Convert survey responses into first-person narratives for AI consumption
- **🎯 Decision Proxy System**: AI-driven decision support with confidence scoring and risk assessment
- **📈 Real-Time Progress Tracking**: Background embedding generation with auto-resume capabilities
- **🔍 Smart Filtering**: AI-suggested segmentation filters for advanced audience analysis
- **🌐 Multi-Language Support**: Full Turkish language support with extensible architecture

---

## ✨ Features

### 📊 Core Data Analysis

<table>
<tr>
<td width="50%">

#### 🔄 Data Ingestion
- **SPSS (.sav) Support**: Full compatibility with SPSS format
- **Excel/CSV Import**: Flexible data import options
- **Automatic Schema Detection**: Intelligent variable type recognition
- **Data Validation**: Real-time quality checks during upload
- **Batch Processing**: Handle large datasets efficiently

#### 📈 Quality Analysis
- **Comprehensive Reports**: Missing data, outliers, distributions
- **Variable Statistics**: Mean, median, mode, standard deviation
- **Completion Rates**: Per-variable and overall completion tracking
- **Data Quality Scores**: Automated quality assessment
- **Visual Analytics**: Interactive charts and graphs

</td>
<td width="50%">

#### 🔍 Variable Explorer
- **Deep Variable Analysis**: Detailed statistics per variable
- **Type Detection**: Automatic classification (numeric, text, categorical)
- **Distribution Visualization**: Histograms, bar charts, pie charts
- **Missing Value Analysis**: Comprehensive missing data insights
- **Export Capabilities**: Export variable-level reports

#### 🎯 Smart Filters
- **AI-Powered Suggestions**: GPT-generated filter recommendations
- **Manual Filtering**: Custom variable-based filters
- **Multi-Select Support**: Combine multiple filters
- **Audience Creation**: Convert filters to reusable audiences
- **CSV Export Integration**: Filters included in exports

</td>
</tr>
</table>

### 🤖 AI-Powered Features

<table>
<tr>
<td width="50%">

#### 💬 Research Workflow
- **Natural Language Queries**: Ask questions in plain Turkish/English
- **Dual-Mode Answering**:
  - **Structured Mode**: Direct SQL aggregation for survey questions
  - **RAG Mode**: Semantic search over transformed utterances
- **Evidence Contract**: Every answer includes provenance and evidence
- **Guardrails**: Number validation, quantifier policy enforcement
- **Thread Management**: Persistent conversation threads
- **Audience Context**: Answer questions within specific audience segments

#### 🔄 Twin Transformer
- **First-Person Conversion**: Transform survey responses to "I" statements
- **AI-Ready Format**: Optimized for LLM consumption
- **Batch Processing**: Process entire datasets efficiently
- **Progress Tracking**: Real-time transformation status
- **Error Handling**: Comprehensive error reporting and recovery

</td>
<td width="50%">

#### 🎯 Decision Proxy
- **Decision Intent Detection**: Automatically identify decision-oriented questions
- **Proxy Variable Identification**: Find relevant variables for decisions
- **Confidence Scoring**: AI-generated confidence levels
- **Risk Assessment**: Multiple decision rules (popularity, risk-averse, segment-fit)
- **Distribution Analysis**: Visual comparison charts
- **Next Best Questions**: AI-suggested follow-up questions

#### 🔍 Embedding Generation
- **Vector Embeddings**: OpenAI embeddings for semantic search
- **Background Processing**: Non-blocking embedding generation
- **Auto-Resume**: Automatic continuation after interruptions
- **Progress Tracking**: Real-time progress monitoring
- **Idempotent Operations**: Safe to run multiple times

</td>
</tr>
</table>

### 🏗️ Enterprise Features

<table>
<tr>
<td width="33%">

#### 👥 User Management
- **Multi-Organization Support**: Isolated data per organization
- **Role-Based Access Control**: Super admin, org admin, user roles
- **Magic Link Authentication**: Passwordless login
- **OTP Support**: One-time password verification
- **Audit Logging**: Comprehensive activity tracking

</td>
<td width="33%">

#### 📤 Export & Integration
- **Multiple Formats**: CSV, JSON, Excel exports
- **Smart Filter Integration**: Filters included in exports
- **Custom Field Selection**: Choose specific variables
- **Batch Export**: Export multiple datasets
- **API Access**: RESTful API for integrations

</td>
<td width="33%">

#### 🔒 Security & Compliance
- **JWT Authentication**: Secure token-based auth
- **Organization Isolation**: Data segregation by org
- **Security Headers**: CORS, XSS protection
- **Input Validation**: Comprehensive data validation
- **Error Handling**: Graceful error recovery

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Upload   │  │ Overview │  │ Threads  │  │  Export  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP/REST
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Backend (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Research   │  │  Transform   │  │   Embedding   │    │
│  │   Service    │  │   Service    │  │   Service    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Decision   │  │     RAG      │  │   Quality    │    │
│  │    Proxy     │  │   Service    │  │   Analyzer   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐   ┌────────▼────────┐   ┌──────▼──────┐
│  PostgreSQL  │   │   OpenAI API    │   │   Redis     │
│  + pgvector  │   │   (GPT-4)      │   │   (Cache)   │
└──────────────┘   └─────────────────┘   └─────────────┘
```

### 🧩 Technology Stack

**Frontend:**
- React 19.2 with TypeScript
- Vite for blazing-fast builds
- TailwindCSS for styling
- Recharts for data visualization
- React Router for navigation

**Backend:**
- FastAPI (Python 3.12+)
- SQLAlchemy ORM
- PostgreSQL with pgvector extension
- OpenAI API integration
- Redis for caching
- Celery for background tasks

**Infrastructure:**
- Docker & Docker Compose
- Nginx for reverse proxy
- Multi-stage builds for optimization

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (recommended)
- OR **Python 3.12+** and **Node.js 20+** for local development
- **PostgreSQL 16+** with pgvector extension
- **OpenAI API Key** (for AI features)

### 🐳 Docker Setup (Recommended)

1. **Clone the repository**
```bash
git clone https://github.com/huseyinhobek/routeai-insightflow.git
cd routeai-insightflow
```

2. **Configure environment variables**

Create `sav-insight-studio/.env`:
```env
# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/sav_insight

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

# Storage
UPLOAD_DIR=./uploads

# Debug
DEBUG=false
```

3. **Start the application**
```bash
cd sav-insight-studio
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 💻 Local Development Setup

#### Backend Setup

```bash
cd sav-insight-studio/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (create .env file)
# Run migrations
python -c "from database import init_db; init_db()"

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd sav-insight-studio

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 📖 Documentation

### 🔬 Research Workflow

The Research Workflow system enables natural language question answering over survey data:

#### **Structured Mode**
- Direct SQL aggregation for questions that map to survey variables
- Fast, deterministic answers with exact numbers
- Evidence includes variable mappings and SQL queries

#### **RAG Mode**
- Semantic search over transformed first-person utterances
- Answers questions not directly in the survey
- Uses vector embeddings for similarity search
- Synthesizes answers from multiple relevant utterances

#### **Usage Example**

```python
# Create a thread
POST /api/research/threads
{
  "dataset_id": "xxx",
  "audience_id": "yyy"  # optional
}

# Ask a question
POST /api/research/threads/{thread_id}/questions
{
  "question": "Yaş ortalaması nedir?"
}

# Response includes:
{
  "answer": "Yaş ortalaması 42.3'tür.",
  "mode": "structured",
  "evidence": {
    "variables": ["AGE"],
    "sql_query": "SELECT AVG(age) FROM ...",
    "confidence": 0.95
  }
}
```

### 🔄 Twin Transformer

Transform survey responses into first-person narratives:

```python
# Start transformation
POST /api/transform/{dataset_id}/start

# Check status
GET /api/transform/{dataset_id}/status

# Results are stored as Utterances
# Each utterance is a first-person statement ready for AI processing
```

### 🎯 Decision Proxy

Get AI-powered decision support:

```python
# Ask a decision question
POST /api/research/threads/{thread_id}/questions
{
  "question": "Hangi ürünü seçmeliyim?"
}

# Response includes:
{
  "mode": "decision_proxy",
  "proxy_variable": "PRODUCT_PREFERENCE",
  "rules": [
    {
      "type": "popularity-first",
      "recommendation": "Product A",
      "confidence": 0.87
    }
  ],
  "distribution": {...},
  "next_questions": [...]
}
```

### 📊 API Endpoints

#### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/datasets` | GET | List all datasets |
| `/api/datasets` | POST | Upload new dataset |
| `/api/datasets/{id}` | GET | Get dataset details |
| `/api/research/threads` | POST | Create research thread |
| `/api/research/threads/{id}/questions` | POST | Ask a question |
| `/api/transform/{id}/start` | POST | Start transformation |
| `/api/research/datasets/{id}/generate-embeddings` | POST | Generate embeddings |

Full API documentation available at `/docs` when running the backend.

---

## 🎨 UI Components

### 📤 Upload Page
- Drag & drop file upload
- Real-time validation
- Progress tracking
- Multiple format support

### 📊 Dataset Overview
- Key metrics dashboard
- Variable type distribution
- Completion rate analysis
- Embedding progress tracking

### 💬 Thread Chat
- Natural language interface
- Real-time question answering
- Evidence visualization
- Decision proxy UI
- Next question suggestions

### 🔄 Twin Transformer
- Batch transformation interface
- Progress monitoring
- Error reporting
- Result preview

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `OPENAI_API_KEY` | OpenAI API key for AI features | Required |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `REDIS_URL` | Redis connection string | Optional |
| `SECRET_KEY` | Application secret key | Required |
| `JWT_SECRET` | JWT signing secret | Required |
| `UPLOAD_DIR` | Directory for uploaded files | `./uploads` |
| `DEBUG` | Enable debug mode | `false` |

### Database Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- The application will create all necessary tables on startup
```

---

## 🧪 Testing

```bash
# Backend tests
cd sav-insight-studio/backend
pytest

# Frontend tests
cd sav-insight-studio
npm test
```

---

## 📈 Performance

- **Embedding Generation**: Background processing with auto-resume
- **Query Response Time**: < 2s for structured queries, < 5s for RAG
- **Concurrent Users**: Tested up to 100 concurrent threads
- **Dataset Size**: Supports datasets up to 100K+ rows
- **Vector Search**: Optimized with pgvector indexes

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- **Python**: Follow PEP 8, use Black formatter
- **TypeScript**: Follow ESLint rules, use Prettier
- **Commits**: Use conventional commit messages

---

## 📝 License

This project is proprietary software. All rights reserved.

---

## 🙏 Acknowledgments

- OpenAI for GPT-4 and embedding models
- FastAPI for the excellent web framework
- React team for the amazing UI library
- PostgreSQL and pgvector for vector search capabilities

---

## 📞 Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Contact: [Your Contact Information]

---

<div align="center">

**Made with ❤️ by the RouteAI Team**

[⭐ Star us on GitHub](https://github.com/huseyinhobek/routeai-insightflow) • [📖 Documentation](#-documentation) • [🐛 Report Bug](https://github.com/huseyinhobek/routeai-insightflow/issues)

</div>

