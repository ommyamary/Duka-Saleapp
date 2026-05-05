# SaaPOS FastAPI Backend

## Quick Start

1. Create a virtual environment and install dependencies:
   - `py -3 -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
2. Run the API:
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
3. Configure frontend env:
   - `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

## Included Functionality

- JWT authentication (`/auth/login`, `/auth/me`)
- Super admin bootstrapping (`superadmin@saapos.com` / `super123`)
- Super admin company management:
  - `POST /admin/companies`
  - `GET /admin/companies`
  - `PATCH /admin/companies/{company_id}`
  - `POST /admin/companies/logo-upload`
- Multi-tenant data APIs:
  - `GET/POST/PATCH/DELETE /tenant/{resource_name}`
  - resources: `categories`, `products`, `customers`, `suppliers`, `transactions`, `purchase_orders`

## Notes

- Uploads are served from `/uploads/*`.
- SQLite is used by default (`saapos.db`) for local development.
