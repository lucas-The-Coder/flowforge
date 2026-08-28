from datetime import date, datetime, timezone
from email.message import EmailMessage as SMTPMessage
import smtplib
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.activity import Activity
from app.models.automation import Automation
from app.models.automation_run import AutomationRun
from app.models.calendar_event import CalendarEvent
from app.models.company import Company
from app.models.contact import Contact
from app.models.email_message import EmailMessage
from app.models.lead import Lead
from app.models.task import Task
from app.services.auth import get_current_user
from app.services.workspace_auth import get_current_workspace
from app.templates import templates

router = APIRouter(tags=["Operations"])


TASK_STATUSES = {
    "todo": "To Do",
    "in_progress": "In Progress",
    "blocked": "Blocked",
    "done": "Done",
}

TASK_PRIORITIES = {
    1: "Low",
    2: "Normal",
    3: "High",
    4: "Urgent",
}

TRIGGERS = {
    "manual": "Manual",
    "email_received": "Email received",
    "lead_created": "Lead created",
    "lead_status_changed": "Lead status changed",
    "task_overdue": "Task overdue",
    "calendar_event_created": "Calendar event created",
    "contact_created": "Contact created",
}

ACTIONS = {
    "create_task": "Create task",
    "create_activity": "Create activity",
    "send_email": "Send email",
    "update_lead": "Update lead",
}


def parse_datetime(
    value: str,
    timezone_name: str = "Africa/Johannesburg",
) -> datetime:
    value = value.strip().replace("Z", "+00:00")

    dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=ZoneInfo(timezone_name)
        )

    return dt.astimezone(timezone.utc)


def validate_company(
    db: Session,
    company_id: str | None,
    workspace_id: str,
) -> str | None:
    if not company_id:
        return None

    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.workspace_id == workspace_id,
        )
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found in this workspace.",
        )

    return company.id


def validate_contact(
    db: Session,
    contact_id: str | None,
    workspace_id: str,
) -> str | None:
    if not contact_id:
        return None

    contact = db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.workspace_id == workspace_id,
        )
    )

    if not contact:
        raise HTTPException(
            status_code=404,
            detail="Contact not found in this workspace.",
        )

    return contact.id


# ============================================================
# OPERATIONS DASHBOARD
# ============================================================

@router.get(
    "/operations",
    response_class=HTMLResponse,
)
def operations_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    task_count = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.workspace_id == workspace.id)
    ) or 0

    open_task_count = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            Task.workspace_id == workspace.id,
            Task.status != "done",
        )
    ) or 0

    event_count = db.scalar(
        select(func.count())
        .select_from(CalendarEvent)
        .where(
            CalendarEvent.workspace_id == workspace.id
        )
    ) or 0

    email_count = db.scalar(
        select(func.count())
        .select_from(EmailMessage)
        .where(
            EmailMessage.workspace_id == workspace.id
        )
    ) or 0

    automation_count = db.scalar(
        select(func.count())
        .select_from(Automation)
        .where(
            Automation.workspace_id == workspace.id
        )
    ) or 0

    lead_count = db.scalar(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.workspace_id == workspace.id
        )
    ) or 0

    return templates.TemplateResponse(
        request=request,
        name="operations.html",
        context={
            "title": "Operations",
            "header": "Operations",
            "header_subtitle": workspace.name,
            "user": user,
            "workspace": workspace,
            "task_count": task_count,
            "open_task_count": open_task_count,
            "event_count": event_count,
            "email_count": email_count,
            "automation_count": automation_count,
            "lead_count": lead_count,
        },
    )


# ============================================================
# TASKS
# ============================================================

@router.get(
    "/tasks",
    response_class=HTMLResponse,
)
def tasks_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    tasks = db.scalars(
        select(Task)
        .where(
            Task.workspace_id == workspace.id
        )
        .order_by(
            Task.due_date.asc().nulls_last(),
            Task.priority.desc(),
            Task.created_at.desc(),
        )
    ).all()

    companies = db.scalars(
        select(Company)
        .where(
            Company.workspace_id == workspace.id
        )
        .order_by(Company.name)
    ).all()

    contacts = db.scalars(
        select(Contact)
        .where(
            Contact.workspace_id == workspace.id
        )
        .order_by(
            Contact.last_name,
            Contact.first_name,
        )
    ).all()

    company_map = {
        company.id: company.name
        for company in companies
    }

    contact_map = {
        contact.id:
        f"{contact.first_name} {contact.last_name}"
        for contact in contacts
    }

    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={
            "title": "Tasks",
            "header": "Tasks",
            "header_subtitle": "Manage work across your business",
            "user": user,
            "workspace": workspace,
            "tasks": tasks,
            "statuses": TASK_STATUSES,
            "priorities": TASK_PRIORITIES,
            "company_map": company_map,
            "contact_map": contact_map,
            "today": date.today(),
        },
    )


@router.get(
    "/tasks/new",
    response_class=HTMLResponse,
)
def new_task_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    companies = db.scalars(
        select(Company)
        .where(
            Company.workspace_id == workspace.id
        )
        .order_by(Company.name)
    ).all()

    contacts = db.scalars(
        select(Contact)
        .where(
            Contact.workspace_id == workspace.id
        )
        .order_by(
            Contact.last_name,
            Contact.first_name,
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="task_form.html",
        context={
            "title": "New Task",
            "header": "New Task",
            "header_subtitle": "Create a task",
            "user": user,
            "workspace": workspace,
            "task": None,
            "companies": companies,
            "contacts": contacts,
            "priorities": TASK_PRIORITIES,
        },
    )


@router.post("/tasks")
def create_task(
    title: str = Form(...),
    description: str | None = Form(None),
    priority: int = Form(2),
    due_date: str | None = Form(None),
    company_id: str | None = Form(None),
    contact_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    title = title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Task title is required.",
        )

    if priority not in TASK_PRIORITIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid task priority.",
        )

    try:
        parsed_due_date = (
            date.fromisoformat(due_date)
            if due_date
            else None
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid due date.",
        ) from exc

    task = Task(
        workspace_id=workspace.id,
        company_id=validate_company(
            db,
            company_id,
            workspace.id,
        ),
        contact_id=validate_contact(
            db,
            contact_id,
            workspace.id,
        ),
        title=title,
        description=(
            description.strip()
            if description
            else None
        ),
        status="todo",
        priority=priority,
        due_date=parsed_due_date,
    )

    db.add(task)
    db.commit()

    return RedirectResponse(
        "/tasks",
        status_code=303,
    )


@router.get(
    "/tasks/{task_id}/edit",
    response_class=HTMLResponse,
)
def edit_task_page(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    task = db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
        )
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    companies = db.scalars(
        select(Company)
        .where(
            Company.workspace_id == workspace.id
        )
        .order_by(Company.name)
    ).all()

    contacts = db.scalars(
        select(Contact)
        .where(
            Contact.workspace_id == workspace.id
        )
        .order_by(
            Contact.last_name,
            Contact.first_name,
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="task_form.html",
        context={
            "title": "Edit Task",
            "header": "Edit Task",
            "header_subtitle": "Update task",
            "user": user,
            "workspace": workspace,
            "task": task,
            "companies": companies,
            "contacts": contacts,
            "priorities": TASK_PRIORITIES,
        },
    )


@router.post(
    "/tasks/{task_id}/edit"
)
def update_task(
    task_id: str,
    title: str = Form(...),
    description: str | None = Form(None),
    priority: int = Form(2),
    due_date: str | None = Form(None),
    company_id: str | None = Form(None),
    contact_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    task = db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
        )
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    if not title.strip():
        raise HTTPException(
            status_code=400,
            detail="Task title is required.",
        )

    if priority not in TASK_PRIORITIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid priority.",
        )

    try:
        parsed_due_date = (
            date.fromisoformat(due_date)
            if due_date
            else None
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid due date.",
        ) from exc

    task.title = title.strip()
    task.description = (
        description.strip()
        if description
        else None
    )
    task.priority = priority
    task.due_date = parsed_due_date
    task.company_id = validate_company(
        db,
        company_id,
        workspace.id,
    )
    task.contact_id = validate_contact(
        db,
        contact_id,
        workspace.id,
    )

    db.commit()

    return RedirectResponse(
        "/tasks",
        status_code=303,
    )


@router.post(
    "/tasks/{task_id}/status"
)
def update_task_status(
    task_id: str,
    status_name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    task = db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
        )
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    if status_name not in TASK_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Invalid task status.",
        )

    task.status = status_name

    if status_name == "done":
        task.completed_at = datetime.now(
            timezone.utc
        )
    else:
        task.completed_at = None

    db.commit()

    return RedirectResponse(
        "/tasks",
        status_code=303,
    )


