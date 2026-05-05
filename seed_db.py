import uuid
import qrcode
import io
import base64
import sys
import os
from datetime import datetime, timedelta

# Add the current directory to sys.path so we can import app
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine, Base
from app.models import Company, User, Category, Product, Customer, Transaction, Expenditure, StaffSalary, Supplier, Debt
from app.security import hash_password

def seed_data():
    # Ensure tables exist
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Create Super Admin (Global Admin)
        super_admin_email = "amali@gmail.com"
        super_admin_password = "amali123"
        
        super_admin = db.query(User).filter(User.email == super_admin_email).first()
        
        if not super_admin:
            print(f"Creating Super Admin: {super_admin_email}...")
            super_admin = User(
                id=str(uuid.uuid4()),
                email=super_admin_email,
                name="Amali Super Admin",
                role="super_admin",
                password_hash=hash_password(super_admin_password),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            print(f"Super Admin created successfully!")
        else:
            print(f"Super Admin {super_admin_email} already exists. Updating password...")
            super_admin.password_hash = hash_password(super_admin_password)
            super_admin.role = "super_admin"
            db.commit()
            print(f"Super Admin updated successfully!")

        # 2. Create Sample Company
        company_email = "hardware@amali.com"
        company = db.query(Company).filter(Company.email == company_email).first()
        
        if not company:
            print(f"Creating sample company: Amali Hardware...")
            company_id = str(uuid.uuid4())
            company = Company(
                id=company_id,
                name="Amali Hardware",
                email=company_email,
                phone="0700000000",
                address="Dar es Salaam, Tanzania",
                types=["hardware"],
                subscription_plan="pro",
                subscription_expiry=datetime.utcnow() + timedelta(days=365),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(company)
            db.commit()
            db.refresh(company)
        
        company_id = company.id

        # 3. Create a Regular Admin for the company
        admin_email = "admin@amali.com"
        company_admin = db.query(User).filter(User.email == admin_email).first()
        if not company_admin:
            print(f"Creating Company Admin: {admin_email}...")
            company_admin = User(
                id=str(uuid.uuid4()),
                company_id=company_id,
                email=admin_email,
                name="Hardware Admin",
                role="admin",
                password_hash=hash_password("amali123"),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(company_admin)
            db.commit()
            print(f"Company Admin created successfully!")

        # Clear existing sample data for this company to avoid duplicates
        print(f"Clearing existing sample data for company {company.name}...")
        db.query(Transaction).filter(Transaction.company_id == company_id).delete()
        db.query(Expenditure).filter(Expenditure.company_id == company_id).delete()
        db.query(StaffSalary).filter(StaffSalary.company_id == company_id).delete()
        db.query(Debt).filter(Debt.company_id == company_id).delete()
        db.query(Product).filter(Product.company_id == company_id).delete()
        db.query(Category).filter(Category.company_id == company_id).delete()
        db.query(Customer).filter(Customer.company_id == company_id).delete()
        db.commit()

        # 4. Seed Categories
        categories_data = [
            {"id": str(uuid.uuid4()), "name": "Vifaa vya Ujenzi", "description": "Construction materials"},
            {"id": str(uuid.uuid4()), "name": "Vifaa vya Umeme", "description": "Electrical supplies"},
            {"id": str(uuid.uuid4()), "name": "Rangi", "description": "Paints and coatings"},
            {"id": str(uuid.uuid4()), "name": "Mbao na Mabati", "description": "Wood and roofing sheets"},
        ]
        
        for cat in categories_data:
            db_cat = Category(
                id=cat["id"],
                company_id=company_id,
                name=cat["name"],
                description=cat["description"]
            )
            db.add(db_cat)
        
        db.commit()
        print(f"Added {len(categories_data)} categories.")

        # 5. Seed Products
        products_data = [
            {"name": "Sementi (Dangote)", "price": 18500, "cost": 16000, "qty": 150, "min": 20, "cat": categories_data[0]["id"]},
            {"name": "Nondo 12mm", "price": 24000, "cost": 21000, "qty": 80, "min": 10, "cat": categories_data[0]["id"]},
            {"name": "Waya wa Umeme 1.5mm", "price": 45000, "cost": 38000, "qty": 25, "min": 5, "cat": categories_data[1]["id"]},
            {"name": "Swichi ya Taa (Double)", "price": 5500, "cost": 3500, "qty": 40, "min": 10, "cat": categories_data[1]["id"]},
            {"name": "Rangi ya Mafuta (Lita 4)", "price": 32000, "cost": 27000, "qty": 15, "min": 5, "cat": categories_data[2]["id"]},
            {"name": "Mabati ya Rangi (Gauge 28)", "price": 28000, "cost": 24500, "qty": 100, "min": 20, "cat": categories_data[3]["id"]},
            {"name": "Mbao 2x4 (Futi 12)", "price": 8500, "cost": 6500, "qty": 200, "min": 50, "cat": categories_data[3]["id"]},
        ]

        products = []
        for p in products_data:
            sku = f"SKU-{p['name'][:3].upper()}-{uuid.uuid4().hex[:4].upper()}"
            
            # Generate QR Code (Base64)
            qr_obj = qrcode.QRCode(version=1, box_size=10, border=5)
            qr_obj.add_data(sku)
            qr_obj.make(fit=True)
            img = qr_obj.make_image(fill_color="black", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

            db_p = Product(
                id=str(uuid.uuid4()),
                company_id=company_id,
                category_id=p["cat"],
                sku=sku,
                qr_code=qr_code_base64,
                barcode=sku,
                name=p["name"],
                unit="pcs",
                cost_price=p["cost"],
                selling_price=p["price"],
                quantity=p["qty"],
                min_stock=p["min"]
            )
            db.add(db_p)
            products.append(db_p)
        
        db.commit()
        print(f"Added {len(products_data)} products.")

        # 6. Seed Customers
        customers_data = [
            {"name": "John Builder", "phone": "0712345678", "limit": 1000000},
            {"name": "Anna Electrician", "phone": "0755998877", "limit": 500000},
            {"name": "Kassim Contractors", "phone": "0622334455", "limit": 2000000},
        ]

        customers = []
        for c in customers_data:
            db_c = Customer(
                id=str(uuid.uuid4()),
                company_id=company_id,
                name=c["name"],
                phone=c["phone"],
                credit_limit=c["limit"]
            )
            db.add(db_c)
            customers.append(db_c)
        
        db.commit()
        print(f"Added {len(customers_data)} customers.")

        # 7. Seed Transactions (Sales)
        print("Seeding transactions...")
        for i in range(15):
            cust = customers[i % len(customers)]
            prod = products[i % len(products)]
            qty = (i % 5) + 1
            total = prod.selling_price * qty
            
            # Seed 8 transactions for today, 7 for previous days
            days_ago = 0 if i < 8 else (i - 7)
            
            txn = Transaction(
                id=str(uuid.uuid4()),
                company_id=company_id,
                transaction_number=f"TRX-{datetime.now().strftime('%Y%m%d')}-{i:04d}",
                type="sale",
                customer_id=cust.id,
                customer_name=cust.name,
                items=[{
                    "product_id": prod.id,
                    "name": prod.name,
                    "price": prod.selling_price,
                    "quantity": qty,
                    "total": total
                }],
                subtotal=total,
                total=total,
                amount_paid=total if i % 3 != 0 else total * 0.5,
                amount_due=0 if i % 3 != 0 else total * 0.5,
                payment_method="cash" if i % 2 == 0 else "mobile_money",
                cashier_id=company_admin.id if company_admin.id else str(uuid.uuid4()),
                cashier_name=company_admin.name,
                created_at=datetime.utcnow() - timedelta(days=days_ago)
            )
            db.add(txn)
        
        db.commit()
        print("Added 15 sample transactions.")

        # 8. Seed Expenditures
        exp_data = [
            {"cat": "Rent", "amt": 500000, "desc": "Monthly shop rent"},
            {"cat": "Utilities", "amt": 45000, "desc": "Electricity bill"},
            {"cat": "Transport", "amt": 120000, "desc": "Stock delivery costs"},
        ]

        for e in exp_data:
            db_e = Expenditure(
                id=str(uuid.uuid4()),
                company_id=company_id,
                category=e["cat"],
                amount=e["amt"],
                description=e["desc"],
                date=datetime.utcnow() - timedelta(days=5)
            )
            db.add(db_e)
        
        db.commit()
        print(f"Added {len(exp_data)} expenditures.")

        # 9. Seed Staff Salaries
        salaries_data = [
            {"name": "James Mallya", "amt": 350000, "month": "2024-03"},
            {"name": "Sarah Omary", "amt": 300000, "month": "2024-03"},
        ]

        for s in salaries_data:
            db_s = StaffSalary(
                id=str(uuid.uuid4()),
                company_id=company_id,
                staff_id=str(uuid.uuid4()),
                staff_name=s["name"],
                amount=s["amt"],
                month=s["month"],
                payment_date=datetime.utcnow() - timedelta(days=2)
            )
            db.add(db_s)
        
        db.commit()
        print(f"Added {len(salaries_data)} salary records.")

        print("\nSUCCESS: PostgreSQL database seeded with Super Admin and Sample Data!")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
