# वाङ्मयम् (Vāṇmayam) - MVP

**The Vedic Corpus Portal - Minimum Viable Product**

A digital preservation platform for Vedic literature with AI-powered OCR, collaborative editing, and Sanskrit-optimized search.

## MVP Features

### Core Functionality
- **Document Import**: PDF upload and processing pipeline
- **OCR Processing**: Multi-engine OCR with confidence scoring
- **Collaborative Editing**: Side-by-side proofreading interface
- **Search**: Basic full-text search with Sanskrit support
- **User Management**: Role-based access (Admin, Editor, Reader)
- **Export**: PDF and text export capabilities

### Technical Stack
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React.js with TypeScript
- **Database**: PostgreSQL with JSONB
- **Search**: Elasticsearch
- **Storage**: Local file system (MinIO for production)
- **Queue**: Celery with Redis
- **OCR**: Tesseract + Google Vision API

## Project Structure

```
vangmayam-mvp/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Core configuration
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utilities
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   └── utils/          # Frontend utilities
│   ├── public/             # Static assets
│   └── package.json        # Node dependencies
├── docker/                 # Docker configurations
├── scripts/                # Utility scripts
└── docs/                   # Documentation
```

## Quick Start

1. **Setup Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Setup Frontend**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Setup Services**:
   ```bash
   docker-compose up -d  # PostgreSQL, Redis, Elasticsearch
   ```

## Development Guidelines

- **Code Quality**: Type hints, linting, comprehensive tests
- **Security**: JWT authentication, input validation, CORS
- **Performance**: Async/await, database indexing, caching
- **Accessibility**: WCAG 2.1 AA compliance
- **Documentation**: API docs, code comments, user guides

## License

MIT License - Open source for cultural preservation

---

**Vaidika Samrakshana Parishad** - Preserving Vedic heritage through technology
