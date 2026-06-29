import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class BotProfile(Base):
    __tablename__ = "bot_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    capabilities = Column(
        JSON, default={"can_sell": False, "can_manage_stock": False, "can_process_payments": False}
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BotNode(Base):
    __tablename__ = "bot_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    bot_profile_id = Column(UUID(as_uuid=True), ForeignKey("bot_profiles.id"), nullable=False)
    name = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)


class BotOption(Base):
    __tablename__ = "bot_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    node_id = Column(UUID(as_uuid=True), ForeignKey("bot_nodes.id"), nullable=False)
    bot_profile_id = Column(UUID(as_uuid=True), ForeignKey("bot_profiles.id"), nullable=False)
    label = Column(String(100), nullable=False)
    next_node_id = Column(UUID(as_uuid=True))
    action = Column(String(100))


class BotSettings(Base):
    __tablename__ = "bot_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    bot_profile_id = Column(UUID(as_uuid=True), ForeignKey("bot_profiles.id"), nullable=False)
    bot_name = Column(String(100))
    welcome_message = Column(Text)
    farewell_message = Column(Text)
    handoff_message = Column(Text)
    support_email = Column(String(255))
    is_global_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WhatsappConversation(Base):
    __tablename__ = "whatsapp_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    phone_number = Column(String(50), nullable=False)
    sender_type = Column(String(50))
    message = Column(Text)
    message_type = Column(String(50))
    current_node_id = Column(UUID(as_uuid=True))
    bot_profile_id = Column(UUID(as_uuid=True), ForeignKey("bot_profiles.id"))
    is_bot_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="sent")
