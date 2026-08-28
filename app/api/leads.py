from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.user import User
from app.services.auth import get_current_user
from app.services.workspace_auth import get_current_workspace
from app.templates import templates


router = APIRouter(
    tags=["Leads"],
)


LEAD_STATUSES = (
    "new",
    "contacted",
    "qualified",
    "proposal",
    "won",
    "lost",
)


LEAD_STATUS_LABELS = {
    "new": "New",
    "contacted": "Contacted",
    "qualified": "Qualified",
    "proposal": "Proposal",
    "won": "Won",
    "lost": "Lost",
}


LEAD_STATUS_PROBABILITIES = {
    "new": 10,
    "contacted": 25,
    "qualified": 50,
    "proposal": 75,
    "won": 100,
    "lost": 0,
}


@router.get(
    "/leads",
    response_class=HTMLResponse,
)
def leads_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    leads = db.scalars(
        select(Lead)
        .where(
            Lead.workspace_id == workspace.id
        )
        .order_by(
            Lead.created_at.desc()
        )
    ).all()

    companies = db.scalars(
        select(Company)
        .where(
            Company.workspace_id == workspace.id
        )
        .order_by(
            Company.name.asc()
        )
    ).all()

    contacts = db.scalars(
        select(Contact)
        .where(
            Contact.workspace_id == workspace.id
        )
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
        contact.id: (
            f"{contact.first_name} {contact.last_name}"
        )
        for contact in contacts
    }

    grouped_leads = {
        status_name: []
        for status_name in LEAD_STATUSES
    }

    for lead in leads:
        if lead.status not in grouped_leads:
            grouped_leads["new"].append(lead)
        else:
            grouped_leads[lead.status].append(lead)

    total_pipeline_value = sum(
        (
            Decimal(str(lead.value))
            for lead in leads
            if lead.value is not None
            and lead.status not in {"won", "lost"}
        ),
        Decimal("0"),
    )

    weighted_pipeline_value = sum(
        (
            Decimal(str(lead.value))
            * Decimal(str(lead.probability))
            / Decimal("100")
            for lead in leads
            if lead.value is not None
            and lead.status not in {"won", "lost"}
        ),
        Decimal("0"),
    )

    return templates.TemplateResponse(
        request=request,
        name="leads.html",
        context={
            "title": "Sales Pipeline",
            "header": "Sales Pipeline",
            "header_subtitle": workspace.name,
            "user": user,
            "workspace": workspace,
            "leads": leads,
            "grouped_leads": grouped_leads,
            "companies": companies,
            "contacts": contacts,
            "company_map": company_map,
            "contact_map": contact_map,
            "status_labels": LEAD_STATUS_LABELS,
            "total_pipeline_value": total_pipeline_value,
            "weighted_pipeline_value": weighted_pipeline_value,
        },
    )


@router.get(
    "/leads/new",
    response_class=HTMLResponse,
)
def new_lead_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    companies = db.scalars(
        select(Company)
        .where(
            Company.workspace_id == workspace.id
        )
        .order_by(
            Company.name.asc()
        )
    ).all()

    contacts = db.scalars(
        select(Contact)
        .where(
            Contact.workspace_id == workspace.id
        )
        .order_by(
            Contact.last_name.asc(),
            Contact.first_name.asc(),
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="lead_form.html",
        context={
            "title": "New Lead",
            "header": "New Lead",
            "header_subtitle": "Add an opportunity to your pipeline",
            "user": user,
            "workspace": workspace,
            "lead": None,
            "companies": companies,
            "contacts": contacts,
            "status_options": LEAD_STATUSES,
            "status_labels": LEAD_STATUS_LABELS,
        },
    )


@router.post(
    "/leads",
)
def create_lead(
    title: str = Form(...),
    status_name: str = Form("new"),
    value: str | None = Form(None),
    probability: str | None = Form(None),
    expected_close_date: str | None = Form(None),
    company_id: str | None = Form(None),
    contact_id: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    title = title.strip()
    status_name = status_name.strip().lower()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead title is required.",
        )

    if status_name not in LEAD_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lead status.",
        )

    parsed_value = None

    if value:
        try:
            parsed_value = Decimal(value)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead value must be a valid number.",
            )

        if parsed_value < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead value cannot be negative.",
            )

    parsed_probability = (
        LEAD_STATUS_PROBABILITIES[status_name]
        if probability is None or probability == ""
        else int(probability)
    )

    if parsed_probability < 0 or parsed_probability > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Probability must be between 0 and 100.",
        )

    parsed_close_date = None

    if expected_close_date:
        try:
            parsed_close_date = date.fromisoformat(
                expected_close_date
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid expected close date.",
            )

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

    if (
        validated_company_id
        and validated_contact_id
    ):
        linked_contact = db.scalar(
            select(Contact).where(
                Contact.id == validated_contact_id,
                Contact.company_id == validated_company_id,
                Contact.workspace_id == workspace.id,
            )
        )

        if not linked_contact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected contact does not belong to the selected company.",
            )

    lead = Lead(
        workspace_id=workspace.id,
        company_id=validated_company_id,
        contact_id=validated_contact_id,
        title=title,
        status=status_name,
        value=parsed_value,
        probability=parsed_probability,
        expected_close_date=parsed_close_date,
        notes=notes.strip() if notes else None,
    )

    db.add(lead)
    db.commit()

    return RedirectResponse(
        url="/leads",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/leads/{lead_id}/status",
)
def update_lead_status(
    lead_id: str,
    status_name: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    lead = db.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.workspace_id == workspace.id,
        )
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found.",
        )

    status_name = status_name.strip().lower()

    if status_name not in LEAD_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lead status.",
        )

    lead.status = status_name
    lead.probability = LEAD_STATUS_PROBABILITIES[status_name]

    db.commit()

    return RedirectResponse(
        url="/leads",
        status_code=status.HTTP_303_SEE_OTHER,
    )