@router.post(
    "/tasks/{task_id}/delete"
)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    task = db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
        )
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    db.delete(task)
    db.commit()

    return RedirectResponse(
        "/tasks",
        status_code=303,
    )


# ============================================================
# CALENDAR
# ============================================================

@router.get(
    "/calendar",
    response_class=HTMLResponse,
)
def calendar_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    events = db.scalars(
        select(CalendarEvent)
        .where(
            CalendarEvent.workspace_id == workspace.id
        )
        .order_by(
            CalendarEvent.start_at.asc()
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="calendar.html",
        context={
            "title": "Calendar",
            "header": "Calendar",
            "header_subtitle": "Meetings and scheduled events",
            "user": user,
            "workspace": workspace,
            "events": events,
        },
    )


@router.get(
    "/calendar/new",
    response_class=HTMLResponse,
)
def new_calendar_event_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    companies = db.scalars(
        select(Company)
        .where(
            Company.workspace_id == workspace.id
        )
        .order_by(Company.name)
    ).all()

    contacts = db.scalars(
        select(Contact)
        .where(
            Contact.workspace_id == workspace.id
        )
        .order_by(
            Contact.last_name,
            Contact.first_name,
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="calendar_form.html",
        context={
            "title": "New Event",
            "header": "New Event",
            "header_subtitle": "Schedule a meeting",
            "user": user,
            "workspace": workspace,
            "companies": companies,
            "contacts": contacts,
        },
    )


@router.post("/calendar")
def create_calendar_event(
    title: str = Form(...),
    start_at: str = Form(...),
    end_at: str = Form(...),
    description: str | None = Form(None),
    location: str | None = Form(None),
    company_id: str | None = Form(None),
    contact_id: str | None = Form(None),
    meeting_url: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    if not title.strip():
        raise HTTPException(
            status_code=400,
            detail="Event title is required.",
        )

    try:
        start = parse_datetime(start_at)
        end = parse_datetime(end_at)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid date or time.",
        ) from exc

    if end <= start:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time.",
        )

    event = CalendarEvent(
        workspace_id=workspace.id,
        company_id=validate_company(
            db,
            company_id,
            workspace.id,
        ),
        contact_id=validate_contact(
            db,
            contact_id,
            workspace.id,
        ),
        title=title.strip(),
        description=(
            description.strip()
            if description
            else None
        ),
        location=(
            location.strip()
            if location
            else None
        ),
        start_at=start,
        end_at=end,
        timezone_name="Africa/Johannesburg",
        status="scheduled",
        meeting_url=(
            meeting_url.strip()
            if meeting_url
            else None
        ),
    )

    db.add(event)
    db.commit()

    return RedirectResponse(
        "/calendar",
        status_code=303,
    )


@router.post(
    "/calendar/{event_id}/delete"
)
def delete_calendar_event(
    event_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    event = db.scalar(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.workspace_id == workspace.id,
        )
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Calendar event not found.",
        )

    db.delete(event)
    db.commit()

    return RedirectResponse(
        "/calendar",
        status_code=303,
    )


# ============================================================
# EMAILS
# ============================================================

@router.get(
    "/emails",
    response_class=HTMLResponse,
)
def emails_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    emails = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.workspace_id == workspace.id
        )
        .order_by(
            EmailMessage.received_at.desc()
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="emails.html",
        context={
            "title": "Emails",
            "header": "Emails",
            "header_subtitle": "Business communication",
            "user": user,
            "workspace": workspace,
            "emails": emails,
        },
    )


@router.get(
    "/emails/new",
    response_class=HTMLResponse,
)
def new_email_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    contacts = db.scalars(
        select(Contact)
        .where(
            Contact.workspace_id == workspace.id
        )
        .order_by(
            Contact.last_name,
            Contact.first_name,
        )
    ).all()

    companies = db.scalars(
        select(Company)
        .where(
            Company.workspace_id == workspace.id
        )
        .order_by(Company.name)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="email_form.html",
        context={
            "title": "Compose Email",
            "header": "Compose Email",
            "header_subtitle": "Send a business email",
            "user": user,
            "workspace": workspace,
            "contacts": contacts,
            "companies": companies,
        },
    )


