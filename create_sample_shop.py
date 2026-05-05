#!/usr/bin/env python3
"""
Sample Data Generator for Amazooh Shop
Creates a comprehensive shop with inventory, customers, sales, and enhanced company details
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.models import (
    Company, User, Product, Category, Customer, Transaction, 
    CompanyBankDetail, CompanyTermsCondition
)
from app.database import SessionLocal, engine
from app.models import Base
import uuid
from datetime import datetime, timedelta
import random

def create_sample_shop():
    """Create Amazooh shop with comprehensive sample data"""
    
    # Create database session
    db = SessionLocal()
    
    try:
        print("🚀 Creating Amazooh sample shop...")
        
        # Create Company with Enhanced Details
        print("📋 Creating company with enhanced details...")
        company = Company(
            id=str(uuid.uuid4()),
            name="Amazooh Electronics Ltd",
            types=["retail", "electronics"],
            email="info@amazooh.com",
            phone="+255 712 345 678",
            address="Uhuru Street, Plot 123",
            tax_id="123-456-789",
            currency="TSH",
            currency_symbol="TSh",
            subscription_plan="pro",
            is_active=True,
            # Enhanced company details
            vrn_no="VRN-40-123456-T",
            tin_no="101234567",
            website="https://www.amazooh.co.tz",
            physical_address="Uhuru Street, Plot 123, Dar es Salaam, Tanzania",
            postal_address="P.O. Box 12345, Dar es Salaam, Tanzania",
            country="Tanzania",
            region="Dar es Salaam",
            city="Dar es Salaam",
            postal_code="12345",
            business_license_no="BL-2023-DSM-456789",
            business_registration_no="RC-2020-123456",
            business_type="Limited Company",
            industry="Electronics Retail",
            year_established=2020,
            contact_person="John Mwangi",
            contact_person_title="Managing Director",
            alternative_phone="+255 754 987 654",
            fax="+255 22 123 4567",
            whatsapp="+255 712 345 678",
            facebook="https://facebook.com/amazooh",
            twitter="https://twitter.com/amazooh_tz",
            instagram="https://instagram.com/amazooh",
            linkedin="https://linkedin.com/company/amazooh",
            document_prefix="AMZ-",
            document_header="AMAZOOH ELECTRONICS LTD | Quality Electronics, Best Prices",
            document_footer="Thank you for your business! | Visit us again | Warranty: 1 Year on all products",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(company)
        db.flush()  # Get the company ID
        
        print(f"✅ Company created: {company.name} (ID: {company.id})")

        # Create Bank Details
        print("💳 Creating bank details...")
        bank_details = [
            CompanyBankDetail(
                id=str(uuid.uuid4()),
                company_id=company.id,
                bank_name="National Bank of Commerce",
                account_name="Amazooh Electronics Ltd",
                account_number="0123456789012",
                branch_name="Kijitonyama Branch",
                branch_code="001",
                swift_code="NBCTTZTZ",
                iban="TZ96 NBCT 0010 1234 5678 9012 3456 789",
                bank_address="Kijitonyama, Dar es Salaam, Tanzania",
                is_primary=True,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            CompanyBankDetail(
                id=str(uuid.uuid4()),
                company_id=company.id,
                bank_name="CRDB Bank",
                account_name="Amazooh Electronics Ltd",
                account_number="0156789012345",
                branch_name="City Centre Branch",
                branch_code="002",
                swift_code="CORUTZTZ",
                bank_address="Ohio Street, Dar es Salaam, Tanzania",
                is_primary=False,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        for bank in bank_details:
            db.add(bank)
        
        print(f"✅ Created {len(bank_details)} bank accounts")

        # Create Terms & Conditions
        print("📝 Creating terms & conditions...")
        terms_conditions = [
            CompanyTermsCondition(
                id=str(uuid.uuid4()),
                company_id=company.id,
                document_type="invoice",
                title="Invoice Terms & Conditions",
                terms_text="All prices are in Tanzanian Shillings. Payment due within 30 days.",
                payment_terms="Payment due within 30 days from invoice date. Late payment subject to 2% monthly interest.",
                delivery_terms="Delivery within 7 business days for in-stock items. Special orders may take 2-3 weeks.",
                warranty_terms="All products come with 1-year manufacturer warranty. Extended warranty available for purchase.",
                return_policy="Returns accepted within 7 days of purchase with original receipt. Item must be in original condition.",
                late_payment_terms="Late payments subject to 2% monthly interest on outstanding balance.",
                cancellation_policy="Orders can be cancelled before shipping. 10% cancellation fee may apply.",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            CompanyTermsCondition(
                id=str(uuid.uuid4()),
                company_id=company.id,
                document_type="quotation",
                title="Quotation Terms & Conditions",
                terms_text="Prices valid for 30 days from quotation date.",
                payment_terms="50% advance payment required for order confirmation.",
                delivery_terms="Delivery within 14 business days after order confirmation.",
                warranty_terms="Standard warranty applies as per manufacturer terms.",
                return_policy="Return policy as per invoice terms.",
                late_payment_terms="Not applicable for quotations.",
                cancellation_policy="Quotation valid for 30 days. Prices subject to change after validity period.",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        for terms in terms_conditions:
            db.add(terms)
        
        print(f"✅ Created {len(terms_conditions)} terms & conditions")

        # Create Admin User
        print("👤 Creating admin user...")
        admin_user = User(
                id=str(uuid.uuid4()),
                company_id=company.id,
                email="admin@amazooh.com",
                name="John Mwangi",
                role="admin",
                password_hash="$2b$12$/U2zSFfbXI2bWudgZzpFWe4idI.5RMz1VCmXGL14uskQXchKYiI1i",  # password: admin123
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        db.add(admin_user)
        
        print(f"✅ Admin user created: {admin_user.email}")

        # Create Categories
        print("📂 Creating categories...")
        categories_data = [
            {"name": "Smartphones", "description": "Latest smartphones and accessories"},
            {"name": "Laptops", "description": "Laptops and computer accessories"},
            {"name": "Tablets", "description": "Tablets and e-readers"},
            {"name": "Audio", "description": "Headphones, speakers, and audio equipment"},
            {"name": "Accessories", "description": "Phone accessories, cables, and cases"},
            {"name": "Gaming", "description": "Gaming consoles and accessories"}
        ]
        
        categories = []
        for cat_data in categories_data:
            category = Category(
                id=str(uuid.uuid4()),
                company_id=company.id,
                name=cat_data["name"],
                description=cat_data["description"],
                sort_order=len(categories),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(category)
            categories.append(category)
        
        print(f"✅ Created {len(categories)} categories")

        # Create Products
        print("📱 Creating products...")
        products_data = [
            # Smartphones
            {"name": "iPhone 15 Pro", "sku": "IP15PRO-128", "category": "Smartphones", "cost": 1800000, "selling": 2200000, "stock": 25},
            {"name": "Samsung Galaxy S24", "sku": "SGS24-256", "category": "Smartphones", "cost": 1500000, "selling": 1850000, "stock": 30},
            {"name": "Xiaomi 14 Pro", "sku": "XM14P-512", "category": "Smartphones", "cost": 1200000, "selling": 1450000, "stock": 20},
            {"name": "Tecno Phantom X2", "sku": "TPX2-256", "category": "Smartphones", "cost": 800000, "selling": 950000, "stock": 40},
            
            # Laptops
            {"name": "MacBook Air M2", "sku": "MBA-M2-256", "category": "Laptops", "cost": 2500000, "selling": 3200000, "stock": 15},
            {"name": "Dell XPS 13", "sku": "DXP13-512", "category": "Laptops", "cost": 1800000, "selling": 2200000, "stock": 12},
            {"name": "HP Pavilion 15", "sku": "HP15-8GB", "category": "Laptops", "cost": 1200000, "selling": 1450000, "stock": 18},
            
            # Tablets
            {"name": "iPad Pro 11", "sku": "IPP11-128", "category": "Tablets", "cost": 1500000, "selling": 1850000, "stock": 20},
            {"name": "Samsung Galaxy Tab S9", "sku": "SGTS9-256", "category": "Tablets", "cost": 1200000, "selling": 1450000, "stock": 15},
            
            # Audio
            {"name": "AirPods Pro 2", "sku": "APP2-GEN2", "category": "Audio", "cost": 350000, "selling": 450000, "stock": 50},
            {"name": "Sony WH-1000XM5", "sku": "SWH-XM5", "category": "Audio", "cost": 450000, "selling": 550000, "stock": 25},
            {"name": "JBL Flip 6", "sku": "JBLF6-BLK", "category": "Audio", "cost": 150000, "selling": 200000, "stock": 60},
            
            # Accessories
            {"name": "iPhone 15 Case", "sku": "IP15C-CLR", "category": "Accessories", "cost": 25000, "selling": 45000, "stock": 100},
            {"name": "USB-C Cable 2m", "sku": "USBC-2M", "category": "Accessories", "cost": 8000, "selling": 15000, "stock": 200},
            {"name": "Screen Protector Tempered", "sku": "SP-TEMP", "category": "Accessories", "cost": 12000, "selling": 25000, "stock": 150},
            
            # Gaming
            {"name": "PlayStation 5", "sku": "PS5-STD", "category": "Gaming", "cost": 800000, "selling": 950000, "stock": 10},
            {"name": "Xbox Series X", "sku": "XSX-1TB", "category": "Gaming", "cost": 750000, "selling": 900000, "stock": 8},
            {"name": "Nintendo Switch", "sku": "NSW-RED", "category": "Gaming", "cost": 450000, "selling": 550000, "stock": 20}
        ]
        
        products = []
        for prod_data in products_data:
            category = next(c for c in categories if c.name == prod_data["category"])
            product = Product(
                id=str(uuid.uuid4()),
                company_id=company.id,
                category_id=category.id,
                sku=prod_data["sku"],
                name=prod_data["name"],
                cost_price=prod_data["cost"],
                selling_price=prod_data["selling"],
                quantity=prod_data["stock"],
                min_stock=5,
                unit="piece",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(product)
            products.append(product)
        
        print(f"✅ Created {len(products)} products")

        # Create Customers with Enhanced Details
        print("👥 Creating customers...")
        customers_data = [
            {
                "name": "Alice Johnson",
                "business_name": "Alice Tech Solutions",
                "phone": "+255 712 111 222",
                "email": "alice@techsolutions.co.tz",
                "address": "Kinondoni, Dar es Salaam",
                "vrn_no": "VRN-40-111222-T",
                "contact_person": "Alice Johnson",
                "contact_person_title": "CEO"
            },
            {
                "name": "Bob Smith",
                "phone": "+255 713 333 444",
                "email": "bob.smith@email.com",
                "address": "Ilala, Dar es Salaam"
            },
            {
                "name": "Carol Williams",
                "business_name": "Carol Electronics",
                "phone": "+255 714 555 666",
                "email": "carol@carol-electronics.com",
                "address": "Temeke, Dar es Salaam",
                "shipping_address": "Industrial Area, Temeke",
                "vrn_no": "VRN-40-555666-T",
                "website": "https://carol-electronics.com"
            },
            {
                "name": "David Brown",
                "phone": "+255 715 777 888",
                "email": "david.brown@gmail.com",
                "address": "Ubungo, Dar es Salaam",
                "alternative_phone": "+255 715 777 999"
            },
            {
                "name": "Eva Davis",
                "business_name": "Eva Mobile Shop",
                "phone": "+255 716 999 000",
                "email": "eva@evamobile.co.tz",
                "address": "Mikocheni, Dar es Salaam",
                "contact_person": "Eva Davis",
                "contact_person_title": "Manager"
            }
        ]
        
        customers = []
        for cust_data in customers_data:
            customer = Customer(
                id=str(uuid.uuid4()),
                company_id=company.id,
                name=cust_data["name"],
                phone=cust_data["phone"],
                email=cust_data.get("email"),
                address=cust_data.get("address"),
                credit_limit=500000,
                current_debt=0,
                # Enhanced customer details
                customer_number=f"CUST{1000 + len(customers):04d}",
                tax_id=cust_data.get("tax_id"),
                vrn_no=cust_data.get("vrn_no"),
                business_name=cust_data.get("business_name"),
                contact_person=cust_data.get("contact_person"),
                contact_person_title=cust_data.get("contact_person_title"),
                shipping_address=cust_data.get("shipping_address"),
                website=cust_data.get("website"),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(customer)
            customers.append(customer)
        
        print(f"✅ Created {len(customers)} customers")

        # Create Sample Sales Transactions
        print("💰 Creating sample sales transactions...")
        transactions = []
        
        for i in range(20):  # Create 20 sample transactions
            # Random customer (including walk-in)
            customer = random.choice(customers) if random.random() > 0.3 else None
            
            # Create transaction
            transaction = Transaction(
                id=str(uuid.uuid4()),
                company_id=company.id,
                transaction_number=f"AMZ-INV-{1000 + i:04d}",
                type="sale",
                status="completed",
                customer_id=customer.id if customer else None,
                customer_name=customer.name if customer else "Walk-in Customer",
                subtotal=0,  # Will be calculated
                discount_amount=random.randint(0, 50000),
                tax_amount=0,  # Will be calculated
                total=0,  # Will be calculated
                payment_method=random.choice(["cash", "card", "mobile"]),
                amount_paid=0,  # Will be calculated
                amount_due=0,  # Will be calculated
                cashier_id=admin_user.id,
                cashier_name=admin_user.name,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                updated_at=datetime.utcnow()
            )
            
            # Add random items to transaction
            num_items = random.randint(1, 4)
            selected_products = random.sample(products, min(num_items, len(products)))
            
            subtotal = 0
            items_json = []
            
            for product in selected_products:
                quantity = random.randint(1, 3)
                unit_price = product.selling_price
                total_price = quantity * unit_price
                subtotal += total_price
                
                # Create item JSON structure
                item_data = {
                    "id": str(uuid.uuid4()),
                    "product_id": product.id,
                    "product_name": product.name,
                    "sku": product.sku,
                    "quantity": quantity,
                    "unit": "piece",
                    "unit_price": unit_price,
                    "cost_price": product.cost_price,
                    "discount_amount": 0,
                    "discount_percent": 0,
                    "total": total_price
                }
                items_json.append(item_data)
            
            # Calculate totals
            discount_amount = transaction.discount_amount
            discounted_subtotal = subtotal - discount_amount
            tax_amount = discounted_subtotal * 0.18  # 18% tax
            total = discounted_subtotal + tax_amount
            
            # Update transaction totals and items
            transaction.items = items_json
            transaction.subtotal = subtotal
            transaction.discount_amount = discount_amount
            transaction.tax_amount = tax_amount
            transaction.total = total
            transaction.amount_paid = total
            transaction.change = 0
            transaction.amount_due = 0
            
            db.add(transaction)
            
            transactions.append(transaction)
        
        print(f"✅ Created {len(transactions)} sample transactions")

        # Commit all changes
        db.commit()
        
        print("\n🎉 Amazooh sample shop created successfully!")
        print("\n📋 LOGIN CREDENTIALS:")
        print("=" * 50)
        print("🌐 Next.js Web App:")
        print("   URL: http://localhost:3000")
        print("   Email: admin@amazooh.com")
        print("   Password: admin123")
        print("\n📱 Flutter App:")
        print("   Email: admin@amazooh.com")
        print("   Password: admin123")
        print("=" * 50)
        
        print("\n📊 Shop Summary:")
        print(f"   📱 Products: {len(products)}")
        print(f"   📂 Categories: {len(categories)}")
        print(f"   👥 Customers: {len(customers)}")
        print(f"   💰 Transactions: {len(transactions)}")
        print(f"   💳 Bank Accounts: {len(bank_details)}")
        print(f"   📝 Terms & Conditions: {len(terms_conditions)}")
        
        print("\n🎯 Enhanced Features Available:")
        print("   ✅ Professional company details (VRN/TIN, addresses, contacts)")
        print("   ✅ Multiple bank accounts for payments")
        print("   ✅ Document terms & conditions")
        print("   ✅ Enhanced customer information")
        print("   ✅ Professional document generation")
        
        return company
        
    except Exception as e:
        print(f"❌ Error creating sample shop: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting Amazooh sample shop creation...")
    create_sample_shop()
    print("\n✅ Script completed successfully!")
