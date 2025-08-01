import requests
from PyPDF2 import PdfReader
import io
import os

class ResumeParserService:
    MIN_WORDS_THRESHOLD = 50

    @staticmethod
    def download_file(file_url: str) -> bytes:
        """
        Download the file from the given URL or read from local path and return its content as bytes.
        """
        if file_url.startswith('http://') or file_url.startswith('https://'):
            response = requests.get(file_url)
            if response.status_code != 200:
                raise Exception(f"Failed to download file. Status code: {response.status_code}")
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type:
                raise Exception("The file is not a PDF.")
            return response.content
        else:
            # Assume local file path
            if not os.path.isfile(file_url):
                raise Exception(f"Local file not found: {file_url}")
            if not file_url.lower().endswith('.pdf'):
                raise Exception("The file is not a PDF.")
            with open(file_url, 'rb') as f:
                return f.read()

    @staticmethod
    def validate_pdf(file_bytes: bytes) -> bool:
        """
        Validate that the file is a readable PDF (not scanned image).
        Returns True if the PDF contains extractable text, False otherwise.
        """
        try:
            pdf = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text.strip()
            # Consider it valid if there is a reasonable amount of text
            return len(text.split()) > ResumeParserService.MIN_WORDS_THRESHOLD
        except Exception:
            return False

    @staticmethod
    def check_ats_compliance(file_bytes: bytes) -> dict:
        """
        Check if the PDF contains essential ATS fields (name, email, phone, etc.).
        Returns a dict with found/missing fields.
        """
        try:
            pdf = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception:
            return {"ats_compliant": False, "fields": {}, "error": "Could not extract text from PDF."}

        import re
        fields = {
            "full_name": False,
            "email": False,
            "phone": False,
            "education": False,
            "work_experience": False,
            "skills": False,
            "location": False,
            "interests": False,
            "volunteer": False
        }
        # Simple regex and keyword checks
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        phone_pattern = r"\+?\d[\d\s\-()]{7,}"
        fields["email"] = bool(re.search(email_pattern, text))
        fields["phone"] = bool(re.search(phone_pattern, text))
        # Name: look for lines with two+ capitalized words (very basic)
        name_lines = [line for line in text.splitlines() if len(re.findall(r"[A-Z][a-z]+", line)) >= 2]
        fields["full_name"] = bool(name_lines)
        # Education: look for keywords
        fields["education"] = any(word in text.lower() for word in ["education", "bachelor", "master", "university", "degree"])
        # Work experience: look for keywords
        fields["work_experience"] = any(word in text.lower() for word in ["experience", "employment", "work history", "professional experience"])
        # Skills: look for keyword
        fields["skills"] = "skills" in text.lower()
        # Location: look for address patterns or city/country keywords
        location_keywords = ["address", "location", "city", "country", "state", "province", "street", "avenue", "road"]
        fields["location"] = any(word in text.lower() for word in location_keywords)
        
        # تحسين اكتشاف الموقع: البحث في السطر الذي يحتوي على الإيميل والهاتف
        lines = text.splitlines()
        for line in lines:
            # تحقق من أن السطر يحتوي على إيميل أو هاتف
            if re.search(email_pattern, line) or re.search(phone_pattern, line):
                # استخرج الكلمات التي ليست إيميل أو هاتف أو روابط
                words = line.split()
                location_words = []
                for word in words:
                    word_clean = re.sub(r'[^\w\s]', '', word)  # إزالة علامات الترقيم
                    # تجاهل الكلمات التي هي إيميل أو هاتف أو روابط
                    if (not re.match(email_pattern, word) and 
                        not re.match(phone_pattern, word) and
                        not re.match(r'https?://', word) and
                        not re.match(r'www\.', word) and
                        not re.match(r'github\.com', word, re.IGNORECASE) and
                        not re.match(r'linkedin\.com', word, re.IGNORECASE) and
                        len(word_clean) > 2):  # تجاهل الكلمات القصيرة جدًا
                        location_words.append(word_clean)
                
                if location_words:
                    fields["location"] = True
                    break
        
        # Interests: look for interests section or keywords
        interests_keywords = ["interests", "hobbies", "activities", "passions", "likes"]
        fields["interests"] = any(word in text.lower() for word in interests_keywords)
        # Volunteer work: look for volunteer section or keywords
        volunteer_keywords = ["volunteer", "volunteering", "community service", "charity", "non-profit", "social work"]
        fields["volunteer"] = any(word in text.lower() for word in volunteer_keywords)
        ats_compliant = all(fields.values())
        return {"ats_compliant": ats_compliant, "fields": fields}

    @staticmethod
    def extract_resume_info(file_bytes: bytes) -> dict:
        """
        Extract relevant information from the PDF resume.
        """
        # TODO: implement extraction logic
        pass 