from typing import Any

from pydantic import BaseModel


class ServiceResponse(BaseModel):
    """
    Standard response format for all system commands.
    """

    success: bool
    message: str
    data: Any | None = None
    error: str | None = None
    code: str | None = None

    @classmethod
    def success_res(cls, message: str, data: Any = None):
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_res(cls, error: str, code: str = "INTERNAL_ERROR", message: str | None = None):
        return cls(success=False, message=message or f"Error: {error}", error=error, code=code)
