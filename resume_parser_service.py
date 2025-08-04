import requests
from PyPDF2 import PdfReader
import io
import os
import pdfplumber
import re
from datetime import datetime

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
            return len(text.split()) > ResumeParserService.MIN_WORDS_THRESHOLD  # At least 100 words
        except Exception:
            return False

    @staticmethod
    def check_ats_compliance(file_bytes: bytes) -> dict:
        """
        Check if the PDF contains essential ATS fields (name, email, phone, etc.).
        Returns a dict with found/missing fields with enhanced accuracy.
        """
        try:
            pdf = PdfReader(io.BytesIO(file_bytes))
            text = ""
            lines = []  # سنحتفظ بالأسطر الفردية لتحليل أفضل
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:  # تحقق من أن النص ليس None
                    text += page_text + "\n"
                    lines.extend(page_text.splitlines())  # حفظ كل سطر بشكل منفصل
        except Exception as e:
            return {"ats_compliant": False, "fields": {}, "error": f"Could not extract text from PDF: {str(e)}"}

        # تحقق من أن النص المستخرج ليس فارغًا
        if not text.strip():
            return {"ats_compliant": False, "fields": {}, "error": "No text content found in PDF (might be scanned image)"}

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
        
        # تحسينات في اكتشاف الاسم
        name_pattern = r"^#\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)+"
        for line in lines:
            if re.match(name_pattern, line.strip()):
                fields["full_name"] = True
                break
        
        # تحسينات في اكتشاف البريد الإلكتروني والهاتف
        email_pattern = r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
        phone_pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        
        fields["email"] = bool(re.search(email_pattern, text))
        fields["phone"] = bool(re.search(phone_pattern, text))
        
        # تحسينات في اكتشاف التعليم
        education_keywords = [
            "university", "college", "bachelor", "master", "phd", "degree", 
            "education", "gpa", "graduation", "diploma", "faculty", "school"
        ]
        education_section_found = any(
            re.search(r"^#+\s*EDUCATION\s*$", line.strip(), re.IGNORECASE) 
            for line in lines
        )
        
        education_content_found = any(
            re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE) 
            for keyword in education_keywords
        )
        
        fields["education"] = education_section_found and education_content_found
        
        # تحسينات في اكتشاف الخبرة العملية
        work_experience_section_found = any(
            re.search(r"^#+\s*WORK\s+EXPERIENCE\s*$", line.strip(), re.IGNORECASE) 
            for line in lines
        )
        
        work_content_found = any(
            re.search(r"\b(company|position|experience|employment|work history|professional experience)\b", text, re.IGNORECASE)
        )
        
        fields["work_experience"] = work_experience_section_found and work_content_found
        
        # تحسينات في اكتشاف المهارات
        skills_section_found = any(
            re.search(r"^#+\s*ADDITIONAL\s+INFORMATION\s*$", line.strip(), re.IGNORECASE) 
            and any("skills" in line.lower() for line in lines[i:i+5])  # البحث في الأسطر التالية
            for i, line in enumerate(lines)
        )
        
        skills_content_found = any(
            re.search(r"Skills:\s*.+", line, re.IGNORECASE) 
            for line in lines
        )
        
        fields["skills"] = skills_section_found or skills_content_found
        
        ats_compliant = all(fields.values())
        return {
            "ats_compliant": ats_compliant,
            "fields": fields,
            "details": {
                "name_pattern": name_pattern,
                "email_pattern": email_pattern,
                "phone_pattern": phone_pattern
            }
        }

    @staticmethod
    def extract_resume_info(file_bytes: bytes) -> dict:
        """
        Extract relevant information from the PDF resume using advanced libraries.
        """
        try:
            # Use pdfplumber for better text extraction
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise Exception(f"Could not extract text from PDF: {str(e)}")

        if not text.strip():
            raise Exception("No text content found in PDF")

        # Initialize result structure according to the required format
        result = {
            "full_name": "",
            "email": "",
            "phone": "",
            "location": "",
            "links": {
                "github": "",
                "linkedin": "",
                "portfolio": ""
            },
            "work_experience": [],
            "education": [],
            "additional_info": {
                "skills": [],
                "interests": [],
                "volunteer": []
            }
        }

        # Extract basic information using improved patterns
        lines = text.split('\n')
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, text)
        if email_matches:
            result["email"] = email_matches[0]

        # Extract phone numbers (multiple formats)
        phone_patterns = [
            r'\+?[\d\s\-\(\)]{10,}',  # International format
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # US format
            r'\d{3}-\d{3}-\d{4}',  # US format with dashes
            r'\d{10,}',  # Simple digits
        ]
        
        for pattern in phone_patterns:
            phone_matches = re.findall(pattern, text)
            if phone_matches:
                result["phone"] = phone_matches[0].strip()
                break

        # Extract name (first prominent name-like line)
        name_pattern = r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$'
        for line in lines[:5]:  # Check first 5 lines
            line_clean = line.strip()
            if re.match(name_pattern, line_clean) and len(line_clean.split()) >= 2:
                result["full_name"] = line_clean
                break

        # Extract location from contact line
        contact_line = ""
        for line in lines:
            if (re.search(email_pattern, line) or 
                any(re.search(pattern, line) for pattern in phone_patterns)):
                contact_line = line
                break
        
        if contact_line:
            # Extract location (words that are not email, phone, or links)
            words = re.split(r'[|,\s]+', contact_line)
            location_words = []
            for word in words:
                word = word.strip()
                if (word and 
                    not re.match(email_pattern, word) and
                    not any(re.match(pattern, word) for pattern in phone_patterns) and
                    not re.match(r'https?://', word) and
                    not re.match(r'www\.', word) and
                    not re.match(r'github\.com|linkedin\.com', word, re.IGNORECASE) and
                    len(word) > 2):
                    location_words.append(word)
            
            if location_words:
                result["location"] = ", ".join(location_words)

        # Extract links
        github_pattern = r'github\.com/[^\s]+'
        linkedin_pattern = r'linkedin\.com/[^\s]+'
        portfolio_pattern = r'https?://[^\s]*(?:portfolio|website|site)[^\s]*'
        
        github_matches = re.findall(github_pattern, text, re.IGNORECASE)
        if github_matches:
            result["links"]["github"] = github_matches[0]
        
        linkedin_matches = re.findall(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_matches:
            result["links"]["linkedin"] = linkedin_matches[0]
        
        portfolio_matches = re.findall(portfolio_pattern, text, re.IGNORECASE)
        if portfolio_matches:
            result["links"]["portfolio"] = portfolio_matches[0]

        # Extract sections using improved logic
        sections = ResumeParserService._extract_sections_improved(text)
        
        # Extract work experience with detailed parsing
        if "experience" in sections:
            result["work_experience"] = ResumeParserService._parse_experience_detailed(sections["experience"])
        
        # Extract education with detailed parsing
        if "education" in sections:
            result["education"] = ResumeParserService._parse_education_detailed(sections["education"])
        
        # Extract skills
        if "skills" in sections:
            result["additional_info"]["skills"] = ResumeParserService._parse_skills_improved(sections["skills"])
        
        # Extract interests
        if "interests" in sections:
            result["additional_info"]["interests"] = ResumeParserService._parse_interests_improved(sections["interests"])
        
        # Extract volunteer work
        if "volunteer" in sections:
            result["additional_info"]["volunteer"] = ResumeParserService._parse_volunteer_improved(sections["volunteer"])
        
        # Extract additional information
        if "additional_info" in sections:
            additional_info = ResumeParserService._parse_additional_info(sections["additional_info"])
            # Merge skills if found in additional_info
            if additional_info.get("skills"):
                result["additional_info"]["skills"].extend(additional_info["skills"])
            # Merge volunteer info if found in additional_info
            if additional_info.get("volunteer"):
                result["additional_info"]["volunteer"].extend(additional_info["volunteer"])
            # Merge other additional info
            if additional_info.get("interests"):
                result["additional_info"]["interests"].extend(additional_info["interests"])

        return result

    @staticmethod
    def _extract_sections_improved(text: str) -> dict:
        """Extract sections from text using improved logic."""
        sections = {}
        lines = text.split('\n')
        
        current_section = None
        current_content = []
        
        section_keywords = {
            "experience": ["experience", "work experience", "employment", "professional experience"],
            "education": ["education", "academic", "qualifications"],
            "skills": ["skills", "technical skills", "competencies", "technologies"],
            "interests": ["interests", "hobbies", "activities"],
            "volunteer": ["volunteer", "volunteering", "community service"],
            "additional_info": ["additional information", "additional info", "other information"]
        }
        
        for line in lines:
            line_clean = line.strip()
            
            # Skip empty lines and separators
            if not line_clean or (line_clean.startswith('-') and len(line_clean) > 10):
                continue
            
            # Check if this line starts a new section
            line_lower = line_clean.lower()
            found_section = None
            
            for section_name, keywords in section_keywords.items():
                if any(keyword in line_lower for keyword in keywords):
                    found_section = section_name
                    break
            
            if found_section:
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = current_content
                
                # Start new section
                current_section = found_section
                current_content = []
            elif current_section:
                # Check if we've hit another section header (all caps words)
                if (line_clean.isupper() and len(line_clean.split()) <= 3 and 
                    any(keyword in line_clean.lower() for keywords in section_keywords.values() for keyword in keywords)):
                    # Save current section and start new one
                    if current_content:
                        sections[current_section] = current_content
                    current_section = None
                    current_content = []
                else:
                    current_content.append(line_clean)
        
        # Save last section
        if current_section and current_content:
            sections[current_section] = current_content
        
        return sections

    @staticmethod
    def _parse_experience_improved(experience_lines: list) -> list:
        """Parse work experience with improved logic."""
        experiences = []
        current_exp = ""
        
        for line in experience_lines:
            if "|" in line:  # New experience entry
                if current_exp:
                    experiences.append(current_exp.strip())
                current_exp = line
            else:
                current_exp += " " + line
        
        if current_exp:
            experiences.append(current_exp.strip())
        
        return experiences

    @staticmethod
    def _parse_education_improved(education_lines: list) -> list:
        """Parse education with improved logic."""
        education = []
        for line in education_lines:
            if line and not line.startswith('-'):
                education.append(line)
        
        return education

    @staticmethod
    def _parse_skills_improved(skills_lines: list) -> list:
        """Parse skills with improved logic."""
        skills_text = " ".join(skills_lines)
        # Split by commas and clean up
        skills = [skill.strip() for skill in re.split(r',|\s+', skills_text) 
                 if skill.strip() and len(skill.strip()) > 1 and not skill.strip().startswith('-')]
        return skills

    @staticmethod
    def _parse_interests_improved(interests_lines: list) -> list:
        """Parse interests with improved logic."""
        return ResumeParserService._parse_skills_improved(interests_lines)

    @staticmethod
    def _parse_volunteer_improved(volunteer_lines: list) -> list:
        """Parse volunteer work with improved logic."""
        volunteer = []
        for line in volunteer_lines:
            if line and not line.startswith('-'):
                volunteer.append(line)
        
        return volunteer

    @staticmethod
    def _parse_additional_info(additional_lines: list) -> dict:
        """Parse additional information section."""
        additional_info = {
            "skills": [],
            "volunteer": [],
            "interests": []
        }
        
        for line in additional_lines:
            if line and not line.startswith('-'):
                line_lower = line.lower()
                if "volunteer" in line_lower:
                    # Extract volunteer information
                    volunteer_text = line.replace("Volunteer:", "").strip()
                    if volunteer_text:
                        additional_info["volunteer"].append(volunteer_text)
                elif "skills" in line_lower:
                    # Extract skills information
                    skills_text = line.replace("Skills:", "").strip()
                    if skills_text:
                        skills = [skill.strip() for skill in re.split(r',|\s+', skills_text) 
                                if skill.strip() and len(skill.strip()) > 1]
                        additional_info["skills"].extend(skills)
                else:
                    # Consider other lines as interests or general info
                    additional_info["interests"].append(line)
        
        return additional_info

    @staticmethod
    def _parse_experience_detailed(experience_lines: list) -> list:
        """Parse work experience with detailed structure."""
        experiences = []
        current_exp = {
            "Company Name": "",
            "location": "",
            "description": "",
            "start_date": "",
            "end_date": None,
            "projects": ""
        }
        
        for line in experience_lines:
            if "|" in line:  # New experience entry
                if current_exp["Company Name"]:  # Save previous experience
                    experiences.append(current_exp.copy())
                
                # Parse new experience line
                parts = [part.strip() for part in line.split("|")]
                if len(parts) >= 1:
                    current_exp["Company Name"] = parts[0]
                if len(parts) >= 2:
                    # Try to extract dates
                    date_part = parts[1]
                    dates = re.findall(r'\d{2}/\d{4}|\d{4}', date_part)
                    if len(dates) >= 1:
                        current_exp["start_date"] = dates[0]
                    if len(dates) >= 2:
                        current_exp["end_date"] = dates[1]
                    elif "present" in date_part.lower():
                        current_exp["end_date"] = None
                if len(parts) >= 3:
                    current_exp["location"] = parts[2]
                if len(parts) >= 4:
                    current_exp["projects"] = parts[3]
            else:
                # Add to description
                if line.strip() and not line.strip().startswith('-'):
                    current_exp["description"] += line.strip() + " "
        
        # Add last experience
        if current_exp["Company Name"]:
            experiences.append(current_exp)
        
        return experiences

    @staticmethod
    def _parse_education_detailed(education_lines: list) -> list:
        """Parse education with detailed structure."""
        education_list = []
        
        for line in education_lines:
            if line and not line.startswith('-'):
                education = {
                    "university_name": "",
                    "graduate_date": "",
                    "location": "",
                    "GPA": ""
                }
                
                # Parse education line (usually format: degree | university | location)
                parts = [part.strip() for part in line.split("|")]
                if len(parts) >= 1:
                    education["university_name"] = parts[0]
                if len(parts) >= 2:
                    education["location"] = parts[1]
                if len(parts) >= 3:
                    # Try to extract graduation date
                    date_part = parts[2]
                    dates = re.findall(r'\d{4}', date_part)
                    if dates:
                        education["graduate_date"] = dates[0]
                
                education_list.append(education)
        
        return education_list 