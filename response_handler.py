from flask import jsonify
from typing import Any, Optional

class ResponseHandler:
    @staticmethod
    def success(data: Any = None, message: str = "Success", status_code: int = 200):
        """
        Create a successful response with standardized format
        """
        response = {
            "data": data,
            "status": "success",
            "message": message,
            "status_code": status_code
        }
        return jsonify(response), status_code
    
    @staticmethod
    def error(message: str = "Error occurred", data: Any = None, status_code: int = 400):
        """
        Create an error response with standardized format
        """
        response = {
            "data": data,
            "status": "error",
            "message": message,
            "status_code": status_code
        }
        return jsonify(response), status_code
    
    @staticmethod
    def not_found(message: str = "Resource not found", data: Any = None):
        """
        Create a 404 not found response
        """
        return ResponseHandler.error(message, data, 404)
    
    @staticmethod
    def validation_error(message: str = "Validation error", data: Any = None):
        """
        Create a validation error response
        """
        return ResponseHandler.error(message, data, 400)
    
    @staticmethod
    def server_error(message: str = "Internal server error", data: Any = None):
        """
        Create a server error response
        """
        return ResponseHandler.error(message, data, 500)