# Resume Generator App

An AI-powered application that generates tailored resumes and cover letters using FastAPI and Google Gemini AI.

## Features

- Job description analysis and keyword extraction
- Resume tailoring based on job requirements
- Cover letter generation
- ATS-friendly formatting
- STAR methodology integration

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file with your Google API key: `GOOGLE_API_KEY=your_key_here`
4. Run the app: `uvicorn main:app --reload`

## API Endpoints

- `POST /generate-full-application/` - Generate complete application package

## Usage

Upload your master resume, STAR stories, and job description to get a tailored application package.