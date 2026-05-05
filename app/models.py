from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    tax_id = Column(String, nullable=True)
    logo = Column(Text, nullable=True)
    currency = Column(String, default="TSH")
    currency_symbol = Column(String, default="TSh")
    subscription_plan_id = Column(String, nullable=True, index=True)
    types = Column(JSON, default=list)
    subscription_plan = Column(String, default="free")
    subscription_expiry = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Enhanced company details for professional documents
    vrn_no = Column(String, nullable=True)  # VAT Registration Number
    tin_no = Column(String, nullable=True)  # Tax Identification Number
    website = Column(String, nullable=True)
    physical_address = Column(Text, nullable=True)
    postal_address = Column(Text, nullable=True)
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    city = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)

    # Business details
    business_license_no = Column(String, nullable=True)
    business_registration_no = Column(String, nullable=True)
    business_type = Column(String, nullable=True)  # e.g., "Limited Company", "Sole Proprietor"
    industry = Column(String, nullable=True)
    year_established = Column(Integer, nullable=True)

    # Contact details
    contact_person = Column(String, nullable=True)
    contact_person_title = Column(String, nullable=True)
    alternative_phone = Column(String, nullable=True)
    fax = Column(String, nullable=True)
    whatsapp = Column(String, nullable=True)

    # Social media
    facebook = Column(String, nullable=True)
    twitter = Column(String, nullable=True)
    instagram = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)

    # Document settings
    document_prefix = Column(String, nullable=True)  # e.g., "INV-", "QUO-"
    document_footer = Column(Text, nullable=True)
    document_header = Column(Text, nullable=True)
    authorised_signatory = Column(String, nullable=True)  # Name for signature line

    users = relationship("User", back_populates="company", cascade="all, delete")
    bank_details = relationship("CompanyBankDetail", back_populates="company", cascade="all, delete")
    terms_conditions = relationship("CompanyTermsCondition", back_populates="company", cascade="all, delete")


class StaffSalary(Base):
    __tablename__ = "staff_salaries"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    staff_id = Column(String, index=True, nullable=False)
    staff_name = Column(String, nullable=False)
    amount = Column(Float, default=0)
    payment_date = Column(DateTime, default=datetime.utcnow)
    payment_method = Column(String, default="cash")
    status = Column(String, default="paid")  # paid, pending, cancelled
    month = Column(String, nullable=False)  # e.g., "2024-01"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Expenditure(Base):
    __tablename__ = "expenditures"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    category = Column(String, nullable=False)  # rent, utilities, supplies, other
    amount = Column(Float, default=0)
    date = Column(DateTime, default=datetime.utcnow)
    payment_method = Column(String, default="cash")
    description = Column(Text, nullable=True)
    reference_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="cashier")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="users")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    price = Column(Float, default=0)
    billing_cycle = Column(String, default="monthly")
    max_users = Column(Integer, default=1)
    max_products = Column(Integer, default=100)
    max_locations = Column(Integer, default=1)
    features = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    parent_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    category_id = Column(String, nullable=True, index=True)
    sku = Column(String, nullable=False, index=True)
    qr_code = Column(Text, nullable=True) # Base64 or URL
    barcode = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False, index=True)
    unit = Column(String, default="piece")
    cost_price = Column(Float, default=0)
    selling_price = Column(Float, default=0)
    quantity = Column(Float, default=0)
    min_stock = Column(Float, default=0)
    
    # Pharmacy specific
    generic_name = Column(String, nullable=True)
    brand_name = Column(String, nullable=True)
    dosage = Column(String, nullable=True)
    form = Column(String, nullable=True)
    requires_prescription = Column(Boolean, default=False)
    units_per_pack = Column(Integer, default=1)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    batches = relationship("ProductBatch", back_populates="product", cascade="all, delete")


class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    batch_number = Column(String, nullable=False, index=True)
    expiry_date = Column(DateTime, nullable=False, index=True)
    quantity = Column(Float, default=0)
    cost_price = Column(Float, nullable=True)
    selling_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="batches")


class CompanyBankDetail(Base):
    __tablename__ = "company_bank_details"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    bank_name = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    branch_name = Column(String, nullable=True)
    branch_code = Column(String, nullable=True)
    swift_code = Column(String, nullable=True)
    iban = Column(String, nullable=True)
    routing_number = Column(String, nullable=True)  # For US banks
    sort_code = Column(String, nullable=True)  # For UK banks
    bank_address = Column(Text, nullable=True)
    mobile_money_name = Column(String, nullable=True)  # e.g., "M-Pesa"
    mobile_money_number = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="bank_details")


class CompanyTermsCondition(Base):
    __tablename__ = "company_terms_conditions"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    document_type = Column(String, nullable=False)  # invoice, quotation, delivery_note, payment_slip, order_receipt
    title = Column(String, nullable=True)
    terms_text = Column(Text, nullable=True)
    payment_terms = Column(Text, nullable=True)  # e.g., "Payment due within 30 days"
    delivery_terms = Column(Text, nullable=True)  # e.g., "Delivery within 7 business days"
    warranty_terms = Column(Text, nullable=True)
    return_policy = Column(Text, nullable=True)
    late_payment_terms = Column(Text, nullable=True)
    cancellation_policy = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="terms_conditions")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    # Enhanced customer details for documents
    customer_number = Column(String, nullable=True)  # Unique customer ID
    tax_id = Column(String, nullable=True)  # Customer TIN/VAT number
    vrn_no = Column(String, nullable=True)  # Customer VAT registration
    physical_address = Column(Text, nullable=True)
    postal_address = Column(Text, nullable=True)
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    city = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    
    # Business details for B2B customers
    business_name = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    contact_person_title = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # Shipping details
    shipping_address = Column(Text, nullable=True)
    shipping_city = Column(String, nullable=True)
    shipping_region = Column(String, nullable=True)
    shipping_country = Column(String, nullable=True)
    shipping_postal_code = Column(String, nullable=True)
    
    credit_limit = Column(Float, default=0)
    current_debt = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False, index=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    payment_terms = Column(String, nullable=True)
    current_debt = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    transaction_number = Column(String, index=True, nullable=False)
    type = Column(String, default="sale", index=True)
    status = Column(String, default="completed")
    customer_id = Column(String, nullable=True, index=True)
    customer_name = Column(String, nullable=True)
    items = Column(JSON, default=list)
    subtotal = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    total = Column(Float, default=0)
    payment_method = Column(String, default="cash")
    amount_paid = Column(Float, default=0)
    amount_due = Column(Float, default=0)
    cashier_id = Column(String, nullable=True)
    cashier_name = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    order_number = Column(String, index=True, nullable=False)
    supplier_id = Column(String, index=True, nullable=False)
    supplier_name = Column(String, nullable=False)
    status = Column(String, default="ordered")
    items = Column(JSON, default=list)
    subtotal = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    shipping_cost = Column(Float, default=0)
    other_costs = Column(Float, default=0)
    total = Column(Float, default=0)
    amount_paid = Column(Float, default=0)
    amount_due = Column(Float, default=0)
    expected_date = Column(DateTime, nullable=True)
    received_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Debt(Base):
    __tablename__ = "debts"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False, index=True)
    entity_name = Column(String, nullable=False)
    reference_type = Column(String, nullable=False)
    reference_id = Column(String, nullable=False, index=True)
    reference_number = Column(String, nullable=False, index=True)
    original_amount = Column(Float, default=0)
    paid_amount = Column(Float, default=0)
    remaining_amount = Column(Float, default=0)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="pending")
    payments = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Advertisement(Base):
    __tablename__ = "advertisements"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    media_type = Column(String, default="image")  # image, video
    link_url = Column(String, nullable=True)
    target = Column(String, default="all")  # all, free, basic, pro, enterprise, custom
    placements = Column(JSON, default=list)  # dashboard, pos, sidebar, modal
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Shift(Base):
    __tablename__ = "shifts"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    user_name = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, default=datetime.utcnow)
    expected_cash = Column(Float, default=0)
    actual_cash = Column(Float, default=0)
    discrepancy = Column(Float, default=0)
    status = Column(String, default="closed")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=True, index=True)
    is_all_day = Column(Boolean, default=False)
    visibility = Column(String, default="public")  # public | private
    created_by = Column(String, nullable=True)
    created_by_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
