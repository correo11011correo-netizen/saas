import uuid
from dataclasses import dataclass


@dataclass
class TenantContext:
    """
    Carries the identity of the current tenant and user
    throughout the command execution lifecycle.
    """

    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    plan: str = "free"  # default to free
    credential_id: str | None = None
