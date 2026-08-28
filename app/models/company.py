from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    industry: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
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