from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    contact_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="new",
        index=True,
    )

    value: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    probability: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    expected_close_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )