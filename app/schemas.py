from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    company_id: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    company_id: str | None = None
    email: str
    name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "cashier"
    company_id: str | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class CompanyBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    logo: str | None = None
    currency: str = "USD"
    currency_symbol: str = "$"
    types: list[str] = []
    subscription_plan: str = "free"
    subscription_plan_id: str | None = None
    subscription_expiry: datetime | None = None
    is_active: bool = True

    # Enhanced company details for professional documents
    vrn_no: str | None = None
    tin_no: str | None = None
    website: str | None = None
    physical_address: str | None = None
    postal_address: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    postal_code: str | None = None
    
    # Business details
    business_license_no: str | None = None
    business_registration_no: str | None = None
    business_type: str | None = None
    industry: str | None = None
    year_established: int | None = None
    
    # Contact details
    contact_person: str | None = None
    contact_person_title: str | None = None
    alternative_phone: str | None = None
    fax: str | None = None
    whatsapp: str | None = None
    
    # Social media
    facebook: str | None = None
    twitter: str | None = None
    instagram: str | None = None
    linkedin: str | None = None
    
    # Document settings
    document_prefix: str | None = None
    document_footer: str | None = None
    document_header: str | None = None
    authorised_signatory: str | None = None


class CompanyCreate(CompanyBase):
    admin_name: str
    admin_email: EmailStr
    admin_password: str
    bank_details: list["CompanyBankDetailCreate"] = []
    terms_conditions: list["CompanyTermsConditionCreate"] = []


class CompanyUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    logo: str | None = None
    currency: str | None = None
    currency_symbol: str | None = None
    types: list[str] | None = None
    subscription_plan: str | None = None
    subscription_plan_id: str | None = None
    subscription_expiry: datetime | None = None
    is_active: bool | None = None

    # Enhanced company details
    vrn_no: str | None = None
    tin_no: str | None = None
    website: str | None = None
    physical_address: str | None = None
    postal_address: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    postal_code: str | None = None
    business_license_no: str | None = None
    business_registration_no: str | None = None
    business_type: str | None = None
    industry: str | None = None
    year_established: int | None = None
    contact_person: str | None = None
    contact_person_title: str | None = None
    alternative_phone: str | None = None
    fax: str | None = None
    whatsapp: str | None = None
    facebook: str | None = None
    twitter: str | None = None
    instagram: str | None = None
    linkedin: str | None = None
    document_prefix: str | None = None
    document_footer: str | None = None
    document_header: str | None = None
    authorised_signatory: str | None = None
    bank_details: list["CompanyBankDetailCreate"] | None = None
    terms_conditions: list["CompanyTermsConditionCreate"] | None = None


class CompanyOut(CompanyBase):
    id: str
    created_at: datetime
    updated_at: datetime
    bank_details: list["CompanyBankDetailOut"] = []
    terms_conditions: list["CompanyTermsConditionOut"] = []

    class Config:
        from_attributes = True


class CompanyBankDetailBase(BaseModel):
    bank_name: str
    account_name: str
    account_number: str
    branch_name: str | None = None
    branch_code: str | None = None
    swift_code: str | None = None
    iban: str | None = None
    routing_number: str | None = None
    sort_code: str | None = None
    bank_address: str | None = None
    mobile_money_name: str | None = None
    mobile_money_number: str | None = None
    is_primary: bool = False
    is_active: bool = True


class CompanyBankDetailCreate(CompanyBankDetailBase):
    pass


class CompanyBankDetailUpdate(BaseModel):
    bank_name: str | None = None
    account_name: str | None = None
    account_number: str | None = None
    branch_name: str | None = None
    branch_code: str | None = None
    swift_code: str | None = None
    iban: str | None = None
    routing_number: str | None = None
    sort_code: str | None = None
    bank_address: str | None = None
    mobile_money_name: str | None = None
    mobile_money_number: str | None = None
    is_primary: bool | None = None
    is_active: bool | None = None


class CompanyBankDetailOut(CompanyBankDetailBase):
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyTermsConditionBase(BaseModel):
    document_type: str
    title: str | None = None
    terms_text: str | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    warranty_terms: str | None = None
    return_policy: str | None = None
    late_payment_terms: str | None = None
    cancellation_policy: str | None = None
    is_active: bool = True


class CompanyTermsConditionCreate(CompanyTermsConditionBase):
    pass


class CompanyTermsConditionUpdate(BaseModel):
    document_type: str | None = None
    title: str | None = None
    terms_text: str | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    warranty_terms: str | None = None
    return_policy: str | None = None
    late_payment_terms: str | None = None
    cancellation_policy: str | None = None
    is_active: bool | None = None


class CompanyTermsConditionOut(CompanyTermsConditionBase):
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionPlanBase(BaseModel):
    name: str
    price: float = 0
    billing_cycle: str = "monthly"
    max_users: int = 1
    max_products: int = 100
    max_locations: int = 1
    features: list[str] = []
    is_active: bool = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    billing_cycle: str | None = None
    max_users: int | None = None
    max_products: int | None = None
    max_locations: int | None = None
    features: list[str] | None = None
    is_active: bool | None = None


class SubscriptionPlanOut(SubscriptionPlanBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResourceBase(BaseModel):
    id: str | None = None
    company_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CategoryIn(ResourceBase):
    parent_id: str | None = None
    name: str
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True


class ProductIn(ResourceBase):
    category_id: str | None = None
    sku: str
    qr_code: str | None = None
    barcode: str | None = None
    name: str
    unit: str = "piece"
    cost_price: float = 0
    selling_price: float = 0
    quantity: float = 0
    min_stock: float = 0
    
    # Pharmacy fields
    generic_name: str | None = None
    brand_name: str | None = None
    dosage: str | None = None
    form: str | None = None
    requires_prescription: bool = False
    units_per_pack: int = 1
    
    is_active: bool = True


class ProductBatchIn(ResourceBase):
    product_id: str
    batch_number: str
    expiry_date: datetime
    quantity: float = 0
    cost_price: float | None = None
    selling_price: float | None = None


class CustomerIn(ResourceBase):
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    
    # Enhanced customer details for documents
    customer_number: str | None = None
    tax_id: str | None = None
    vrn_no: str | None = None
    physical_address: str | None = None
    postal_address: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    postal_code: str | None = None
    
    # Business details for B2B customers
    business_name: str | None = None
    business_type: str | None = None
    contact_person: str | None = None
    contact_person_title: str | None = None
    website: str | None = None
    
    # Shipping details
    shipping_address: str | None = None
    shipping_city: str | None = None
    shipping_region: str | None = None
    shipping_country: str | None = None
    shipping_postal_code: str | None = None
    
    credit_limit: float = 0
    current_debt: float = 0
    is_active: bool = True


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    customer_number: str | None = None
    tax_id: str | None = None
    vrn_no: str | None = None
    physical_address: str | None = None
    postal_address: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    postal_code: str | None = None
    business_name: str | None = None
    business_type: str | None = None
    contact_person: str | None = None
    contact_person_title: str | None = None
    website: str | None = None
    shipping_address: str | None = None
    shipping_city: str | None = None
    shipping_region: str | None = None
    shipping_country: str | None = None
    shipping_postal_code: str | None = None
    credit_limit: float | None = None
    current_debt: float | None = None
    is_active: bool | None = None


class CustomerOut(CustomerIn):
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupplierIn(ResourceBase):
    name: str
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    payment_terms: str | None = None
    current_debt: float = 0
    is_active: bool = True


class TransactionIn(ResourceBase):
    transaction_number: str
    type: str = "sale"
    status: str = "completed"
    customer_id: str | None = None
    customer_name: str | None = None
    items: list[dict[str, Any]] = []
    subtotal: float = 0
    discount_amount: float = 0
    tax_amount: float = 0
    total: float = 0
    payment_method: str = "cash"
    amount_paid: float = 0
    amount_due: float = 0
    cashier_id: str | None = None
    cashier_name: str | None = None
    notes: str | None = None


class PurchaseOrderIn(ResourceBase):
    order_number: str
    supplier_id: str
    supplier_name: str
    status: str = "ordered"
    items: list[dict[str, Any]] = []
    subtotal: float = 0
    discount_amount: float = 0
    tax_amount: float = 0
    shipping_cost: float = 0
    other_costs: float = 0
    total: float = 0
    amount_paid: float = 0
    amount_due: float = 0
    expected_date: datetime | None = None
    received_date: datetime | None = None
    notes: str | None = None


class StaffSalaryIn(ResourceBase):
    staff_id: str
    staff_name: str
    amount: float = 0
    payment_date: datetime | None = None
    payment_method: str = "cash"
    status: str = "paid"
    month: str
    notes: str | None = None


class ExpenditureIn(ResourceBase):
    category: str
    amount: float = 0
    date: datetime | None = None
    payment_method: str = "cash"
    description: str | None = None
    reference_number: str | None = None


ResourceType = Literal["categories", "products", "customers", "suppliers", "transactions", "purchase_orders", "staff_salaries", "expenditures"]


class AdvertisementBase(BaseModel):
    title: str
    content: str
    image_url: str | None = None
    media_type: str = "image"
    link_url: str | None = None
    target: str = "all"
    placements: list[str] = []
    start_date: datetime
    end_date: datetime
    is_active: bool = True


class AdvertisementCreate(AdvertisementBase):
    pass


class AdvertisementOut(AdvertisementBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Forward references to resolve circular dependencies
CompanyCreate.model_rebuild()
CompanyUpdate.model_rebuild()
CompanyOut.model_rebuild()
