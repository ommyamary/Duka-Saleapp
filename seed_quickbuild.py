import uuid
import qrcode
import io
import base64
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Company, User, Category, Product, Customer, Transaction, Expenditure, StaffSalary, Supplier, Debt
from app.security import hash_password

def seed_data():
    db = SessionLocal()
    try:
        # Check if company exists
        email = "amali@gmail.com"
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"Creating default company and user {email}...")
            company_id = str(uuid.uuid4())
            company = Company(
                id=company_id,
                name="Amali Hardware",
                email="contact@amali.com",
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
            
            user = User(
                id=str(uuid.uuid4()),
                company_id=company_id,
                email=email,
                name="Amali Admin",
                role="admin",
                password_hash=hash_password("password123"),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(user)
            db.commit()
            print(f"Created user {email} with password: password123")
        else:
            company_id = user.company_id
            company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            print(f"Company for user {email} not found.")
            return

        print(f"Found company: {company.name} ({company_id})")

        # Clear existing data for this company to avoid duplicates
        print("Clearing existing data for this company...")
        db.query(Transaction).filter(Transaction.company_id == company_id).delete()
        db.query(Expenditure).filter(Expenditure.company_id == company_id).delete()
        db.query(StaffSalary).filter(StaffSalary.company_id == company_id).delete()
        db.query(Debt).filter(Debt.company_id == company_id).delete()
        db.query(Product).filter(Product.company_id == company_id).delete()
        db.query(Category).filter(Category.company_id == company_id).delete()
        db.query(Customer).filter(Customer.company_id == company_id).delete()
        db.commit()

        # 1. Seed Categories
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

        # 2. Seed Products
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

        # 3. Seed Customers
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

        # 4. Seed Transactions (Sales)
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
                cashier_id=user.id,
                cashier_name=user.name,
                created_at=datetime.utcnow() - timedelta(days=days_ago)
            )
            db.add(txn)
        
        db.commit()
        print("Added 15 sample transactions (8 for today).")

        # 5. Seed Expenditures
        exp_data = [
            {"cat": "Rent", "amt": 500000, "desc": "Monthly shop rent"},
            {"cat": "Utilities", "amt": 45000, "desc": "Electricity bill"},
            {"cat": "Transport", "amt": 120000, "desc": "Stock delivery costs"},
            {"cat": "Supplies", "amt": 15000, "desc": "Cleaning materials"},
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

        # 6. Seed Staff Salaries
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

        # 7. Seed Suppliers & Payable Debt
        print("Seeding suppliers and payable debts...")
        suppliers_data = [
            {"name": "Mtwara Cement Ltd", "phone": "0788112233", "debt": 2500000},
            {"name": "Steel Masters", "phone": "0755443322", "debt": 0},
        ]

        for s_data in suppliers_data:
            supplier = Supplier(
                id=str(uuid.uuid4()),
                company_id=company_id,
                name=s_data["name"],
                phone=s_data["phone"],
                current_debt=s_data["debt"],
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(supplier)
            
            if s_data["debt"] > 0:
                debt = Debt(
                    id=str(uuid.uuid4()),
                    company_id=company_id,
                    type="payable",
                    entity_type="supplier",
                    entity_id=supplier.id,
                    entity_name=supplier.name,
                    reference_type="manual",
                    reference_id="initial-seed",
                    reference_number="SEED-001",
                    original_amount=s_data["debt"],
                    paid_amount=0,
                    remaining_amount=s_data["debt"],
                    status="pending",
                    payments=[],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(debt)

        db.commit()
        print(f"Added {len(suppliers_data)} suppliers.")

        print("\nSUCCESS: Sample data seeded for QuickBuild!")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
