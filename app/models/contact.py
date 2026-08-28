from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

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

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    job_title: Mapped[str | None] = mapped_column(
        String(150),
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