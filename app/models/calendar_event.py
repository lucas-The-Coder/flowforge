from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "workspaces.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    company_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "companies.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    contact_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "contacts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    timezone_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Africa/Johannesburg",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="scheduled",
        index=True,
    )

    provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    meeting_url: Mapped[str | None] = mapped_column(
        String(1000),
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