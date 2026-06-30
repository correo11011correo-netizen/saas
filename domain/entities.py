from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime
from typing import Any, Dict, List, Optional

@dataclass
class User:
    email: str
    role: str
    tenant_id: UUID
    id: UUID = field(default_factory=uuid4)

@dataclass
class Product:
    code: str
    name: str
    price: float
    quantity: int
    tenant_id: UUID
    id: UUID = field(default_factory=uuid4)

@dataclass
class SaleItem:
    product_code: str
    quantity: int
    price: float
    id: UUID = field(default_factory=uuid4)

@dataclass
class Sale:
    customer_id: UUID
    total: float
    tenant_id: UUID
    items: List[SaleItem] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    id: UUID = field(default_factory=uuid4)

@dataclass
class Customer:
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    tenant_id: UUID
    id: UUID = field(default_factory=uuid4)

@dataclass
class BotConfig:
    name: str
    settings: Dict[str, Any] = field(default_factory=dict)
    tenant_id: UUID
    id: UUID = field(default_factory=uuid4)
