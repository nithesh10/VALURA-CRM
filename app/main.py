from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from typing import Optional, List
import os
from pathlib import Path

# Using Freshworks API
from app.services.freshworks_service import FreshworksService
from app.services.analytics_service import AnalyticsService

app = FastAPI(
    title="Valura CRM Dashboard",
    description="CRM Dashboard with Freshworks API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services with Freshworks API
freshworks_service = FreshworksService()
analytics_service = AnalyticsService(freshworks_service)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard"""
    dashboard_path = Path(__file__).parent.parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return HTMLResponse("<h1>Dashboard not found. Please create static/dashboard.html</h1>")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

# ============================================
# 1. All Contacts
# ============================================
@app.get("/api/contacts")
async def get_all_contacts(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100)
):
    """Get all contacts in tabular format"""
    try:
        contacts = await freshworks_service.get_all_contacts(page=page, per_page=per_page)
        return {
            "success": True,
            "data": contacts.get("contacts", []),
            "meta": contacts.get("meta", {}),
            "page": page,
            "per_page": per_page
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# 2. All Opportunities (Deals)
# ============================================
@app.get("/api/opportunities")
async def get_all_opportunities(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    pipeline_id: Optional[int] = None
):
    """Get all investment opportunities in tabular format"""
    try:
        opportunities = await freshworks_service.get_all_deals(page=page, per_page=per_page)
        deals = opportunities.get("deals", [])
        
        # Filter by pipeline if specified
        if pipeline_id:
            deals = [d for d in deals if d.get("deal_pipeline_id") == pipeline_id]
        
        return {
            "success": True,
            "data": deals,
            "meta": opportunities.get("meta", {}),
            "page": page,
            "per_page": per_page
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# 3. Contacts NOT in Opportunities
# ============================================
@app.get("/api/contacts-not-in-opportunities")
async def get_contacts_not_in_opportunities(pipeline_id: Optional[int] = None):
    """Get contacts that are not associated with any opportunities"""
    try:
        result = await analytics_service.get_contacts_without_opportunities(pipeline_id=pipeline_id)
        return {
            "success": True,
            "data": result,
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# 4. Contacts by Source (Referral, Walk-in, Online)
# ============================================
@app.get("/api/contacts-by-source")
async def get_contacts_by_source(source: Optional[str] = None, pipeline_id: Optional[int] = None):
    """
    Get contacts grouped by source type (Referral, Walk-in, Online Walk-in)
    Optional: filter by specific source and pipeline
    """
    try:
        result = await analytics_service.get_contacts_by_source(source_filter=source, pipeline_id=pipeline_id)
        return {
            "success": True,
            "data": result,
            "breakdown": {
                "referral": len(result.get("referral", [])),
                "walk_in": len(result.get("walk_in", [])),
                "online_walk_in": len(result.get("online_walk_in", [])),
                "other": len(result.get("other", []))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# 5. Opportunities Grouped by Stage
# ============================================
@app.get("/api/opportunities-by-stage")
async def get_opportunities_by_stage(stage: Optional[str] = None, pipeline_id: Optional[int] = None):
    """
    Get opportunities grouped by stage
    Optional: filter by specific stage and pipeline
    """
    try:
        result = await analytics_service.get_opportunities_by_stage(stage_filter=stage, pipeline_id=pipeline_id)
        return {
            "success": True,
            "data": result,
            "stages": list(result.keys()) if isinstance(result, dict) else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# 6. Leads by Sales Owner
# ============================================
@app.get("/api/leads-by-sales-owner")
async def get_leads_by_sales_owner(owner_id: Optional[int] = None, pipeline_id: Optional[int] = None):
    """
    Get leads/opportunities filtered by sales owner with all details
    Optional: filter by specific owner_id and pipeline_id
    """
    try:
        result = await analytics_service.get_leads_by_sales_owner(owner_id=owner_id, pipeline_id=pipeline_id)
        return {
            "success": True,
            "data": result,
            "owners": list(result.keys()) if isinstance(result, dict) else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# 7. Dashboard Summary
# ============================================
@app.get("/api/summary")
async def get_dashboard_summary(pipeline_id: Optional[int] = None):
    """
    Get aggregated dashboard summary with key metrics:
    - Total contacts and opportunities
    - Contacts without opportunities
    - Source breakdown
    - Top deal stages
    - Top sales owners
    """
    try:
        result = await analytics_service.get_dashboard_summary(pipeline_id=pipeline_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Utility Endpoints
# ============================================
@app.get("/api/sales-owners")
async def get_sales_owners():
    """Get list of all sales owners for filtering"""
    try:
        owners = await analytics_service.get_all_sales_owners()
        return {
            "success": True,
            "data": owners
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stages")
async def get_stages():
    """Get list of all opportunity stages"""
    try:
        stages = await analytics_service.get_all_stages()
        return {
            "success": True,
            "data": stages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pipelines")
async def get_pipelines():
    """Get list of all deal pipelines"""
    try:
        pipelines = await freshworks_service.get_all_pipelines()
        return {
            "success": True,
            "data": pipelines
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
