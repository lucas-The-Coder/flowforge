from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.activity import Activity
from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User
from app.services.auth import get_current_user
from app.services.workspace_auth import get_current_workspace
from app.templates import templates


router = APIRouter(
    tags=["CRM"],
)


# ============================================================
# COMPANIES
# ============================================================

@router.get(
    "/companies",
    response_class=HTMLResponse,
)
def companies_page(
    request: Request,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    query = select(Company).where(
        Company.workspace_id == workspace.id
    )

    if search:
        search_term = f"%{search.strip()}%"

        query = query.where(
            or_(
                Company.name.ilike(search_term),
                Company.industry.ilike(search_term),
                Company.email.ilike(search_term),
            )
        )

    companies = db.scalars(
        query.order_by(Company.name.asc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="companies.html",
        context={
            "title": "Companies",
            "header": "Companies",
            "header_subtitle": "Manage your business relationships",
            "user": user,
            "workspace": workspace,
            "companies": companies,
            "search": search or "",
        },
    )


@router.get(
    "/companies/new",
    response_class=HTMLResponse,
)
def new_company_page(
    request: Request,
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    return templates.TemplateResponse(
        request=request,
        name="company_form.html",
        context={
            "title": "New Company",
            "header": "New Company",
            "header_subtitle": "Add a company to your CRM",
            "user": user,
            "workspace": workspace,
            "company": None,
        },
    )


@router.post("/companies")
def create_company(
    name: str = Form(...),
    industry: str | None = Form(None),
    website: str | None = Form(None),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    name = name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name is required.",
        )

    company = Company(
        workspace_id=workspace.id,
        name=name,
        industry=industry.strip() if industry else None,
        website=website.strip() if website else None,
        phone=phone.strip() if phone else None,
        email=email.strip().lower() if email else None,
        notes=notes.strip() if notes else None,
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return RedirectResponse(
        url=f"/companies/{company.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/companies/{company_id}/edit",
    response_class=HTMLResponse,
)
def edit_company_page(
    company_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.workspace_id == workspace.id,
        )
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    return templates.TemplateResponse(
        request=request,
        name="company_form.html",
        context={
            "title": f"Edit {company.name}",
            "header": "Edit Company",
            "header_subtitle": "Update company information",
            "user": user,
            "workspace": workspace,
            "company": company,
        },
    )


@router.post(
    "/companies/{company_id}/edit",
)
def update_company(
    company_id: str,
    name: str = Form(...),
    industry: str | None = Form(None),
    website: str | None = Form(None),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.workspace_id == workspace.id,
        )
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    name = name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name is required.",
        )

    company.name = name
    company.industry = industry.strip() if industry else None
    company.website = website.strip() if website else None
    company.phone = phone.strip() if phone else None
    company.email = email.strip().lower() if email else None
    company.notes = notes.strip() if notes else None

    db.commit()

    return RedirectResponse(
        url=f"/companies/{company.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/companies/{company_id}",
    response_class=HTMLResponse,
)
def company_detail(
    company_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.workspace_id == workspace.id,
        )
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    contacts = db.scalars(
        select(Contact)
        .where(
            Contact.company_id == company.id,
            Contact.workspace_id == workspace.id,
        )
        .order_by(
            Contact.last_name.asc(),
            Contact.first_name.asc(),
        )
    ).all()

    activities = db.scalars(
        select(Activity)
        .where(
            Activity.company_id == company.id,
            Activity.workspace_id == workspace.id,
        )
        .order_by(
            Activity.occurred_at.desc()
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="company_detail.html",
        context={
            "title": company.name,
            "header": company.name,
            "header_subtitle": "Company details",
            "user": user,
            "workspace": workspace,
            "company": company,
            "contacts": contacts,
            "activities": activities,
        },
    )


@router.post(
    "/companies/{company_id}/delete",
)
def delete_company(
    company_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.workspace_id == workspace.id,
        )
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    db.delete(company)
    db.commit()

    return RedirectResponse(
        url="/companies",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/companies/{company_id}/activities",
)
def create_company_activity(
    company_id: str,
    activity_type: str = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.workspace_id == workspace.id,
        )
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    allowed_types = {
        "note",
        "call",
        "meeting",
        "email",
        "task",
    }

    activity_type = activity_type.strip().lower()

    if activity_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activity type.",
        )

    title = title.strip()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activity title is required.",
        )

    activity = Activity(
        workspace_id=workspace.id,
        company_id=company.id,
        contact_id=None,
        activity_type=activity_type,
        title=title,
        description=description.strip() if description else None,
        occurred_at=datetime.now(timezone.utc),
    )

    db.add(activity)
    db.commit()

    return RedirectResponse(
        url=f"/companies/{company.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ============================================================
# CONTACTS
# ============================================================

@router.get(
    "/contacts",
    response_class=HTMLResponse,
)
def contacts_page(
    request: Request,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    query = select(Contact).where(
        Contact.workspace_id == workspace.id
    )

    if search:
        search_term = f"%{search.strip()}%"

        query = query.where(
            or_(
                Contact.first_name.ilike(search_term),
                Contact.last_name.ilike(search_term),
                Contact.email.ilike(search_term),
                Contact.job_title.ilike(search_term),
            )
        )

    contacts = db.scalars(
        query.order_by(
            Contact.last_name.asc(),
            Contact.first_name.asc(),
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

    company_map = {
        company.id: company.name
        for company in companies
    }

    return templates.TemplateResponse(
        request=request,
        name="contacts.html",
        context={
            "title": "Contacts",
            "header": "Contacts",
            "header_subtitle": "Manage your customer contacts",
            "user": user,
            "workspace": workspace,
            "contacts": contacts,
            "companies": companies,
            "company_map": company_map,
            "search": search or "",
        },
    )


@router.get(
    "/contacts/new",
    response_class=HTMLResponse,
)
def new_contact_page(
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

    return templates.TemplateResponse(
        request=request,
        name="contact_form.html",
        context={
            "title": "New Contact",
            "header": "New Contact",
            "header_subtitle": "Add a contact to your CRM",
            "user": user,
            "workspace": workspace,
            "contact": None,
            "companies": companies,
        },
    )


@router.post(
    "/contacts",
)
def create_contact(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str | None = Form(None),
    phone: str | None = Form(None),
    job_title: str | None = Form(None),
    company_id: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    first_name = first_name.strip()
    last_name = last_name.strip()

    if not first_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name is required.",
        )

    if not last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last name is required.",
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

    contact = Contact(
        workspace_id=workspace.id,
        company_id=validated_company_id,
        first_name=first_name,
        last_name=last_name,
        email=email.strip().lower() if email else None,
        phone=phone.strip() if phone else None,
        job_title=job_title.strip() if job_title else None,
        notes=notes.strip() if notes else None,
    )

    db.add(contact)
    db.commit()
    db.refresh(contact)

    return RedirectResponse(
        url=f"/contacts/{contact.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/contacts/{contact_id}/edit",
    response_class=HTMLResponse,
)
def edit_contact_page(
    contact_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    contact = db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.workspace_id == workspace.id,
        )
    )

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found.",
        )

    companies = db.scalars(
        select(Company)
        .where(
            Company.workspace_id == workspace.id
        )
        .order_by(
            Company.name.asc()
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="contact_form.html",
        context={
            "title": "Edit Contact",
            "header": "Edit Contact",
            "header_subtitle": "Update contact information",
            "user": user,
            "workspace": workspace,
            "contact": contact,
            "companies": companies,
        },
    )


@router.post(
    "/contacts/{contact_id}/edit",
)
def update_contact(
    contact_id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str | None = Form(None),
    phone: str | None = Form(None),
    job_title: str | None = Form(None),
    company_id: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    contact = db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.workspace_id == workspace.id,
        )
    )

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found.",
        )

    first_name = first_name.strip()
    last_name = last_name.strip()

    if not first_name or not last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name and last name are required.",
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

    contact.first_name = first_name
    contact.last_name = last_name
    contact.email = email.strip().lower() if email else None
    contact.phone = phone.strip() if phone else None
    contact.job_title = job_title.strip() if job_title else None
    contact.company_id = validated_company_id
    contact.notes = notes.strip() if notes else None

    db.commit()

    return RedirectResponse(
        url=f"/contacts/{contact.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/contacts/{contact_id}",
    response_class=HTMLResponse,
)
def contact_detail(
    contact_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    contact = db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.workspace_id == workspace.id,
        )
    )

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found.",
        )

    company = None

    if contact.company_id:
        company = db.scalar(
            select(Company).where(
                Company.id == contact.company_id,
                Company.workspace_id == workspace.id,
            )
        )

    activities = db.scalars(
        select(Activity)
        .where(
            Activity.contact_id == contact.id,
            Activity.workspace_id == workspace.id,
        )
        .order_by(
            Activity.occurred_at.desc()
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="contact_detail.html",
        context={
            "title": f"{contact.first_name} {contact.last_name}",
            "header": f"{contact.first_name} {contact.last_name}",
            "header_subtitle": "Contact details",
            "user": user,
            "workspace": workspace,
            "contact": contact,
            "company": company,
            "activities": activities,
        },
    )


@router.post(
    "/contacts/{contact_id}/delete",
)
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    contact = db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.workspace_id == workspace.id,
        )
    )

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found.",
        )

    db.delete(contact)
    db.commit()

    return RedirectResponse(
        url="/contacts",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/contacts/{contact_id}/activities",
)
def create_contact_activity(
    contact_id: str,
    activity_type: str = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    contact = db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.workspace_id == workspace.id,
        )
    )

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found.",
        )

    allowed_types = {
        "note",
        "call",
        "meeting",
        "email",
        "task",
    }

    activity_type = activity_type.strip().lower()

    if activity_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activity type.",
        )

    title = title.strip()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activity title is required.",
        )

    activity = Activity(
        workspace_id=workspace.id,
        contact_id=contact.id,
        company_id=contact.company_id,
        activity_type=activity_type,
        title=title,
        description=description.strip() if description else None,
        occurred_at=datetime.now(timezone.utc),
    )

    db.add(activity)
    db.commit()

    return RedirectResponse(
        url=f"/contacts/{contact.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ============================================================
# CRM JSON API
# ============================================================

@router.get("/api/crm/companies")
def api_list_companies(
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

    return [
        {
            "id": company.id,
            "name": company.name,
            "industry": company.industry,
            "website": company.website,
            "phone": company.phone,
            "email": company.email,
            "notes": company.notes,
        }
        for company in companies
    ]


@router.get("/api/crm/contacts")
def api_list_contacts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
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

    return [
        {
            "id": contact.id,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "phone": contact.phone,
            "job_title": contact.job_title,
            "company_id": contact.company_id,
            "notes": contact.notes,
        }
        for contact in contacts
    ]