import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    service_name = Column(String(100))
    account_alias = Column(String(100))
    api_key = Column(String, nullable=True)
    secret = Column(String, nullable=True)
    custom_data = Column("metadata", JSON)


class BotAssignment(Base):
    __tablename__ = "bot_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    credential_id = Column(UUID(as_uuid=True), ForeignKey("credentials.id"), nullable=False)
    bot_profile_id = Column(UUID(as_uuid=True), ForeignKey("bot_profiles.id"), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FrontendManifest(Base):
    __tablename__ = "frontend_manifest"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    module = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    assets = Column(JSON, nullable=False)
    active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class UIComponent(Base):
    __tablename__ = "ui_components"

    id = Column(String(50), primary_key=True)
    component_type = Column(String(50), nullable=False)
    default_props = Column(JSON, default={})


class UITheme(Base):
    __tablename__ = "ui_themes"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True)
    primary_color = Column(String(7), default="#000000")
    secondary_color = Column(String(7), default="#FFFFFF")
    accent_color = Column(String(7), default="#CCCCCC")
    dark_mode = Column(Boolean, default=False)
    logo_url = Column(String)


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    source = Column(String(50))  # 'frontend' o 'backend'
    message = Column(Text)
    stack_trace = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
