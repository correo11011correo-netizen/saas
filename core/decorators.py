import functools
from typing import Callable, Any, Dict, Optional, Type
from pydantic import BaseModel


def command(
    name: str, 
    description: str, 
    params_model: Optional[Type[BaseModel]] = None,
    required_plan: str = "free"
):
    """
    Decorator to mark a method as a system command and register it
    with the dispatcher.
    """

    def decorator(func: Callable):
        # Attach metadata to the function for registration
        func._is_command = True
        func._command_name = name
        func._command_description = description
        func._params_model = params_model
        func._required_plan = required_plan

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator
