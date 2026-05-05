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

@app.get("/admin/companies/{company_id}/stats")
def get_company_stats_admin(company_id: str, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    user_count = db.query(User).filter(User.company_id == company_id).count()
    product_count = db.query(Product).filter(Product.company_id == company_id).count()
    transaction_count = db.query(Transaction).filter(Transaction.company_id == company_id).count()
    revenue_list = db.query(Transaction).filter(Transaction.company_id == company_id, Transaction.type == "sale", Transaction.status == "completed").all()
    total_revenue = sum(t.total for t in revenue_list)
    customer_count = db.query(Customer).filter(Customer.company_id == company_id).count()
    supplier_count = db.query(Supplier).filter(Supplier.company_id == company_id).count()
    
    return {
        "users": user_count,
        "products": product_count,
        "transactions": transaction_count,
        "revenue": total_revenue,
        "customers": customer_count,
        "suppliers": supplier_count,
    }

@app.get("/admin/companies/{company_id}/users")
def get_company_users_admin(company_id: str, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return db.query(User).filter(User.company_id == company_id).all()

@app.get("/admin/companies/{company_id}/transactions")
def get_company_transactions_admin(company_id: str, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return db.query(Transaction).filter(Transaction.company_id == company_id).order_by(Transaction.created_at.desc()).limit(100).all()

@app.post("/admin/companies/{company_id}/toggle-status")
def toggle_company_status_admin(company_id: str, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.is_active = not bool(company.is_active)
    company.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(company)
    return company

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


@app.get("/admin/system/overview")
def get_system_overview(_: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    # Basic system overview
    total_companies = db.query(Company).count()
    total_users = db.query(User).count()
    active_sessions = 0 # Placeholder
    
    # Calculate total revenue
    active_companies = db.query(Company).filter(Company.is_active == True).all()
    total_revenue = 0
    for comp in active_companies:
        if comp.subscription_plan_id:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == comp.subscription_plan_id).first()
            if plan: total_revenue += plan.price
            
    return {
        "totalCompanies": total_companies,
        "totalUsers": total_users,
        "activeSessions": active_sessions,
        "totalRevenue": total_revenue,
        "serverStatus": "online",
        "databaseStatus": "connected",
        "lastBackup": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/admin/system/logs")
def get_system_logs(limit: int = 100, _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    # Placeholder for system logs - in a real app, you'd query a logs table
    # For now, return some mock data or recent activity from users/companies
    activities = []
    recent_companies = db.query(Company).order_by(Company.created_at.desc()).limit(limit // 2).all()
    for c in recent_companies:
        activities.append({
            "id": f"log-c-{c.id}",
            "level": "info",
            "message": f"New company registered: {c.name}",
            "timestamp": c.created_at.isoformat() + "Z",
            "source": "system"
        })
        
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(limit // 2).all()
    for u in recent_users:
        activities.append({
            "id": f"log-u-{u.id}",
            "level": "info",
            "message": f"User account created: {u.email}",
            "timestamp": u.created_at.isoformat() + "Z",
            "source": "auth"
        })
    
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:limit]


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
            f"V7-SaaS: Shift imefungwa na {current_user.name}.\n"
            f"Mauzo ya Cash: Tsh {expected_cash:,.0f}\n"
            f"Cash Halisi: Tsh {actual_cash:,.0f}\n"
            f"{diff_text}\n"
            f"Muda: {end_time.strftime('%H:%M %d/%m/%Y')}"
        )
        try:
            sms_service = BeemSMSService()
            sms_service.send_sms(owner_phone, message)
        except Exception:
            pass
            
    return {"success": True, "shift_id": new_shift.id}

@app.get("/tenant/shifts")
async def list_shifts(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="No company assigned")
        
    return db.query(Shift).filter(
        Shift.company_id == current_user.company_id
    ).order_by(Shift.end_time.desc()).limit(100).all()
