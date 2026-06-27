from typing import Any, Optional, Dict
from pydantic import BaseModel


class ServiceResponse(BaseModel):
    """
    Standard response format for all system commands.
    """

    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    code: Optional[str] = None

    @classmethod
    def success_res(cls, message: str, data: Any = None):
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_res(
        cls, error: str, code: str = "INTERNAL_ERROR", message: Optional[str] = None
    ):
        return cls(
            success=False, message=message or f"Error: {error}", error=error, code=code
        )
