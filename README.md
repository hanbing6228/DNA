# DNA Personal Genome Analyzer

Personal genome interpretation system.

## Input
- VCF
- VCF.GZ

## Pipeline
```
VCF
  ↓
Parser
  ↓
Variant normalization
  ↓
ClinVar lookup
  ↓
Annotation
  ↓
Personal report
```

## Features
- Variant summary
- Pathogenic findings
- Gene interpretation
- Evidence tracking

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
