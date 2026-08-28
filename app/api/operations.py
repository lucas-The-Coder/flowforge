from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.automation import Automation
from app.models.calendar_event import CalendarEvent
from app.models.company import Company
from app.models.contact import Contact
from app.models.email_message import EmailMessage
from app.models.task import Task
from app.services.auth import get_current_user
from app.services.workspace_auth import get_current_workspace
from app.templates import templates


router = APIRouter(
    tags=["Operations"],
)


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


AUTOMATION_TRIGGERS = {
    "email_received": "Email Received",
    "lead_created": "Lead Created",
    "lead_status_changed": "Lead Status Changed",
    "task_overdue": "Task Overdue",
    "calendar_event_created": "Calendar Event Created",
    "contact_created": "Contact Created",
}


AUTOMATION_ACTIONS = {
    "create_task": "Create Task",
    "send_email": "Send Email",
    "create_activity": "Create Activity",
    "update_lead": "Update Lead",
}


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

    event_count = db.scalar(
        select(func.count())
        .select_from(CalendarEvent)
        .where(CalendarEvent.workspace_id == workspace.id)
    ) or 0

    email_count = db.scalar(
        select(func.count())
        .select_from(EmailMessage)
        .where(EmailMessage.workspace_id == workspace.id)
    ) or 0

    automation_count = db.scalar(
        select(func.count())
        .select_from(Automation)
        .where(Automation.workspace_id == workspace.id)
    ) or 0

    return templates.TemplateResponse(
        request=request,
        name="operations.html",
        context={
            "title": "Operations",
            "header": "Operations",
            "header_subtitle": "Run your business from one place",
            "user": user,
            "workspace": workspace,
            "task_count": task_count,
            "event_count": event_count,
            "email_count": email_count,
            "automation_count": automation_count,
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
        .where(Task.workspace_id == workspace.id)
        .order_by(
            Task.due_date.asc().nulls_last(),
            Task.priority.desc(),
            Task.created_at.desc(),
        )
    ).all()

    companies = db.scalars(
        select(Company)
        .where(Company.workspace_id == workspace.id)
        .order_by(Company.name.asc())
    ).all()

    contacts = db.scalars(
        select(Contact)
        .where(Contact.workspace_id == workspace.id)
        .order_by(
            Contact.last_name.asc(),
            Contact.first_name.asc(),
        )
    ).all()

    company_map = {
        company.id: company.name
        for company in companies
    }

    contact_map = {
        contact.id: f"{contact.first_name} {contact.last_name}"
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
        .where(Company.workspace_id == workspace.id)
        .order_by(Company.name.asc())
    ).all()

    contacts = db.scalars(
        select(Contact)
        .where(Contact.workspace_id == workspace.id)
        .order_by(
            Contact.last_name.asc(),
            Contact.first_name.asc(),
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
            "statuses": TASK_STATUSES,
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task title is required.",
        )

    if priority not in TASK_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task priority.",
        )

    parsed_due_date = None

    if due_date:
        try:
            parsed_due_date = date.fromisoformat(due_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid due date.",
            ) from exc

    validated_company_id = None

    if company_id:
        company = db.scalar(
            select(Company).where(
                Company.id == company_id,
                Company.workspace_id == workspace.id,
            )
        )

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found in this workspace.",
            )

        validated_company_id = company.id

    validated_contact_id = None

    if contact_id:
        contact = db.scalar(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.workspace_id == workspace.id,
            )
        )

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found in this workspace.",
            )

        validated_contact_id = contact.id

    task = Task(
        workspace_id=workspace.id,
        company_id=validated_company_id,
        contact_id=validated_contact_id,
        title=title,
        description=description.strip() if description else None,
        status="todo",
        priority=priority,
        due_date=parsed_due_date,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return RedirectResponse(
        url="/tasks",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/tasks/{task_id}/status")
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    if status_name not in TASK_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task status.",
        )

    task.status = status_name

    if status_name == "done":
        task.completed_at = datetime.now(timezone.utc)
    else:
        task.completed_at = None

    db.commit()

    return RedirectResponse(
        url="/tasks",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    

@router.post("/tasks/{task_id}/priority")
def update_task_priority(
    task_id: str,
    priority: int = Form(...),
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    if priority not in TASK_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task priority.",
        )

    task.priority = priority

    db.commit()

    return RedirectResponse(
        url="/tasks",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/tasks/{task_id}/delete")
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    db.delete(task)
    db.commit()

    return RedirectResponse(
        url="/tasks",
        status_code=status.HTTP_303_SEE_OTHER,
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
        .where(CalendarEvent.workspace_id == workspace.id)
        .order_by(CalendarEvent.start_at.asc())
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
        .where(EmailMessage.workspace_id == workspace.id)
        .order_by(EmailMessage.received_at.desc())
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
        .where(Automation.workspace_id == workspace.id)
        .order_by(Automation.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="automations.html",
        context={
            "title": "Automations",
            "header": "Automations",
            "header_subtitle": "Automate repetitive business work",
            "user": user,
            "workspace": workspace,
            "automations": automations,
        },
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
    task_count = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.workspace_id == workspace.id)
    ) or 0

    email_count = db.scalar(
        select(func.count())
        .select_from(EmailMessage)
        .where(EmailMessage.workspace_id == workspace.id)
    ) or 0

    automation_count = db.scalar(
        select(func.count())
        .select_from(Automation)
        .where(Automation.workspace_id == workspace.id)
    ) or 0

    company_count = db.scalar(
        select(func.count())
        .select_from(Company)
        .where(Company.workspace_id == workspace.id)
    ) or 0

    contact_count = db.scalar(
        select(func.count())
        .select_from(Contact)
        .where(Contact.workspace_id == workspace.id)
    ) or 0

    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={
            "title": "Analytics",
            "header": "Analytics",
            "header_subtitle": "Business performance overview",
            "user": user,
            "workspace": workspace,
            "task_count": task_count,
            "email_count": email_count,
            "automation_count": automation_count,
            "company_count": company_count,
            "contact_count": contact_count,
        },
    )