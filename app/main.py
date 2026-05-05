import base64
import io
import qrcode
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import schemas
from .config import settings
from .database import Base, engine, get_db
from .deps import get_current_user, require_super_admin, require_admin, require_manager, require_cashier
from .models import (
    Advertisement,
    Category,
    Company,
    CompanyBankDetail,
    CompanyTermsCondition,
    Customer,
    Debt,
    Event,
    Expenditure,
    Product,
    ProductBatch,
    PurchaseOrder,
    Shift,
    StaffSalary,
    SubscriptionPlan,
    Supplier,
    Transaction,
    User,
)
from .schemas import (
    AdvertisementCreate,
    AdvertisementOut,
    CategoryIn,
    CompanyBankDetailCreate,
    CompanyBankDetailUpdate,
    CompanyCreate,
    CompanyOut,
    CompanyTermsConditionCreate,
    CompanyTermsConditionUpdate,
    CompanyUpdate,
    CustomerIn,
    CustomerUpdate,
    LoginIn,
    ProductIn,
    PurchaseOrderIn,
    SubscriptionPlanCreate,
    SubscriptionPlanOut,
    SubscriptionPlanUpdate,
    SupplierIn,
    TokenOut,
    TransactionIn,
    UserOut,
    UserCreate,
    UserUpdate,
)
from .security import create_access_token, hash_password, verify_password

# Ensure upload directory exists
import os
os.makedirs(settings.upload_dir, exist_ok=True)

