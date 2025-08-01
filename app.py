from flask import Flask, request
from response_handler import ResponseHandler
from resume_parser_service import ResumeParserService

app = Flask(__name__)

@app.route('/api/parse_resume', methods=['POST'])
def parse_resume():
    data = request.get_json()
    if not data or 'file_url' not in data:
        return ResponseHandler.validation_error("Missing 'file_url' in request body")
    file_url = data['file_url']
    try:
        file_bytes = ResumeParserService.download_file(file_url)
        extracted_info = ResumeParserService.extract_resume_info(file_bytes)
        return ResponseHandler.success(extracted_info, message="Resume parsed successfully.")
    except Exception as e:
        return ResponseHandler.server_error(str(e))

@app.route('/api/is_readable', methods=['POST'])
def is_readable():
    data = request.get_json()
    if not data or 'file_url' not in data:
        return ResponseHandler.validation_error("Missing 'file_url' in request body")
    file_url = data['file_url']
    try:
        file_bytes = ResumeParserService.download_file(file_url)
        is_valid = ResumeParserService.validate_pdf(file_bytes)
        if not is_valid:
            return ResponseHandler.validation_error(f"PDF is not readable (might be scanned image or contains less than {ResumeParserService.MIN_WORDS_THRESHOLD} words)", {"is_readable": False, "ats_compliant": False, "fields": {}})
        ats_result = ResumeParserService.check_ats_compliance(file_bytes)
        return ResponseHandler.success({"is_readable": is_valid, **ats_result}, message="PDF readability and ATS compliance check completed.")
    except Exception as e:
        return ResponseHandler.server_error(str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002) 