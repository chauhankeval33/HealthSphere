# HealthSphere ? Medical Document AI Assistant

HealthSphere is an AI-powered medical document management and question-answering application.

> Disclaimer: This is an educational software project, not a medical diagnostic system. AI-generated content must not replace professional medical advice. Use fictional data for demonstrations and testing.

## Features

- Supabase authentication
- Patient record management
- Medical document upload and management
- PDF text extraction with OCR fallback
- Image OCR using Tesseract
- AI-assisted document analysis using Google Gemini
- Document indexing and retrieval-augmented generation (RAG)
- Conversation-aware question answering
- Source references for retrieved content
- Visit notes management

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Database and authentication | Supabase |
| AI integration | Google Gemini |
| PDF processing | pypdf, pypdfium2 |
| Image processing | Pillow |
| OCR | Tesseract, pytesseract |
| Deployment | Docker, Render, Netlify |

## Architecture

Browser -> HTML/CSS/JavaScript -> FastAPI Backend

The backend integrates with Supabase, Google Gemini, PDF processing, OCR, and document retrieval services.

## Project Structure

- ackend/api/ ? API routes
- ackend/database/ ? Database client
- ackend/schemas/ ? Data schemas
- ackend/services/ ? AI, OCR, embedding and RAG services
- rontend/ ? Static web application
- 	ests/ ? Tests

## Local Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

   pip install -r requirements.txt

4. Create .env using .env.example as a template.
5. Install the native Tesseract OCR executable.
6. Start the backend:

   uvicorn backend.main:app --reload

7. Serve the frontend from the rontend directory:

   python -m http.server 5500

Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

Frontend: http://localhost:5500

## Environment Variables

Configure Supabase and Gemini credentials in .env. Never commit secrets or API keys.

## Deployment

Planned deployment:

- Backend: Render using Dockerfile
- Frontend: Netlify
- Database and authentication: Supabase
- AI: Google Gemini

Production environment variables and frontend API URL must be configured in the hosting dashboards.

## Security and Privacy

- Never publish .env or API credentials.
- Do not publish real patient records.
- Use fictional data for demonstrations.
- Medical documents must be treated as sensitive information.

## Project Status

Deployment preparation in progress.

## License

No license has been assigned yet. All rights reserved unless a license is added.
