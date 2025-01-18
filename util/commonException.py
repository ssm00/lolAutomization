from enum import Enum
from typing import Any, Optional

class ErrorCode(Enum):
    JSON_DECODE_ERROR = "JSON_DECODE_ERROR"
    SERVER_BUSY = "SERVER_BUSY"
    TRANSLATION_ERROR = "TRANSLATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    NOMATCH_IMAGE = "NOMATCH_IMAGE"

class CommonError(Exception):
    def __init__(self, error_code: ErrorCode, message: str, data: Optional[Any] = None, original_error: Optional[Exception] = None):
        self.error_code = error_code
        self.message = message
        self.data = data
        self.original_error = original_error
        super().__init__(self.message)

    def to_dict(self):
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "data": self.data
        }