@router.post("/emails")
def create_email(
    recipient_email: str = Form(...),
    subject: str = Form(...),
    body_text: str = Form(...),
    contact_id: str | None = Form(None),
    company_id: str | None = Form(None),
    action: str = Form("draft"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    recipient_email = recipient_email.strip()
    subject = subject.strip()

    if not recipient_email:
        raise HTTPException(
            status_code=400,
            detail="Recipient email is required.",
        )

    if not subject:
        raise HTTPException(
            status_code=400,
            detail="Subject is required.",
        )

    if not body_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Email body is required.",
        )

    from_email = (
        settings.smtp_from_email
        or settings.smtp_username
        or user.email
    )

    email = EmailMessage(
        workspace_id=workspace.id,
        company_id=validate_company(
            db,
            company_id,
            workspace.id,
        ),
        contact_id=validate_contact(
            db,
            contact_id,
            workspace.id,
        ),
        direction="outbound",
        status="draft",
        provider=(
            "smtp"
            if settings.smtp_host
            else "local"
        ),
        sender_name=user.full_name,
        sender_email=from_email,
        recipient_email=recipient_email,
        subject=subject,
        body_text=body_text,
        received_at=datetime.now(timezone.utc),
    )

    db.add(email)
    db.commit()
    db.refresh(email)

    if action == "send":

        if not settings.smtp_host:
            raise HTTPException(
                status_code=400,
                detail=(
                    "SMTP is not configured. "
                    "Save the email as a draft instead."
                ),
            )

        smtp_message = SMTPMessage()

        smtp_message["From"] = from_email
        smtp_message["To"] = recipient_email
        smtp_message["Subject"] = subject

        smtp_message.set_content(body_text)

        try:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=20,
            ) as smtp:

                if settings.smtp_use_tls:
                    smtp.starttls()

                if settings.smtp_username:
                    smtp.login(
                        settings.smtp_username,
                        settings.smtp_password,
                    )

                smtp.send_message(
                    smtp_message
                )

            email.status = "sent"

            db.commit()

        except Exception as exc:

            email.status = "failed"

            db.commit()

            raise HTTPException(
                status_code=502,
                detail=f"Email delivery failed: {exc}",
            ) from exc

    return RedirectResponse(
        "/emails",
        status_code=303,
    )


