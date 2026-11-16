# System Architecture and Data Flow

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

## Project
AI-Assisted Cybersecurity Training Platform Using Log Analysis and a Local LLM

## Core Flow
Controlled local cybersecurity attacks → real security logs → log ingestion and normalization → structured/labeled dataset → rule-based detection + machine-learning detection → evaluation → FastAPI/PostgreSQL application layer → React training interface → local Ollama LLM + RAG explanations.

## Component Responsibilities

### Cybersecurity Lab

Purpose:
- Run only controlled local attack scenarios.
- Generate authentic benign and malicious security logs.
- Record exact run metadata so labels can be defended.

Required scenarios:
1. Brute-force attack
2. SQL injection
3. Reconnaissance / network scanning

### Data Processing

Purpose:
- Preserve raw evidence.
- Parse different log formats.
- Normalize them into a consistent event representation.
- Join events to trusted run metadata for labels.
- Engineer features for rules and ML.

### Rule-Based Detection

Purpose:
- Provide transparent baseline rules for all three attacks.
- Return both a decision and evidence explaining why the rule fired.

### Machine Learning

Technology:
- Python
- Pandas
- scikit-learn

Purpose:
- Train only on data generated from the project lab.
- Compare a small number of sensible classical models.
- Evaluate using accuracy, precision, recall, F1-score, confusion matrix, and false-positive rate.

### Backend and Database

Technology:
- FastAPI
- PostgreSQL

Purpose:
- Store runs, events, detections, and later explanations.
- Expose a small API to the frontend.
- Keep ground truth, rule predictions, and ML predictions clearly separate.

### Frontend

Technology:
- React
- TypeScript
- Vite
- Tailwind CSS

Purpose:
- Show runs, detections, evidence, evaluation metrics, and learning-oriented explanations.

### Local LLM and RAG

Technology:
- Ollama
- Sentence Transformers
- FAISS

Purpose:
- Explain existing detection evidence.
- Retrieve trusted cybersecurity/project documentation.
- Never replace, alter, or become the actual detection system.

## Architecture Rule
Detection and explanation are separate:

Security evidence → Rules/ML → Detection result → LLM/RAG explanation

The LLM receives detection evidence as input. It does not decide whether an attack occurred.

## Main Boundaries
- Raw logs are preserved and not silently edited.
- Labels come from controlled run metadata, not detector output.
- ML is not trained before a usable lab-generated dataset exists.
- RAG is not used as a detector.
- Only the three mandatory attack scenarios are required.