app = FastAPI(title="SaaS POS API")

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def root():
    return {"message": "API is running successfully"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

def _coerce_datetimes(data: dict) -> dict:
    for k, v in data.items():
        if isinstance(v, str) and (
            k.endswith("_at") or 
            k.endswith("_date") or 
            k in ["date", "expiry", "start_time", "end_time", "payment_date"]
        ):
            try:
                # Handle ISO format with 'Z' or offset
                data[k] = datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                pass
    return data

def _resource_model(name: str):
    mapping = {
        "categories": Category,
        "products": Product,
        "customers": Customer,
        "suppliers": Supplier,
        "transactions": Transaction,
        "purchase_orders": PurchaseOrder,
        "events": Event,
        "staff_salaries": StaffSalary,
        "expenditures": Expenditure,
        "users": User,
    }
    if name not in mapping:
        raise HTTPException(status_code=404, detail="Resource not found")
    return mapping[name]

def _filter_valid_fields(data: dict, model) -> dict:
    valid_fields = {c.name for c in model.__table__.columns}
    return {k: v for k, v in data.items() if k in valid_fields}

# --- Specific Endpoints ---
@app.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email.ilike(payload.email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account disabled")
    
    token = create_access_token(subject=user.id, role=user.role, company_id=user.company_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "company_id": user.company_id
    }

@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    company = None
    if current_user.company_id:
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
    return {"user": current_user, "company": company}

@app.get("/tenant/company")
def get_company(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Company).filter(Company.id == current_user.company_id).first()

# Subscription endpoint for tenant
@app.get("/tenant/subscription/current")
def get_current_subscription(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current subscription details for the tenant's company"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get subscription plan details
    subscription_plan = None
    if company.subscription_plan_id:
        subscription_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == company.subscription_plan_id).first()
    elif company.subscription_plan:
        subscription_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name.ilike(company.subscription_plan)).first()
    
    # Calculate days remaining
    days_remaining = 0
    if company.subscription_expiry:
        days_remaining = (company.subscription_expiry - datetime.utcnow()).days
    
    # Check if subscription is active
    is_active = company.is_active and (company.subscription_expiry is None or company.subscription_expiry > datetime.utcnow())
    
    return {
        "company_id": company.id,
        "company_name": company.name,
        "subscription_plan": subscription_plan.name if subscription_plan else company.subscription_plan,
        "subscription_plan_id": company.subscription_plan_id,
        "subscription_expiry": company.subscription_expiry,
        "is_active": is_active,
        "days_remaining": days_remaining,
        "max_users": subscription_plan.max_users if subscription_plan else 10,
        "max_products": subscription_plan.max_products if subscription_plan else 1000,
        "max_locations": subscription_plan.max_locations if subscription_plan else 1,
        "features": subscription_plan.features if subscription_plan else [],
        "price": subscription_plan.price if subscription_plan else 0
    }

@app.get("/tenant/dashboard-stats")
def get_tenant_stats(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    # Very basic stats for now
    sales_count = db.query(Transaction).filter(Transaction.company_id == current_user.company_id, Transaction.type == "sale").count()
    total_revenue = db.query(Transaction).filter(Transaction.company_id == current_user.company_id, Transaction.type == "sale").all()
    revenue = sum(s.total for s in total_revenue)
    
    low_stock = db.query(Product).filter(Product.company_id == current_user.company_id, Product.quantity <= Product.min_stock).count()
    
    return {
        "salesCount": sales_count,
        "totalRevenue": revenue,
        "lowStockCount": low_stock,
        "totalProfit": revenue * 0.25,
        "profitMargin": 25.0,
        "totalPurchases": 0,
        "totalRefunds": 0,
        "returnRate": 0,
        "topCustomer": "N/A"
    }

@app.get("/tenant/finance/overview")
def get_finance_overview(period: str = "this_month", current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    now = datetime.utcnow()
    
    # Determine date range based on period
    if period == "this_month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == "this_year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == "last_month":
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = first_of_this_month - timedelta(seconds=1)
        start_date = end_date.replace(day=1)
    elif period == "last_year":
        start_date = now.replace(year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(year=now.year - 1, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    else:
        # Default to this_month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    
    # Query transactions for the period
    transactions = db.query(Transaction).filter(
        Transaction.company_id == current_user.company_id,
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.type == "sale"
    ).all()
    
    # Query purchase orders for the period
    purchase_orders = db.query(PurchaseOrder).filter(
        PurchaseOrder.company_id == current_user.company_id,
        PurchaseOrder.created_at >= start_date,
        PurchaseOrder.created_at <= end_date
    ).all()
    
    # Query expenditures for the period
    expenditures = db.query(Expenditure).filter(
        Expenditure.company_id == current_user.company_id,
        Expenditure.created_at >= start_date,
        Expenditure.created_at <= end_date
    ).all()
    
    # Calculate totals
    total_revenue = sum(t.total for t in transactions)
    total_costs = sum(po.total for po in purchase_orders) + sum(e.amount for e in expenditures)
    total_profit = total_revenue - total_costs
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_revenue": total_revenue,
        "total_costs": total_costs,
        "total_profit": total_profit,
        "profit_margin": profit_margin,
        "transaction_count": len(transactions),
        "average_transaction": total_revenue / len(transactions) if transactions else 0,
        "total_paid": sum(t.amount_paid for t in transactions),
        "total_due": sum(t.amount_due for t in transactions),
    }

@app.get("/admin/subscription-plans", response_model=list[SubscriptionPlanOut])
def list_subscription_plans(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(SubscriptionPlan).all()

@app.post("/admin/subscription-plans", response_model=SubscriptionPlanOut)
def create_subscription_plan(payload: SubscriptionPlanCreate, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    plan = SubscriptionPlan(
        id=str(uuid4()),
        name=payload.name,
        price=payload.price,
        max_users=payload.max_users,
        max_products=payload.max_products,
        max_locations=payload.max_locations,
        features=payload.features,
        is_active=payload.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@app.patch("/admin/subscription-plans/{plan_id}", response_model=SubscriptionPlanOut)
def update_subscription_plan(plan_id: str, payload: SubscriptionPlanUpdate, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan

@app.delete("/admin/subscription-plans/{plan_id}")
def delete_subscription_plan(plan_id: str, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    db.delete(plan)
    db.commit()
    return {"success": True}

@app.get("/admin/companies", response_model=list[CompanyOut])
def list_companies(_: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return db.query(Company).all()

# --- Admin User Management ---

@app.get("/admin/users", response_model=list[UserOut])
def list_admin_users(_: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return db.query(User).all()

@app.post("/admin/users", response_model=UserOut)
def create_admin_user(payload: UserCreate, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email.ilike(payload.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use")
    
    user = User(
        id=str(uuid4()),
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        company_id=payload.company_id,
        is_active=payload.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.patch("/admin/users/{user_id}", response_model=UserOut)
def update_admin_user(user_id: str, payload: UserUpdate, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
        
    for key, value in data.items():
        setattr(user, key, value)
        
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user

@app.delete("/admin/users/{user_id}")
def delete_admin_user(user_id: str, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"success": True}

@app.post("/admin/companies", response_model=CompanyOut)
def create_company(payload: CompanyCreate, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    # 0. Check if admin email already exists
    existing_user = db.query(User).filter(User.email.ilike(payload.admin_email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Admin email already in use")

    # 1. Create Company
    company_id = str(uuid4())
    company = Company(
        id=company_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        tax_id=payload.tax_id,
        logo=payload.logo,
        currency=payload.currency,
        currency_symbol=payload.currency_symbol,
        subscription_plan=payload.subscription_plan,
        subscription_expiry=payload.subscription_expiry,
        is_active=payload.is_active,
        types=payload.types,
        # Enhanced company details
        vrn_no=payload.vrn_no,
        tin_no=payload.tin_no,
        website=payload.website,
        physical_address=payload.physical_address,
        postal_address=payload.postal_address,
        country=payload.country,
        region=payload.region,
        city=payload.city,
        postal_code=payload.postal_code,
        business_license_no=payload.business_license_no,
        business_registration_no=payload.business_registration_no,
        business_type=payload.business_type,
        industry=payload.industry,
        year_established=payload.year_established,
        contact_person=payload.contact_person,
        contact_person_title=payload.contact_person_title,
        alternative_phone=payload.alternative_phone,
        fax=payload.fax,
        whatsapp=payload.whatsapp,
        facebook=payload.facebook,
        twitter=payload.twitter,
        instagram=payload.instagram,
        linkedin=payload.linkedin,
        document_prefix=payload.document_prefix,
        document_footer=payload.document_footer,
        document_header=payload.document_header,
        authorised_signatory=payload.authorised_signatory,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(company)
    
    # 2. Create Admin User for this company
    admin_user = User(
        id=str(uuid4()),
        company_id=company_id,
        email=payload.admin_email,
        name=payload.admin_name,
        password_hash=hash_password(payload.admin_password),
        role="admin",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(admin_user)
    
    # 3. Create Bank Details
    for bank_detail in payload.bank_details:
        bank = CompanyBankDetail(
            id=str(uuid4()),
            company_id=company_id,
            bank_name=bank_detail.bank_name,
            account_name=bank_detail.account_name,
            account_number=bank_detail.account_number,
            branch_name=bank_detail.branch_name,
            branch_code=bank_detail.branch_code,
            swift_code=bank_detail.swift_code,
            iban=bank_detail.iban,
            routing_number=bank_detail.routing_number,
            sort_code=bank_detail.sort_code,
            bank_address=bank_detail.bank_address,
            mobile_money_name=bank_detail.mobile_money_name,
            mobile_money_number=bank_detail.mobile_money_number,
            is_primary=bank_detail.is_primary,
            is_active=bank_detail.is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(bank)
    
    # 4. Create Terms & Conditions
    for terms in payload.terms_conditions:
        condition = CompanyTermsCondition(
            id=str(uuid4()),
            company_id=company_id,
            document_type=terms.document_type,
            title=terms.title,
            terms_text=terms.terms_text,
            payment_terms=terms.payment_terms,
            delivery_terms=terms.delivery_terms,
            warranty_terms=terms.warranty_terms,
            return_policy=terms.return_policy,
            late_payment_terms=terms.late_payment_terms,
            cancellation_policy=terms.cancellation_policy,
            is_active=terms.is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(condition)
    
    db.commit()
    db.refresh(company)
    return company

@app.get("/admin/companies/{company_id}", response_model=CompanyOut)
def get_company_admin(company_id: str, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@app.delete("/admin/companies/{company_id}")
def delete_company(company_id: str, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()
    return {"success": True}

@app.post("/admin/companies/{company_id}/assign-subscription")
def assign_company_subscription(company_id: str, payload: dict, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    plan_id = payload.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id is required")

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    expiry = payload.get("subscription_expiry")
    if expiry:
        try:
            expiry_date = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid subscription_expiry format") from exc
    else:
        expiry_date = datetime.utcnow() + timedelta(days=30)

    company.subscription_plan_id = plan.id
    company.subscription_plan = plan.name.lower()
    company.subscription_expiry = expiry_date
    company.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(company)
    return company

@app.patch("/admin/companies/{company_id}", response_model=CompanyOut)
def update_company(company_id: str, payload: CompanyUpdate, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    company.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(company)
    return company

@app.post("/admin/companies/logo-upload")
async def upload_company_logo(
    file: UploadFile = File(...),
    company_id: str = Form(...),
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Super admin endpoint to upload logo for any company
    """
    # Find the company
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Validate file format
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use PNG, JPG, JPEG, WEBP, or SVG")
    
    # Check file size (max 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Max file size is 2MB")
    
    # Delete old logo file if it exists
    if company.logo and company.logo.startswith("/uploads/"):
        old_logo_path = Path(settings.upload_dir) / Path(company.logo).name
        if old_logo_path.exists():
            try:
                old_logo_path.unlink()
            except Exception:
                pass
    
    # Save new file
    filename = f"company_logo_{company_id}_{uuid4()}{ext}"
    save_path = Path(settings.upload_dir) / filename
    save_path.write_bytes(content)
    
    # Update company logo
    company.logo = f"/uploads/{filename}"
    company.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(company)
    
    return {
        "success": True,
        "message": "Company logo uploaded successfully",
        "logo_url": f"/uploads/{filename}",
        "company_id": company_id,
        "company_name": company.name
    }

@app.post("/tenant/company/logo-upload")
async def upload_tenant_company_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tenant endpoint for company admins/managers to upload their own company logo
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned to your account")
    
    # Check if user has permission (admin or manager)
    if current_user.role not in ["admin", "manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and managers can upload company logos")
    
    # Find the company
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Validate file format
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use PNG, JPG, JPEG, WEBP, or SVG")
    
    # Check file size (max 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Max file size is 2MB")
    
    # Delete old logo file if it exists and is not a default
    if company.logo and company.logo.startswith("/uploads/"):
        old_logo_path = Path(settings.upload_dir) / Path(company.logo).name
        if old_logo_path.exists():
            try:
                old_logo_path.unlink()
            except Exception:
                pass
    
    # Save new file
    filename = f"company_logo_{current_user.company_id}_{uuid4()}{ext}"
    save_path = Path(settings.upload_dir) / filename
    save_path.write_bytes(content)
    
    # Update company logo
    company.logo = f"/uploads/{filename}"
    company.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(company)
    
    return {
        "success": True,
        "message": "Company logo uploaded successfully",
        "logo_url": f"/uploads/{filename}"
    }

@app.post("/admin/ads/upload")
async def upload_ad_media(
    file: UploadFile = File(...),
    _: User = Depends(require_super_admin),
):
    ext = Path(file.filename or "").suffix.lower()
    is_video = ext in {".mp4", ".mov", ".avi", ".webm", ".mkv"}
    is_image = ext in {".png", ".jpg", ".jpeg", ".webp", ".svg"}
    
    if not is_video and not is_image:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    content = await file.read()
    max_size = 50 * 1024 * 1024 if is_video else 5 * 1024 * 1024
    if len(content) > max_size:
        limit_mb = max_size // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"Max file size is {limit_mb}MB")
    
    filename = f"ad_{uuid4()}{ext}"
    save_path = Path(settings.upload_dir) / filename
    save_path.write_bytes(content)
    
    return {
        "image_url": f"/uploads/{filename}",
        "media_type": "video" if is_video else "image"
    }

@app.post("/admin/ads", response_model=AdvertisementOut)
def create_advertisement(
    payload: AdvertisementCreate,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    ad = Advertisement(
        id=str(uuid4()),
        **payload.model_dump(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad

@app.patch("/admin/ads/{ad_id}", response_model=AdvertisementOut)
def update_advertisement(
    ad_id: str,
    payload: dict,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    ad = db.query(Advertisement).filter(Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    
    data = _coerce_datetimes(payload)
    valid_fields = {c.name for c in Advertisement.__table__.columns}
    data = {k: v for k, v in data.items() if k in valid_fields}
    
    for key, value in data.items():
        if key not in ["id", "created_at"]:
            setattr(ad, key, value)
            
    ad.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ad)
    return ad

@app.get("/admin/ads", response_model=list[AdvertisementOut])
def list_advertisements(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Advertisement).order_by(Advertisement.created_at.desc()).all()

@app.get("/tenant/ads")
def get_tenant_ads(
    placement: str = Query("dashboard"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get active advertisements for the tenant based on placement and company type
    """
    query = db.query(Advertisement).filter(
        Advertisement.is_active == True,
        Advertisement.placement == placement
    )
    
    # Optional: Filter by company type if target_types is implemented on Advertisement model
    # For now, return all active ads for that placement
    return query.order_by(Advertisement.created_at.desc()).all()

@app.delete("/admin/ads/{ad_id}")
def delete_advertisement(
    ad_id: str,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    ad = db.query(Advertisement).filter(Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    db.delete(ad)
    db.commit()
    return {"success": True}

@app.get("/admin/dashboard-stats")
def get_admin_dashboard_stats(_: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    total_companies = db.query(Company).count()
    active_companies = db.query(Company).filter(Company.is_active.is_(True)).count()
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_companies_this_month = db.query(Company).filter(Company.created_at >= thirty_days_ago).count()
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    
    active_companies_list = db.query(Company).filter(Company.is_active.is_(True)).all()
    monthly_revenue = 0
    for comp in active_companies_list:
        if comp.subscription_plan_id:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == comp.subscription_plan_id).first()
            if plan:
                monthly_revenue += plan.price
        elif comp.subscription_plan:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name.ilike(comp.subscription_plan)).first()
            if plan:
                monthly_revenue += plan.price
    
    subscription_breakdown = []
    plans = db.query(SubscriptionPlan).all()
    for plan in plans:
        count = db.query(Company).filter(Company.subscription_plan_id == plan.id).count()
        count += db.query(Company).filter(Company.subscription_plan_id.is_(None), Company.subscription_plan.ilike(plan.name)).count()
        
        percentage = (count / active_companies * 100) if active_companies > 0 else 0
        subscription_breakdown.append({
            "plan": plan.name,
            "count": count,
            "percentage": percentage
        })
        
    recent_companies = db.query(Company).order_by(Company.created_at.desc()).limit(5).all()
    
    activities = []
    for c in recent_companies:
        activities.append({
            "action": "New company registered",
            "target": c.name,
            "time": c.created_at.isoformat() + "Z",
            "type": "company"
        })
        
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    for u in recent_users:
        activities.append({
            "action": "User account created",
            "target": u.email,
            "time": u.created_at.isoformat() + "Z",
            "type": "user"
        })
        
    recent_ads = db.query(Advertisement).order_by(Advertisement.created_at.desc()).limit(3).all()
    for ad in recent_ads:
        activities.append({
            "action": "Ad campaign created",
            "target": ad.title,
            "time": ad.created_at.isoformat() + "Z",
            "type": "ad"
        })
        
    activities.sort(key=lambda x: x["time"], reverse=True)
    activities = activities[:5]
    
    return {
        "stats": {
            "totalCompanies": total_companies,
            "activeCompanies": active_companies,
            "totalUsers": total_users,
            "activeUsers": active_users,
            "monthlyRevenue": monthly_revenue,
            "revenueGrowth": 12.5,
            "newCompaniesThisMonth": new_companies_this_month,
            "activeSubscriptions": active_companies,
            "pendingApprovals": 0
        },
        "subscriptionBreakdown": subscription_breakdown,
        "recentCompanies": recent_companies,
        "recentActivity": activities
    }

@app.get("/tenant/shift/summary")
async def get_shift_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
        
    # Find last closed shift for this user to get start_time
    last_shift = db.query(Shift).filter(
        Shift.user_id == current_user.id
    ).order_by(Shift.end_time.desc()).first()
    
    start_time = last_shift.end_time if last_shift else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = datetime.now()
    
    # All sales since start_time
    sales = db.query(Transaction).filter(
        Transaction.company_id == current_user.company_id,
        Transaction.type == "sale",
        Transaction.created_at >= start_time,
        Transaction.created_at <= end_time
    ).all()
    
    total_sales = sum(s.total for s in sales)
    sales_count = len(sales)
    items_count = sum(len(s.items or []) for s in sales)
    
    cash_received = sum(s.amount_paid for s in sales if s.payment_method == "cash")
    credit_sales = sum(s.total - s.amount_paid for s in sales if s.status == "pending")
    
    # Calculate profit and find top customer
    total_profit = 0
    customer_sales = {}
    
    for s in sales:
        # Top Customer calculation - exclude Walk-in Customer
        if s.customer_name and s.customer_name != "Walk-in Customer":
            customer_sales[s.customer_name] = customer_sales.get(s.customer_name, 0) + s.total
        
        # Profit calculation: total - sum(cost_price * quantity for each item)
        sale_cost = 0
        for item in (s.items or []):
            try:
                qty = float(item.get('quantity', 0))
                cost = float(item.get('cost_price', 0))
                sale_cost += (qty * cost)
            except (ValueError, TypeError):
                continue
        total_profit += (s.total - sale_cost)

    top_customer = "N/A"
    if customer_sales:
        top_customer = max(customer_sales, key=customer_sales.get)

    # Group by payment method
    payment_methods = {}
    for s in sales:
        method = s.payment_method or "cash"
        payment_methods[method] = payment_methods.get(method, 0) + s.amount_paid
        
    # Expenses since start_time
    expenses = db.query(Expenditure).filter(
        Expenditure.company_id == current_user.company_id,
        Expenditure.created_at >= start_time,
        Expenditure.created_at <= end_time
    ).all()
    total_expenses = sum(e.amount for e in expenses)
    
    # Net Profit (Profit from sales - Expenses)
    net_profit = total_profit - total_expenses
    
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_sales": total_sales,
        "total_profit": total_profit,
        "net_profit": net_profit,
        "sales_count": sales_count,
        "items_count": items_count,
        "cash_received": cash_received,
        "expected_cash": cash_received,
        "credit_sales": credit_sales,
        "total_expenses": total_expenses,
        "payment_methods": payment_methods,
        "top_customer": top_customer
    }

@app.post("/tenant/shift/close")
async def close_shift(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
        
    actual_cash = float(payload.get("actual_cash", 0))
    notes = payload.get("notes", "")
    
    # Find last closed shift for this user to get start_time
    last_shift = db.query(Shift).filter(
        Shift.user_id == current_user.id
    ).order_by(Shift.end_time.desc()).first()
    
    start_time = last_shift.end_time if last_shift else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = datetime.now()
    
    # Calculate total cash sales since start_time
    cash_sales = db.query(Transaction).filter(
        Transaction.company_id == current_user.company_id,
        Transaction.type == "sale",
        Transaction.payment_method == "cash",
        Transaction.created_at >= start_time,
        Transaction.created_at <= end_time
    ).all()
    
    expected_cash = sum(t.amount_paid for t in cash_sales)
    discrepancy = actual_cash - expected_cash
    
    # Create shift record
    new_shift = Shift(
        id=str(uuid4()),
        company_id=current_user.company_id,
        user_id=current_user.id,
        user_name=current_user.name,
        start_time=start_time,
        end_time=end_time,
        expected_cash=expected_cash,
        actual_cash=actual_cash,
        discrepancy=discrepancy,
        notes=notes
    )
    db.add(new_shift)
    db.commit()
    
    # Send SMS to owner
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    from .sms import BeemSMSService
    if company and company.phone:
        owner_phone = company.phone
        diff_text = f"Pungufu ya: Tsh {abs(discrepancy):,.0f}" if discrepancy < 0 else f"Ziada ya: Tsh {discrepancy:,.0f}"
        if discrepancy == 0: diff_text = "Hesabu Imelingana"
        
        message = (
            f"Funga Hesabu: {current_user.name}\n"
            f"Pesa Inayotarajiwa: Tsh {expected_cash:,.0f}\n"
            f"Pesa Taslimu: Tsh {actual_cash:,.0f}\n"
            f"{diff_text}\n"
            f"DUKA-SALES"
        )
        try:
            await BeemSMSService.send_sms(dest_addr=owner_phone, message=message)
        except Exception:
            pass
            
    return {"message": "Shift closed successfully", "expected_cash": expected_cash, "discrepancy": discrepancy}

@app.get("/tenant/events")
def list_events(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Event).filter(Event.company_id == current_user.company_id).order_by(Event.created_at.desc()).all()

@app.post("/tenant/events")
def create_event(payload: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    # Handle multiple possible field names from different frontend versions
    start_date_raw = payload.get("start_date") or payload.get("event_date")
    end_date_raw = payload.get("end_date")
    
    if not start_date_raw:
        raise HTTPException(status_code=400, detail="Start date is required")
        
    try:
        start_date = datetime.fromisoformat(str(start_date_raw).replace("Z", "+00:00"))
        end_date = None
        if end_date_raw:
            end_date = datetime.fromisoformat(str(end_date_raw).replace("Z", "+00:00"))
            
        event = Event(
            id=str(uuid4()),
            company_id=current_user.company_id,
            title=payload.get("title", "Untitled Event"),
            description=payload.get("description"),
            start_date=start_date,
            end_date=end_date,
            is_all_day=payload.get("is_all_day", False),
            visibility=payload.get("visibility", "public"),
            created_by=current_user.id,
            created_by_name=current_user.name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/tenant/pos/process-return")
def process_return(payload: dict, current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    original_txn_id = payload.get("original_transaction_id")
    return_qtys = payload.get("return_qtys", {})
    refund_method = payload.get("refund_method", "cash")
    reason = payload.get("reason")
    
    if not original_txn_id or not return_qtys:
        raise HTTPException(status_code=400, detail="Original transaction ID and return quantities are required")
        
    # 1. Get original transaction
    original_txn = db.query(Transaction).filter(
        Transaction.id == original_txn_id,
        Transaction.company_id == current_user.company_id
    ).first()
    
    if not original_txn:
        raise HTTPException(status_code=404, detail="Original transaction not found")
        
    # 2. Create Return Transaction
    return_txn_id = str(uuid4())
    # Generate return number based on original
    return_number = f"RET-{original_txn.transaction_number}"
    
    # Calculate return totals and update items
    return_items = []
    total_refund = 0
    
    for item in original_txn.items:
        item_id = item.get("id") or item.get("product_id")
        qty_to_return = float(return_qtys.get(item_id, 0))
        
        if qty_to_return > 0:
            unit_price = float(item.get("unit_price") or item.get("price") or 0)
            line_total = qty_to_return * unit_price
            total_refund += line_total
            
            return_items.append({
                **item,
                "quantity": qty_to_return,
                "total": line_total,
                "is_return": True,
                "original_transaction_number": original_txn.transaction_number
            })
            
            # 3. Update stock (put items back into inventory)
            product_id = item.get("id") or item.get("product_id")
            if product_id:
                product = db.query(Product).filter(Product.id == product_id).first()
                if product:
                    product.quantity += qty_to_return
                    product.updated_at = datetime.utcnow()

    if not return_items:
        raise HTTPException(status_code=400, detail="No valid items to return")

    # 4. Create the return transaction record
    new_return = Transaction(
        id=return_txn_id,
        company_id=current_user.company_id,
        transaction_number=return_number,
        type="return",
        status="completed",
        customer_id=original_txn.customer_id,
        customer_name=original_txn.customer_name,
        items=return_items,
        subtotal=total_refund,
        total=total_refund,
        amount_paid=total_refund,
        payment_method=refund_method,
        cashier_id=current_user.id,
        cashier_name=current_user.name,
        notes=reason,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_return)
    
    # 5. If it was a credit sale, reduce customer debt
    if original_txn.customer_id and total_refund > 0:
        customer = db.query(Customer).filter(Customer.id == original_txn.customer_id).first()
        if customer and customer.current_debt > 0:
            refund_to_debt = min(customer.current_debt, total_refund)
            customer.current_debt -= refund_to_debt
            
    db.commit()
    db.refresh(new_return)
    return new_return

@app.get("/tenant/products")
def list_products(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Product).filter(Product.company_id == current_user.company_id).order_by(Product.name).all()

@app.get("/tenant/products/by-code/{code}")
def get_product_by_code(code: str, current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    product = db.query(Product).filter(
        Product.company_id == current_user.company_id,
        (Product.sku == code) | (Product.barcode == code)
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/tenant/products")
def create_product(payload: ProductIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    data = payload.model_dump(exclude={"id", "company_id", "created_at", "updated_at"})
    product = Product(
        id=str(uuid4()),
        company_id=current_user.company_id,
        **data,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@app.get("/tenant/categories")
def list_categories(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Category).filter(Category.company_id == current_user.company_id).all()

@app.post("/tenant/categories")
def create_category(payload: CategoryIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    data = payload.model_dump(exclude={"id", "company_id", "created_at", "updated_at"})
    category = Category(
        id=str(uuid4()),
        company_id=current_user.company_id,
        **data,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except Exception as e:
        db.rollback()
        if "database or disk is full" in str(e).lower():
            raise HTTPException(status_code=507, detail="Database storage is full. Please free up disk space or contact support.")
        raise HTTPException(status_code=500, detail=f"Failed to create category: {str(e)}")

@app.get("/tenant/customers")
def list_customers(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Customer).filter(Customer.company_id == current_user.company_id).all()

@app.post("/tenant/customers")
def create_customer(payload: CustomerIn, current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    data = payload.model_dump(exclude={"id", "company_id", "created_at", "updated_at"})
    customer = Customer(
        id=str(uuid4()),
        company_id=current_user.company_id,
        **data,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@app.get("/tenant/suppliers")
def list_suppliers(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Supplier).filter(Supplier.company_id == current_user.company_id).all()

@app.post("/tenant/suppliers")
def create_supplier(payload: SupplierIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    data = payload.model_dump(exclude={"id", "company_id", "created_at", "updated_at"})
    supplier = Supplier(
        id=str(uuid4()),
        company_id=current_user.company_id,
        **data,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@app.get("/tenant/purchase_orders")
def list_purchase_orders(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(PurchaseOrder).filter(PurchaseOrder.company_id == current_user.company_id).order_by(PurchaseOrder.created_at.desc()).all()

@app.post("/tenant/purchase_orders")
def create_purchase_order(payload: PurchaseOrderIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    # 1. Create Purchase Order
    data = payload.model_dump(exclude={"id", "company_id", "created_at", "updated_at"})
    po_id = str(uuid4())
    po = PurchaseOrder(
        id=po_id,
        company_id=current_user.company_id,
        **data,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(po)
    
    # 2. Handle Supplier Debt (Payable)
    if po.amount_due > 0:
        supplier = db.query(Supplier).filter(
            Supplier.id == po.supplier_id,
            Supplier.company_id == current_user.company_id
        ).first()
        
        if supplier:
            # Update supplier's current debt balance
            supplier.current_debt += po.amount_due
            supplier.updated_at = datetime.utcnow()
            
            # Create a Debt record (payable type)
            debt = Debt(
                id=str(uuid4()),
                company_id=current_user.company_id,
                type="payable",
                entity_type="supplier",
                entity_id=supplier.id,
                entity_name=supplier.name,
                reference_type="purchase",
                reference_id=po_id,
                reference_number=po.order_number,
                original_amount=po.amount_due,
                paid_amount=0,
                remaining_amount=po.amount_due,
                due_date=po.expected_date or (datetime.utcnow() + timedelta(days=30)),
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(debt)

    db.commit()
    db.refresh(po)
    return po

@app.post("/tenant/purchase_orders/{order_id}/receive")
def receive_purchase_order(
    order_id: str,
    payload: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == order_id,
        PurchaseOrder.company_id == current_user.company_id
    ).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot receive items for a cancelled order")
    
    receive_qtys = payload.get("receive_qtys", {})
    auto_create_products = payload.get("auto_create_products", False)
    
    if not receive_qtys:
        raise HTTPException(status_code=400, detail="No quantities provided")
    
    from sqlalchemy.orm.attributes import flag_modified
    
    # Update order items with received quantities
    updated_items = []
    for item in po.items:
        item_id = item.get("id")
        qty_received = float(receive_qtys.get(item_id, 0))
        product_id = item.get("productId") or item.get("product_id")
        
        if qty_received > 0:
            item["receivedQuantity"] = float(item.get("receivedQuantity", 0)) + qty_received
            
            # Update/create product in inventory if auto_create_products is enabled
            product = None
            if product_id:
                product = db.query(Product).filter(Product.id == product_id).first()

            unit_cost = float(item.get("unitCost", 0))

            if auto_create_products and not product:
                new_product_id = product_id or str(uuid4())
                product = Product(
                    id=new_product_id,
                    company_id=current_user.company_id,
                    name=item.get("productName", "Unknown"),
                    sku=item.get("sku") or f"SKU-{new_product_id[:8]}",
                    quantity=qty_received,
                    category_id=item.get("categoryId"),
                    selling_price=float(item.get("sellingPrice", 0)),
                    cost_price=unit_cost,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(product)
                if not product_id:
                    item["productId"] = new_product_id
            elif product:
                # Update existing product quantity and cost price
                product.quantity += qty_received
                if unit_cost > 0:
                    product.cost_price = unit_cost
                product.updated_at = datetime.utcnow()
        
        updated_items.append(item)
    
    # Calculate order status
    # We consider it received if ALL items are fully received
    all_received = True
    any_received = False
    
    for item in updated_items:
        ordered = float(item.get("orderedQuantity", 0))
        received = float(item.get("receivedQuantity", 0))
        if received < ordered:
            all_received = False
        if received > 0:
            any_received = True
            
    if all_received:
        po.status = "received"
        po.received_date = datetime.utcnow()
    elif any_received:
        po.status = "partial"
    
    po.items = updated_items
    flag_modified(po, "items")
    po.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(po)
        return po
    except Exception as e:
        db.rollback()
        if "database or disk is full" in str(e).lower():
            raise HTTPException(status_code=507, detail="Database storage is full. Please free up disk space or contact support.")
        raise HTTPException(status_code=500, detail=f"Failed to update purchase order: {str(e)}")

@app.get("/tenant/transactions")
def list_transactions(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Transaction).filter(Transaction.company_id == current_user.company_id).order_by(Transaction.created_at.desc()).all()

@app.post("/tenant/pos/complete-sale")
def complete_sale(payload: TransactionIn, current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    # 1. Create Transaction
    # Filter data to only include valid Transaction model fields
    txn_data = payload.model_dump(exclude={"id", "company_id", "created_at", "updated_at", "cashier_id", "cashier_name"})
    valid_fields = {c.name for c in Transaction.__table__.columns}
    txn_data = {k: v for k, v in txn_data.items() if k in valid_fields}
    
    txn_id = str(uuid4())
    txn = Transaction(
        id=txn_id,
        company_id=current_user.company_id,
        cashier_id=current_user.id,
        cashier_name=current_user.name,
        **txn_data,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(txn)
    
    # 2. Update Stock & Handle Items
    for item in (payload.items or []):
        product_id = item.get("id") or item.get("product_id")
        if product_id:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                qty = float(item.get("quantity", 0))
                product.quantity -= qty
                product.updated_at = datetime.utcnow()

    # 3. Handle Customer Debt
    if payload.customer_id and payload.amount_due > 0:
        customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
        if customer:
            customer.current_debt += payload.amount_due
            
            # Create Debt record
            debt = Debt(
                id=str(uuid4()),
                company_id=current_user.company_id,
                type="receivable",
                entity_type="customer",
                entity_id=customer.id,
                entity_name=customer.name,
                reference_type="transaction",
                reference_id=txn_id,
                reference_number=txn.transaction_number,
                original_amount=payload.amount_due,
                paid_amount=0,
                remaining_amount=payload.amount_due,
                due_date=datetime.utcnow() + timedelta(days=30),
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(debt)

    db.commit()
    db.refresh(txn)
    return txn

@app.get("/tenant/expenditures")
def list_expenditures(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Expenditure).filter(Expenditure.company_id == current_user.company_id).order_by(Expenditure.created_at.desc()).all()

@app.get("/tenant/product_batches")
def list_product_batches(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(ProductBatch).filter(ProductBatch.company_id == current_user.company_id).all()

@app.get("/tenant/staff_salaries")
def list_staff_salaries(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(StaffSalary).filter(StaffSalary.company_id == current_user.company_id).all()

@app.get("/tenant/insights")
def get_insights(
    current_user: User = Depends(require_cashier), 
    db: Session = Depends(get_db),
    language: str = Query(default="en", description="Language code (en or sw)")
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    # Calculate dynamic insights based on actual data
    company_id = current_user.company_id
    
    # Get sales data
    today = datetime.utcnow()
    today_sales = db.query(Transaction).filter(
        Transaction.company_id == company_id,
        Transaction.type == "sale",
        Transaction.created_at >= today.replace(hour=0, minute=0, second=0, microsecond=0)
    ).all()
    today_revenue = sum(t.total for t in today_sales)
    
    # Get low stock items
    low_stock = db.query(Product).filter(
        Product.company_id == company_id,
        Product.quantity <= Product.min_stock
    ).count()
    
    # Get outstanding debts with details
    outstanding_debt_records = db.query(Debt).filter(
        Debt.company_id == company_id,
        Debt.status.in_(["pending", "partial"])
    ).all()
    outstanding_debts = len(outstanding_debt_records)
    total_outstanding = sum(d.remaining_amount for d in outstanding_debt_records)
    
    # Get top customers with debts
    top_debtors = db.query(Debt).filter(
        Debt.company_id == company_id,
        Debt.entity_type == "customer",
        Debt.status.in_(["pending", "partial"]),
        Debt.remaining_amount > 0
    ).order_by(Debt.remaining_amount.desc()).limit(3).all()
    
    # Get supplier credits (payables)
    supplier_payables = db.query(PurchaseOrder).filter(
        PurchaseOrder.company_id == company_id,
        PurchaseOrder.status == "received",
        PurchaseOrder.amount_due > 0
    ).all()
    total_payables = sum(po.amount_due for po in supplier_payables)
    
    # Get top suppliers to pay
    top_suppliers_to_pay = db.query(PurchaseOrder, Supplier).join(
        Supplier, PurchaseOrder.supplier_id == Supplier.id
    ).filter(
        PurchaseOrder.company_id == company_id,
        PurchaseOrder.status == "received",
        PurchaseOrder.amount_due > 0
    ).order_by(PurchaseOrder.amount_due.desc()).limit(3).all()
    
    # Get pending orders
    pending_orders = db.query(PurchaseOrder).filter(
        PurchaseOrder.company_id == company_id,
        PurchaseOrder.status.in_(["ordered", "pending"])
    ).count()
    
    # Get top selling products today
    top_products_today = {}
    
    for transaction in today_sales:
        if transaction.items and isinstance(transaction.items, list):
            for item in transaction.items:
                # Handle both dict and object cases
                if isinstance(item, dict):
                    product_id = item.get('id') or item.get('product_id') or item.get('productId')
                    quantity = item.get('quantity') or item.get('qty') or item.get('amount', 0)
                    item_name = item.get('name') or item.get('product_name') or item.get('productName')
                else:
                    product_id = getattr(item, 'id', None) or getattr(item, 'product_id', None)
                    quantity = getattr(item, 'quantity', 0) or getattr(item, 'qty', 0)
                    item_name = getattr(item, 'name', None) or getattr(item, 'product_name', None)
                
                if product_id and quantity > 0:
                    if product_id not in top_products_today:
                        top_products_today[product_id] = {'name': item_name, 'quantity': 0}
                    top_products_today[product_id]['quantity'] += quantity
    
    # Fetch product names from database if we have product IDs
    if top_products_today:
        product_ids = [pid for pid in list(top_products_today.keys()) if pid]
        if product_ids:
            products = db.query(Product).filter(
                Product.id.in_(product_ids),
                Product.company_id == company_id
            ).all()
            
            product_name_map = {p.id: p.name for p in products}
            
            for product_id in top_products_today:
                if product_id in product_name_map:
                    top_products_today[product_id]['name'] = product_name_map[product_id]
                elif not top_products_today[product_id]['name']:
                    product = db.query(Product).filter(Product.id == product_id).first()
                    if product:
                        top_products_today[product_id]['name'] = product.name or product.sku or f'Product {product_id[:8]}'
                    else:
                        top_products_today[product_id]['name'] = f'Unknown {product_id[:8]}'
    
    # Sort by quantity and get top 3
    sorted_products = sorted(
        [(k, v) for k, v in top_products_today.items() if v['quantity'] > 0],
        key=lambda x: x[1]['quantity'],
        reverse=True
    )[:3]
    
    # Get low stock products with names
    low_stock_products = db.query(Product).filter(
        Product.company_id == company_id,
        Product.quantity <= Product.min_stock,
        Product.quantity > 0
    ).order_by(Product.quantity.asc()).limit(3).all()
    
    # Get out of stock products
    out_of_stock = db.query(Product).filter(
        Product.company_id == company_id,
        Product.quantity == 0,
        Product.is_active == True
    ).count()
    
    # Build insights list
    insights = []
    
    if language == "sw":
        # Swahili translations
        sales_insights = []
        if today_revenue > 0:
            sales_insights.append(f"💰 Mauzo ya leo: Ksh {today_revenue:,.0f}")
        
        if sorted_products:
            product_names = [f"{data['name']} ({data['quantity']})" for product_id, data in sorted_products[:3]]
            sales_insights.append(f"🏆 Vinavyouza zaidi: {', '.join(product_names)}")
        
        if sales_insights:
            insights.append("📈 MUHTASARI WA MAUZO")
            insights.extend(sales_insights)
        
        financial_insights = []
        if top_debtors:
            debtor_names = [f"{debt.entity_name} (Ksh {debt.remaining_amount:,.0f})" for debt in top_debtors[:3]]
            financial_insights.append(f"📝 Wateja wanaodaiwa: {', '.join(debtor_names)}")
        
        if top_suppliers_to_pay:
            supplier_names = [f"{supplier.name} (Ksh {po.amount_due:,.0f})" for po, supplier in top_suppliers_to_pay[:3]]
            financial_insights.append(f"🏪 Madeni kwa wasambazaji: {', '.join(supplier_names)}")
        
        if total_outstanding > 0 or total_payables > 0:
            financial_insights.append(f"💵 Jumla: Madeni (Ya Kupokelewa) Ksh {total_outstanding:,.0f} | Deni (Ya Kulipa) Ksh {total_payables:,.0f}")
        
        if financial_insights:
            insights.append("💰 MADENI NA MALIPO")
            insights.extend(financial_insights)
        
        stock_insights = []
        if out_of_stock > 0:
            stock_insights.append(f"🚫 {out_of_stock} bidhaa zimekosa stoo kamili")
        
        if low_stock > 0:
            if low_stock_products:
                stock_items = [f"{p.name} ({p.quantity} wazimu)" for p in low_stock_products[:3]]
                stock_insights.append(f"⚠️ Stoo ndogo: {', '.join(stock_items)}")
            else:
                stock_insights.append(f"⚠️ {low_stock} bidhaa zina stoo ndogo")
        else:
            stock_insights.append("✅ Stoo yako iko katika hali nzuri")
        
        if stock_insights:
            insights.append("📦 HALI YA STOO")
            insights.extend(stock_insights)
        
        if pending_orders > 0:
            insights.append("📋 MATUKIO NA ODA")
            insights.append(f"📦 Oda {pending_orders} za manunuzi zinazosubiri kuwasilishwa")
        
        if len(insights) > 0:
            insights.append("💡 USHAURI WA KILA SIKU")
            insights.append("Fuatilia ripoti hizi kila siku kwa maamuzi mazuri")
        
        if len(insights) == 0:
            insights = [
                "🌟 KARIBU KWENYE DUKA LAKO!",
                "📊 Fuatilia mauzo yako kila siku",
                "📦 Hakikisha stoo iko katika hali nzuri",
                "💰 Simamia madeni ya wateja na wasambazaji"
            ]
    else:
        # English translations
        sales_insights = []
        if today_revenue > 0:
            sales_insights.append(f"💰 Today's sales: Ksh {today_revenue:,.0f}")
        
        if sorted_products:
            product_names = [f"{data['name']} (x{data['quantity']})" for product_id, data in sorted_products[:3]]
            sales_insights.append(f"🏆 Top sellers: {', '.join(product_names)}")
        
        if sales_insights:
            insights.append("📈 SALES SUMMARY")
            insights.extend(sales_insights)
        
        financial_insights = []
        if top_debtors:
            debtor_names = [f"{debt.entity_name} (Ksh {debt.remaining_amount:,.0f})" for debt in top_debtors[:3]]
            financial_insights.append(f"📝 Customers owing: {', '.join(debtor_names)}")
        
        if top_suppliers_to_pay:
            supplier_names = [f"{supplier.name} (Ksh {po.amount_due:,.0f})" for po, supplier in top_suppliers_to_pay[:3]]
            financial_insights.append(f"🏪 Payables to suppliers: {', '.join(supplier_names)}")
        
        if total_outstanding > 0 or total_payables > 0:
            financial_insights.append(f"💵 Total: Receivables (Owed to You) Ksh {total_outstanding:,.0f} | Payables (You Owe) Ksh {total_payables:,.0f}")
        
        if financial_insights:
            insights.append("💰 DEBTS & PAYMENTS")
            insights.extend(financial_insights)
        
        stock_insights = []
        if out_of_stock > 0:
            stock_insights.append(f"🚫 {out_of_stock} products completely out of stock")
        
        if low_stock > 0:
            if low_stock_products:
                stock_items = [f"{p.name} ({p.quantity} left)" for p in low_stock_products[:3]]
                stock_insights.append(f"⚠️ Low stock: {', '.join(stock_items)}")
            else:
                stock_insights.append(f"⚠️ {low_stock} items have low stock")
        else:
            stock_insights.append("✅ Your stock levels are healthy")
        
        if stock_insights:
            insights.append("📦 STOCK STATUS")
            insights.extend(stock_insights)
        
        if pending_orders > 0:
            insights.append("📋 EVENTS & ORDERS")
            insights.append(f"📦 {pending_orders} purchase orders awaiting delivery")
        
        if len(insights) > 0:
            insights.append("💡 DAILY BUSINESS TIPS")
            insights.append("Review these metrics daily for better decisions")
        
        if len(insights) == 0:
            insights = [
                "🌟 WELCOME TO YOUR SHOP!",
                "📊 Track your sales performance daily",
                "📦 Maintain optimal stock levels",
                "💰 Monitor customer and supplier debts"
            ]
    
    return {"insights": insights}

@app.get("/tenant/debts")
def list_debts(current_user: User = Depends(require_cashier), db: Session = Depends(get_db)):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    return db.query(Debt).filter(Debt.company_id == current_user.company_id).order_by(Debt.created_at.desc()).all()

@app.post("/tenant/debts/{debt_id}/record-payment")
def record_debt_payment(
    debt_id: str,
    payload: dict,
    current_user: User = Depends(require_cashier),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.company_id == current_user.company_id
    ).first()
    
    if not debt:
        raise HTTPException(status_code=404, detail="Debt record not found")
        
    amount = float(payload.get("amount", 0))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")
        
    if amount > debt.remaining_amount:
        raise HTTPException(status_code=400, detail="Payment amount exceeds remaining debt")
        
    payment_method = payload.get("payment_method", "cash")
    
    # 1. Update debt record
    debt.paid_amount += amount
    debt.remaining_amount -= amount
    
    if debt.remaining_amount <= 0:
        debt.status = "paid"
    else:
        debt.status = "partial"
        
    # Add to payments history
    payment_record = {
        "id": str(uuid4()),
        "amount": amount,
        "date": datetime.utcnow().isoformat(),
        "method": payment_method,
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.name
    }
    
    if debt.payments is None:
        debt.payments = []
    
    # SQLAlchemy JSON column needs reassignment to detect change or use flag_modified
    new_payments = list(debt.payments)
    new_payments.append(payment_record)
    debt.payments = new_payments
    
    # 2. Update related entity's debt (Customer or Supplier)
    if debt.entity_type == "customer":
        customer = db.query(Customer).filter(Customer.id == debt.entity_id).first()
        if customer:
            customer.current_debt -= amount
    elif debt.entity_type == "supplier":
        supplier = db.query(Supplier).filter(Supplier.id == debt.entity_id).first()
        if supplier:
            supplier.current_debt -= amount
            
    # 3. Create a transaction record for the payment
    txn_number = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    txn = Transaction(
        id=str(uuid4()),
        company_id=current_user.company_id,
        transaction_number=txn_number,
        type="payment",
        status="completed",
        customer_id=debt.entity_id if debt.entity_type == "customer" else None,
        customer_name=debt.entity_name if debt.entity_type == "customer" else None,
        subtotal=amount,
        total=amount,
        amount_paid=amount,
        payment_method=payment_method,
        cashier_id=current_user.id,
        cashier_name=current_user.name,
        notes=f"Debt payment for {debt.reference_number}",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(txn)
    
    debt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(debt)
    return debt

# Company Bank Details Endpoints
@app.post("/tenant/bank-details")
def create_bank_detail(
    bank_detail: schemas.CompanyBankDetailCreate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    db_bank_detail = CompanyBankDetail(
        company_id=current_user.company_id,
        **bank_detail.dict()
    )
    db.add(db_bank_detail)
    db.commit()
    db.refresh(db_bank_detail)
    return db_bank_detail

@app.get("/tenant/bank-details")
def list_bank_details(
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    return db.query(CompanyBankDetail).filter(
        CompanyBankDetail.company_id == current_user.company_id,
        CompanyBankDetail.is_active == True
    ).all()

@app.put("/tenant/bank-details/{bank_detail_id}")
def update_bank_detail(
    bank_detail_id: str,
    bank_detail_update: schemas.CompanyBankDetailUpdate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    bank_detail = db.query(CompanyBankDetail).filter(
        CompanyBankDetail.id == bank_detail_id,
        CompanyBankDetail.company_id == current_user.company_id
    ).first()
    
    if not bank_detail:
        raise HTTPException(status_code=404, detail="Bank detail not found")
    
    for field, value in bank_detail_update.dict(exclude_unset=True).items():
        setattr(bank_detail, field, value)
    
    db.commit()
    db.refresh(bank_detail)
    return bank_detail

@app.delete("/tenant/bank-details/{bank_detail_id}")
def delete_bank_detail(
    bank_detail_id: str,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    bank_detail = db.query(CompanyBankDetail).filter(
        CompanyBankDetail.id == bank_detail_id,
        CompanyBankDetail.company_id == current_user.company_id
    ).first()
    
    if not bank_detail:
        raise HTTPException(status_code=404, detail="Bank detail not found")
    
    bank_detail.is_active = False
    db.commit()
    return {"message": "Bank detail deleted successfully"}

# Company Terms & Conditions Endpoints
@app.post("/tenant/terms-conditions")
def create_terms_condition(
    terms_condition: schemas.CompanyTermsConditionCreate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    db_terms_condition = CompanyTermsCondition(
        company_id=current_user.company_id,
        **terms_condition.dict()
    )
    db.add(db_terms_condition)
    db.commit()
    db.refresh(db_terms_condition)
    return db_terms_condition

@app.get("/tenant/terms-conditions")
def list_terms_conditions(
    document_type: str = None,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    query = db.query(CompanyTermsCondition).filter(
        CompanyTermsCondition.company_id == current_user.company_id,
        CompanyTermsCondition.is_active == True
    )
    
    if document_type:
        query = query.filter(CompanyTermsCondition.document_type == document_type)
    
    return query.all()

@app.put("/tenant/terms-conditions/{terms_id}")
def update_terms_condition(
    terms_id: str,
    terms_update: schemas.CompanyTermsConditionUpdate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    terms_condition = db.query(CompanyTermsCondition).filter(
        CompanyTermsCondition.id == terms_id,
        CompanyTermsCondition.company_id == current_user.company_id
    ).first()
    
    if not terms_condition:
        raise HTTPException(status_code=404, detail="Terms & conditions not found")
    
    for field, value in terms_update.dict(exclude_unset=True).items():
        setattr(terms_condition, field, value)
    
    db.commit()
    db.refresh(terms_condition)
    return terms_condition

@app.delete("/tenant/terms-conditions/{terms_id}")
def delete_terms_condition(
    terms_id: str,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    terms_condition = db.query(CompanyTermsCondition).filter(
        CompanyTermsCondition.id == terms_id,
        CompanyTermsCondition.company_id == current_user.company_id
    ).first()
    
    if not terms_condition:
        raise HTTPException(status_code=404, detail="Terms & conditions not found")
    
    terms_condition.is_active = False
    db.commit()
    return {"message": "Terms & conditions deleted successfully"}

# Enhanced Company Update Endpoint
@app.put("/tenant/company")
def update_company_details(
    company_update: CompanyUpdate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    for field, value in company_update.dict(exclude_unset=True).items():
        setattr(company, field, value)
    
    db.commit()
    db.refresh(company)
    return company

# Enhanced Customer Update Endpoint
@app.put("/tenant/customers/{customer_id}")
def update_customer_details(
    customer_id: str,
    customer_update: CustomerUpdate,
    current_user: User = Depends(require_cashier),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.company_id == current_user.company_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    for field, value in customer_update.dict(exclude_unset=True).items():
        setattr(customer, field, value)
    
    db.commit()
    db.refresh(customer)
    return customer

@app.post("/tenant/customers/{customer_id}/remind-debt")
async def remind_customer_debt(
    customer_id: str,
    current_user: User = Depends(require_cashier),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.company_id == current_user.company_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    if customer.current_debt <= 0:
        raise HTTPException(status_code=400, detail="Customer has no outstanding debt")
        
    if not customer.phone:
        raise HTTPException(status_code=400, detail="Customer has no phone number recorded")
        
    # Send SMS reminder
    from .sms import BeemSMSService
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    company_name = company.name if company else "Duka Lako"
    
    message = (
        f"Habari {customer.name},\n"
        f"Hii ni kumbukumbu ya deni lako la Tsh {customer.current_debt:,.0f} "
        f"katika duka la {company_name}.\n"
        f"Tafadhali fika kulipia. Ahsante."
    )
    
    try:
        await BeemSMSService.send_sms(dest_addr=customer.phone, message=message)
        return {"success": True, "message": "Reminder sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")

# --- Generic Tenant Resource Endpoints ---

@app.get("/tenant/{resource_name}")
def list_tenant_resource(
    resource_name: str,
    current_user: User = Depends(require_cashier),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    model = _resource_model(resource_name)
    return db.query(model).filter(model.company_id == current_user.company_id).all()

@app.post("/tenant/users", response_model=UserOut)
def create_tenant_user(
    payload: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    existing_user = db.query(User).filter(User.email.ilike(payload.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use")
    
    user = User(
        id=str(uuid4()),
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        company_id=current_user.company_id,
        is_active=payload.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.patch("/tenant/users/{user_id}", response_model=UserOut)
def update_tenant_user(
    user_id: str,
    payload: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
        
    for key, value in data.items():
        setattr(user, key, value)
        
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user

@app.get("/tenant/{resource_name}/{id}")
def get_tenant_resource(
    resource_name: str,
    id: str,
    current_user: User = Depends(require_cashier),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    model = _resource_model(resource_name)
    obj = db.query(model).filter(
        model.id == id,
        model.company_id == current_user.company_id
    ).first()
    
    if not obj:
        raise HTTPException(status_code=404, detail=f"{resource_name.capitalize()} not found")
    return obj

@app.post("/tenant/{resource_name}")
def create_tenant_resource(
    resource_name: str,
    payload: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    model = _resource_model(resource_name)
    data = _coerce_datetimes(payload)
    
    # --- Backend Integration for Specific Models ---
    # We use _filter_valid_fields to ensure the payload matches the DB model columns
    data = _filter_valid_fields(data, model)
    
    # Ensure ID is generated if not provided
    if "id" not in data or not data["id"]:
        data["id"] = str(uuid4())
    
    # Map frontend camelCase/custom keys to backend snake_case if they don't match
    # Note: Our _filter_valid_fields already cleaned up unknown keys.
    # But for customers, we need to be extra sure the new fields (tin_id, vrn_no, etc) are there.
    
    obj = model(
        company_id=current_user.company_id,
        **data
    )
    
    # Set timestamps if they exist on the model
    if hasattr(obj, "created_at"):
        obj.created_at = datetime.utcnow()
    if hasattr(obj, "updated_at"):
        obj.updated_at = datetime.utcnow()
        
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.patch("/tenant/{resource_name}/{id}")
def update_tenant_resource(
    resource_name: str,
    id: str,
    payload: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    model = _resource_model(resource_name)
    obj = db.query(model).filter(
        model.id == id,
        model.company_id == current_user.company_id
    ).first()
    
    if not obj:
        raise HTTPException(status_code=404, detail=f"{resource_name.capitalize()} not found")
    
    data = _coerce_datetimes(payload)
    data = _filter_valid_fields(data, model)
    
    for key, value in data.items():
        if key not in ["id", "company_id", "created_at"]:
            setattr(obj, key, value)
    
    if hasattr(obj, "updated_at"):
        obj.updated_at = datetime.utcnow()
        
    db.commit()
    db.refresh(obj)
    return obj

@app.get("/tenant/reports/customers")
def get_customer_report(
    period: str = "this_month",
    current_user: User = Depends(require_cashier),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    # Date range
    now = datetime.utcnow()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "this_week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "this_month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "this_year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 1. Total Stats
    total_customers = db.query(Customer).filter(Customer.company_id == current_user.company_id).count()
    active_customers = db.query(Customer).filter(Customer.company_id == current_user.company_id, Customer.is_active == True).count()
    
    # 2. Financial Stats
    debt_records = db.query(Debt).filter(
        Debt.company_id == current_user.company_id,
        Debt.entity_type == "customer",
        Debt.status.in_(["pending", "partial"])
    ).all()
    total_receivables = sum(d.remaining_amount for d in debt_records)
    
    # 3. Sales by customer in period
    transactions = db.query(Transaction).filter(
        Transaction.company_id == current_user.company_id,
        Transaction.type == "sale",
        Transaction.status == "completed",
        Transaction.created_at >= start_date
    ).all()
    
    customer_sales = {}
    total_revenue = 0
    for t in transactions:
        c_id = t.customer_id or "walk-in"
        c_name = t.customer_name or "Walk-in Customer"
        if c_id not in customer_sales:
            customer_sales[c_id] = {"name": c_name, "total": 0, "count": 0}
        customer_sales[c_id]["total"] += t.total
        customer_sales[c_id]["count"] += 1
        total_revenue += t.total

    # Sort top customers
    top_customers = sorted(customer_sales.values(), key=lambda x: x["total"], reverse=True)[:10]

    return {
        "totalCustomers": total_customers,
        "activeCustomers": active_customers,
        "totalReceivables": total_receivables,
        "totalRevenue": total_revenue,
        "topCustomers": top_customers,
        "period": period
    }

@app.delete("/tenant/{resource_name}/{id}")
def delete_tenant_resource(
    resource_name: str,
    id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
    
    model = _resource_model(resource_name)
    obj = db.query(model).filter(
        model.id == id,
        model.company_id == current_user.company_id
    ).first()
    
    if not obj:
        raise HTTPException(status_code=404, detail=f"{resource_name.capitalize()} not found")
    
    db.delete(obj)
    db.commit()
    return {"success": True}