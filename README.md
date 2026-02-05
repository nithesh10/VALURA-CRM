# CRM API (FastAPI + Freshworks)

FastAPI backend that exposes **list all contacts** and **list all deals** from Freshworks CRM, with built-in **Swagger UI**.

## Setup

1. **Copy env and set your Freshworks credentials**

   ```bash
   copy env.example .env
   ```

   Edit `.env` and set:
   - `FRESHWORKS_DOMAIN` – your bundle alias (e.g. `yourcompany`)
   - `FRESHWORKS_API_KEY` – from Profile Settings → API Settings in Freshworks CRM

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**

   ```bash
   uvicorn app.main:app --reload
   ```

   By default the app is at **http://127.0.0.1:8000**.

## Export deals to Excel

Use `scripts/export_deals_to_excel.py` to export **all deals**, their **linked contact(s)**, and the **sales owner** into an Excel file.

1. Set `FRESHWORKS_DOMAIN` and `FRESHWORKS_API_KEY` in `.env`.
2. Run:

   ```bash
   python scripts/export_deals_to_excel.py --output "./deals.xlsx"
   ```

## Swagger UI

- **Swagger UI:** http://127.0.0.1:8000/docs  
- **ReDoc:** http://127.0.0.1:8000/redoc  

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/contacts/filters` | List contact view IDs (use one in `/contacts`) |
| GET | `/contacts` | **List all contacts** (paginated) |
| GET | `/deals/filters` | List deal view IDs (use one in `/deals`) |
| GET | `/deals` | **List all deals** (paginated) |
| GET | `/health` | Health check |

Optional query params for `/contacts` and `/deals`: `page`, `per_page`, `sort`, `sort_type`, `include`, `view_id`.

## Verify with curl (Freshworks API)

Use these **correct** URLs (path is `api/contacts`, not `apicontacts`):

**Contact filters (list view IDs):**
```bash
curl -H "Authorization: Token token=YOUR_API_KEY" -H "Content-Type: application/json" -X GET "https://YOUR_DOMAIN.myfreshworks.com/crm/sales/api/contacts/filters"
```

**Single contact by ID (e.g. id=1) with owner:**
```bash
curl -H "Authorization: Token token=YOUR_API_KEY" -H "Content-Type: application/json" -X GET "https://YOUR_DOMAIN.myfreshworks.com/crm/sales/api/contacts/1?include=owner"
```

**List contacts for a view (e.g. view_id=3):**
```bash
curl -H "Authorization: Token token=YOUR_API_KEY" -H "Content-Type: application/json" -X GET "https://YOUR_DOMAIN.myfreshworks.com/crm/sales/api/contacts/view/3"
```

Replace `YOUR_DOMAIN` with your bundle alias and `YOUR_API_KEY` with your API key. Our app uses the same base URL, headers, and path pattern (`/api/contacts/...`, `/api/deals/...`).
"# VALURA-CRM" 
