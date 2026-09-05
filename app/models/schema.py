from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.types import TIMESTAMP
from datetime import datetime, timezone
import enum

from app.core.database import Base

# Using BigInt generated always as identity for PKs as per Postgres skill guidelines
from sqlalchemy import Identity, BigInteger, Enum

class EventType(enum.Enum):
    payment_failure = "payment_failure"
    checkout_abandonment = "checkout_abandonment"
    b2b_overdue_invoice = "b2b_overdue_invoice"

class EventStatus(enum.Enum):
    open = "open"
    in_progress = "in_progress"
    recovered = "recovered"
    unrecovered = "unrecovered"
    escalated = "escalated"

class RecoveryActionType(enum.Enum):
    retry = "retry"
    nudge = "nudge"
    escalate = "escalate"
    block = "block"

class RecoveryOutcome(enum.Enum):
    success = "success"
    failure = "failure"
    pending = "pending"

class RevenueEvent(Base):
    __tablename__ = "revenue_event"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    batch_id = Column(String, nullable=False, index=True)
    type = Column(Enum(EventType), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    context = Column(JSON, nullable=False, server_default='{}')
    detected_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(Enum(EventStatus), nullable=False, default=EventStatus.open)

    diagnosis = relationship("Diagnosis", back_populates="event", uselist=False)
    policy_decisions = relationship("PolicyDecision", back_populates="event")
    recovery_actions = relationship("RecoveryAction", back_populates="event")

class Diagnosis(Base):
    __tablename__ = "diagnosis"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    event_id = Column(BigInteger, ForeignKey("revenue_event.id"), nullable=False, unique=True)
    root_cause = Column(String, nullable=False)
    recommended_action = Column(String, nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    rationale = Column(String, nullable=False)
    model_used = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("RevenueEvent", back_populates="diagnosis")

class PolicyDecision(Base):
    __tablename__ = "policy_decision"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    event_id = Column(BigInteger, ForeignKey("revenue_event.id"), nullable=False, index=True)
    action_proposed = Column(String, nullable=False)
    action_approved = Column(Boolean, nullable=False)
    rule_triggered = Column(String, nullable=False)
    rationale = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("RevenueEvent", back_populates="policy_decisions")

class RecoveryAction(Base):
    __tablename__ = "recovery_action"
    __table_args__ = (
        UniqueConstraint('event_id', 'action_type', 'attempt_number', name='uq_recovery_action_event_type_attempt'),
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    event_id = Column(BigInteger, ForeignKey("revenue_event.id"), nullable=False, index=True)
    action_type = Column(Enum(RecoveryActionType), nullable=False)
    executed_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    outcome = Column(Enum(RecoveryOutcome), nullable=False, default=RecoveryOutcome.pending)
    attempt_number = Column(Integer, nullable=False, default=1)
    context = Column(JSON, nullable=False, server_default='{}')

    event = relationship("RevenueEvent", back_populates="recovery_actions")