@router.post(
    "/emails/{email_id}/delete"
)
def delete_email(
    email_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    email = db.scalar(
        select(EmailMessage).where(
            EmailMessage.id == email_id,
            EmailMessage.workspace_id == workspace.id,
        )
    )

    if not email:
        raise HTTPException(
            status_code=404,
            detail="Email not found.",
        )

    db.delete(email)
    db.commit()

    return RedirectResponse(
        "/emails",
        status_code=303,
    )


# ============================================================
# AUTOMATIONS
# ============================================================

@router.get(
    "/automations",
    response_class=HTMLResponse,
)
def automations_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    automations = db.scalars(
        select(Automation)
        .where(
            Automation.workspace_id == workspace.id
        )
        .order_by(
            Automation.created_at.desc()
        )
    ).all()

    runs = db.scalars(
        select(AutomationRun)
        .where(
            AutomationRun.workspace_id == workspace.id
        )
        .order_by(
            AutomationRun.started_at.desc()
        )
        .limit(25)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="automations.html",
        context={
            "title": "Automations",
            "header": "Automations",
            "header_subtitle": (
                "Automate repetitive business work"
            ),
            "user": user,
            "workspace": workspace,
            "automations": automations,
            "runs": runs,
            "triggers": TRIGGERS,
            "actions": ACTIONS,
        },
    )


@router.get(
    "/automations/new",
    response_class=HTMLResponse,
)
def new_automation_page(
    request: Request,
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    return templates.TemplateResponse(
        request=request,
        name="automation_form.html",
        context={
            "title": "New Automation",
            "header": "New Automation",
            "header_subtitle": "Create an automation rule",
            "user": user,
            "workspace": workspace,
            "triggers": TRIGGERS,
            "actions": ACTIONS,
        },
    )


@router.post("/automations")
def create_automation(
    name: str = Form(...),
    trigger_type: str = Form(...),
    action_type: str = Form(...),
    description: str | None = Form(None),
    trigger_config: str = Form("{}"),
    action_config: str = Form("{}"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    import json

    if not name.strip():
        raise HTTPException(
            status_code=400,
            detail="Automation name is required.",
        )

    if trigger_type not in TRIGGERS:
        raise HTTPException(
            status_code=400,
            detail="Invalid trigger.",
        )

    if action_type not in ACTIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid action.",
        )

    try:
        trigger_data = json.loads(
            trigger_config or "{}"
        )

        action_data = json.loads(
            action_config or "{}"
        )

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Automation configuration must be valid JSON.",
        ) from exc

    automation = Automation(
        workspace_id=workspace.id,
        name=name.strip(),
        description=(
            description.strip()
            if description
            else None
        ),
        trigger_type=trigger_type,
        action_type=action_type,
        trigger_config=trigger_data,
        action_config=action_data,
        is_active=True,
    )

    db.add(automation)
    db.commit()

    return RedirectResponse(
        "/automations",
        status_code=303,
    )


@router.post(
    "/automations/{automation_id}/toggle"
)
def toggle_automation(
    automation_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    automation = db.scalar(
        select(Automation).where(
            Automation.id == automation_id,
            Automation.workspace_id == workspace.id,
        )
    )

    if not automation:
        raise HTTPException(
            status_code=404,
            detail="Automation not found.",
        )

    automation.is_active = (
        not automation.is_active
    )

    db.commit()

    return RedirectResponse(
        "/automations",
        status_code=303,
    )


@router.post(
    "/automations/{automation_id}/delete"
)
def delete_automation(
    automation_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    automation = db.scalar(
        select(Automation).where(
            Automation.id == automation_id,
            Automation.workspace_id == workspace.id,
        )
    )

    if not automation:
        raise HTTPException(
            status_code=404,
            detail="Automation not found.",
        )

    db.delete(automation)
    db.commit()

    return RedirectResponse(
        "/automations",
        status_code=303,
    )


@router.post(
    "/automations/{automation_id}/run"
)
def run_automation(
    automation_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    automation = db.scalar(
        select(Automation).where(
            Automation.id == automation_id,
            Automation.workspace_id == workspace.id,
        )
    )

    if not automation:
        raise HTTPException(
            status_code=404,
            detail="Automation not found.",
        )

    run = AutomationRun(
        workspace_id=workspace.id,
        automation_id=automation.id,
        status="running",
        trigger_data={
            "manual": True
        },
        result_data={},
        started_at=datetime.now(timezone.utc),
    )

    db.add(run)
    db.flush()

    try:

        config = (
            automation.action_config
            or {}
        )

        if automation.action_type == "create_task":

            task = Task(
                workspace_id=workspace.id,
                company_id=config.get(
                    "company_id"
                ),
                contact_id=config.get(
                    "contact_id"
                ),
                title=config.get(
                    "title",
                    f"Automation: {automation.name}",
                ),
                description=config.get(
                    "description"
                ),
                status="todo",
                priority=int(
                    config.get(
                        "priority",
                        2,
                    )
                ),
                due_date=(
                    date.fromisoformat(
                        config["due_date"]
                    )
                    if config.get("due_date")
                    else None
                ),
            )

            db.add(task)

            run.result_data = {
                "created_task": task.title,
            }

        elif automation.action_type == "create_activity":

            activity = Activity(
                workspace_id=workspace.id,
                company_id=config.get(
                    "company_id"
                ),
                contact_id=config.get(
                    "contact_id"
                ),
                activity_type=config.get(
                    "activity_type",
                    "note",
                ),
                title=config.get(
                    "title",
                    automation.name,
                ),
                description=config.get(
                    "description"
                ),
                occurred_at=datetime.now(
                    timezone.utc
                ),
            )

            db.add(activity)

            run.result_data = {
                "created_activity": activity.title,
            }

        elif automation.action_type == "update_lead":

            lead = db.scalar(
                select(Lead).where(
                    Lead.id == config.get(
                        "lead_id"
                    ),
                    Lead.workspace_id == workspace.id,
                )
            )

            if not lead:
                raise RuntimeError(
                    "Lead specified by automation was not found."
                )

            if config.get("status"):
                lead.status = config["status"]

            if config.get(
                "probability"
            ) is not None:
                lead.probability = int(
                    config["probability"]
                )

            run.result_data = {
                "lead_id": lead.id,
                "status": lead.status,
            }

        elif automation.action_type == "send_email":

            if not settings.smtp_host:
                raise RuntimeError(
                    "SMTP is not configured."
                )

            from_email = (
                settings.smtp_from_email
                or settings.smtp_username
            )

            message = SMTPMessage()

            message["From"] = from_email
            message["To"] = config[
                "recipient_email"
            ]
            message["Subject"] = config.get(
                "subject",
                automation.name,
            )

            message.set_content(
                config.get(
                    "body",
                    "",
                )
            )

            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=20,
            ) as smtp:

                if settings.smtp_use_tls:
                    smtp.starttls()

                if settings.smtp_username:
                    smtp.login(
                        settings.smtp_username,
                        settings.smtp_password,
                    )

                smtp.send_message(
                    message
                )

            run.result_data = {
                "recipient": config[
                    "recipient_email"
                ],
            }

        else:

            raise RuntimeError(
                f"Unsupported action: "
                f"{automation.action_type}"
            )

        run.status = "success"

        run.completed_at = datetime.now(
            timezone.utc
        )

        automation.last_run_at = run.completed_at

        db.commit()

    except Exception as exc:

        db.rollback()

        run = db.scalar(
            select(AutomationRun).where(
                AutomationRun.id == run.id
            )
        )

        if run:

            run.status = "failed"

            run.error_message = str(exc)

            run.completed_at = datetime.now(
                timezone.utc
            )

            db.commit()

    return RedirectResponse(
        "/automations",
        status_code=303,
    )


# ============================================================
# ANALYTICS
# ============================================================

@router.get(
    "/analytics",
    response_class=HTMLResponse,
)
def analytics_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    company_count = db.scalar(
        select(func.count())
        .select_from(Company)
        .where(
            Company.workspace_id == workspace.id
        )
    ) or 0

    contact_count = db.scalar(
        select(func.count())
        .select_from(Contact)
        .where(
            Contact.workspace_id == workspace.id
        )
    ) or 0

    lead_count = db.scalar(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.workspace_id == workspace.id
        )
    ) or 0

    won_leads = db.scalar(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.workspace_id == workspace.id,
            Lead.status == "won",
        )
    ) or 0

    open_leads = db.scalar(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.workspace_id == workspace.id,
            Lead.status.not_in(
                ["won", "lost"]
            ),
        )
    ) or 0

    pipeline_value = db.scalar(
        select(
            func.coalesce(
                func.sum(Lead.value),
                0,
            )
        )
        .where(
            Lead.workspace_id == workspace.id,
            Lead.status.not_in(
                ["won", "lost"]
            ),
        )
    ) or 0

    task_count = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            Task.workspace_id == workspace.id
        )
    ) or 0

    completed_tasks = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            Task.workspace_id == workspace.id,
            Task.status == "done",
        )
    ) or 0

    event_count = db.scalar(
        select(func.count())
        .select_from(CalendarEvent)
        .where(
            CalendarEvent.workspace_id == workspace.id
        )
    ) or 0

    sent_email_count = db.scalar(
        select(func.count())
        .select_from(EmailMessage)
        .where(
            EmailMessage.workspace_id == workspace.id,
            EmailMessage.direction == "outbound",
            EmailMessage.status == "sent",
        )
    ) or 0

    automation_count = db.scalar(
        select(func.count())
        .select_from(Automation)
        .where(
            Automation.workspace_id == workspace.id
        )
    ) or 0

    successful_runs = db.scalar(
        select(func.count())
        .select_from(AutomationRun)
        .where(
            AutomationRun.workspace_id == workspace.id,
            AutomationRun.status == "success",
        )
    ) or 0

    failed_runs = db.scalar(
        select(func.count())
        .select_from(AutomationRun)
        .where(
            AutomationRun.workspace_id == workspace.id,
            AutomationRun.status == "failed",
        )
    ) or 0

    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={
            "title": "Analytics",
            "header": "Analytics",
            "header_subtitle": (
                "Business performance overview"
            ),
            "user": user,
            "workspace": workspace,
            "company_count": company_count,
            "contact_count": contact_count,
            "lead_count": lead_count,
            "won_leads": won_leads,
            "open_leads": open_leads,
            "pipeline_value": pipeline_value,
            "task_count": task_count,
            "completed_tasks": completed_tasks,
            "event_count": event_count,
            "sent_email_count": sent_email_count,
            "automation_count": automation_count,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
        },
    )