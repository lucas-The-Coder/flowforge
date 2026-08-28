from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

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

    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="received",
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

    thread_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    message_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    sender_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    sender_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        index=True,
    )

    recipient_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    cc_emails: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    bcc_emails: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    subject: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    body_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    body_html: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )