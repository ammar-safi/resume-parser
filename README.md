# Resume Parser API

A Flask-based API for parsing and extracting structured information from resume (CV) PDF files. The service is designed to help HR systems and ATS (Applicant Tracking Systems) extract key candidate information from English-language, text-based PDF resumes.

## Features

- Accepts a URL to a PDF resume file via a REST API endpoint
- Validates that the file is a readable, text-based PDF (not a scanned image)
- Extracts key information such as:
  - Full Name
  - Email
  - Phone Number
  - Address (if available)
  - Work Experience
  - Education
  - Skills
  - Certifications (if available)
  - Links (LinkedIn, GitHub, etc.)
  - Summary (if available)
- Returns results in a standardized JSON format

## API Usage

### Endpoint

`POST /api/parse_resume`

#### Request Body (JSON)

```
{
  "file_url": "https://example.com/path/to/resume.pdf"
}
```

#### Successful Response

```
{
  "data": {
    "full_name": "John Doe",
    "email": "john.doe@email.com",
    "phone": "+1234567890",
    "address": "123 Main St, City, Country",
    "work_experience": [...],
    "education": [...],
    "skills": [...],
    "certifications": [...],
    "links": [...],
    "summary": "..."
  },
  "status": "success",
  "message": "Resume parsed successfully.",
  "status_code": 200
}
```

#### Error Response

```
{
  "data": null,
  "status": "error",
  "message": "The file is not a readable PDF (text-based)",
  "status_code": 400
}
```

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd resume_parser
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application:**
   ```bash
   python app.py
   ```

## Requirements

- Python 3.7+
- Flask
- requests
- PyPDF2

## Notes

- Only English, text-based PDF resumes are supported.
- No data is stored; all processing is in-memory and results are returned in the response.

## License

MIT
