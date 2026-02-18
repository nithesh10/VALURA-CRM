import httpx
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class FreshworksService:
    """Service to interact with Freshworks CRM API"""
    
    def __init__(self):
        self.domain = os.getenv("FRESHWORKS_DOMAIN")
        self.api_key = os.getenv("FRESHWORKS_API_KEY")
        self.contacts_view_id = os.getenv("CONTACTS_VIEW_ID", "402014829835")
        self.deals_view_id = os.getenv("DEALS_VIEW_ID", "402014829847")
        
        if not self.domain or not self.api_key:
            raise ValueError("FRESHWORKS_DOMAIN and FRESHWORKS_API_KEY must be set in environment")
        
        self.base_url = f"https://{self.domain}.myfreshworks.com/crm/sales/api"
        self.headers = {
            "Authorization": f"Token token={self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Cache for stage names
        self._stage_cache = None
        # Cache for sales accounts
        self._sales_account_cache = {}
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        """Make HTTP request to Freshworks API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{endpoint}",
                headers=self.headers,
                params=params or {},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def _fetch_deal_stages(self) -> Dict[int, str]:
        """Fetch all deal stages from Freshworks API and cache them"""
        if self._stage_cache is not None:
            return self._stage_cache
        
        try:
            result = await self._make_request("selector/deal_stages")
            stages = result.get("deal_stages", [])
            
            # Build a mapping of stage_id -> stage_name
            self._stage_cache = {stage["id"]: stage["name"] for stage in stages if "id" in stage and "name" in stage}
            return self._stage_cache
        except Exception as e:
            # If fetching fails, return empty dict and log the error
            print(f"Warning: Failed to fetch deal stages: {e}")
            self._stage_cache = {}
            return self._stage_cache
    
    async def get_sales_account(self, account_id: int) -> Optional[Dict]:
        """Fetch a sales account by ID and cache it"""
        if account_id in self._sales_account_cache:
            return self._sales_account_cache[account_id]
        
        try:
            result = await self._make_request(f"sales_accounts/{account_id}")
            account = result.get("sales_account")
            if account:
                self._sales_account_cache[account_id] = account
            return account
        except Exception as e:
            print(f"Warning: Failed to fetch sales account {account_id}: {e}")
            return None
    
    async def get_all_contacts(
        self, 
        page: int = 1, 
        per_page: int = 25,
        view_id: Optional[int] = None,
        include: str = "owner"
    ) -> Dict:
        """
        Get all contacts from Freshworks CRM
        
        Args:
            page: Page number
            per_page: Results per page
            view_id: Optional view ID to filter contacts
            include: Additional fields to include (e.g., 'owner')
        """
        params = {
            "page": page,
            "per_page": per_page
        }
        
        # Use the configured view ID or the provided one
        if view_id:
            endpoint = f"contacts/view/{view_id}"
        else:
            endpoint = f"contacts/view/{self.contacts_view_id}"
        
        return await self._make_request(endpoint, params)
    
    async def get_all_deals(
        self,
        page: int = 1,
        per_page: int = 25,
        view_id: Optional[int] = None,
        include: str = "owner,sales_account"
    ) -> Dict:
        """
        Get all deals (opportunities) from Freshworks CRM
        
        Args:
            page: Page number
            per_page: Results per page
            view_id: Optional view ID to filter deals
            include: Additional fields to include (e.g., 'owner')
        """
        params = {
            "page": page,
            "per_page": per_page,
            "sort": "amount",
            "include": include
        }
        
        # Use the configured view ID or the provided one
        if view_id:
            endpoint = f"deals/view/{view_id}"
        else:
            endpoint = f"deals/view/{self.deals_view_id}"
        
        result = await self._make_request(endpoint, params)
        
        # Fetch stage mapping
        stage_map = await self._fetch_deal_stages()
        
        # Map users to dealers
        users = result.get("users", [])
        deals = result.get("deals", [])
        
        # Create owner lookup dict
        owner_map = {user["id"]: user for user in users}
        
        # Add owner object and stage name to each deal
        for deal in deals:
            owner_id = deal.get("owner_id")
            if owner_id and owner_id in owner_map:
                deal["owner"] = owner_map[owner_id]
            
            # Add stage mapping using actual stage names from API
            stage_id = deal.get("deal_stage_id")
            if stage_id:
                deal["deal_stage"] = {
                    "id": stage_id,
                    "name": stage_map.get(stage_id, f"Stage {stage_id}")
                }
        
        return result
    
    async def get_contact_by_id(self, contact_id: int, include: str = "owner") -> Dict:
        """Get a specific contact by ID"""
        return await self._make_request(f"contacts/{contact_id}", {"include": include})
    
    async def get_deal_by_id(self, deal_id: int, include: str = "owner,contact") -> Dict:
        """Get a specific deal by ID"""
        return await self._make_request(f"deals/{deal_id}", {"include": include})
    
    async def get_all_contacts_paginated(self, max_pages: int = 100) -> List[Dict]:
        """
        Get all contacts across multiple pages
        
        Args:
            max_pages: Maximum number of pages to fetch
        """
        all_contacts = []
        page = 1
        
        while page <= max_pages:
            result = await self.get_all_contacts(page=page, per_page=100)
            contacts = result.get("contacts", [])
            
            if not contacts:
                break
            
            all_contacts.extend(contacts)
            
            # Check if there are more pages
            meta = result.get("meta", {})
            total_pages = meta.get("total_pages", 1)
            
            if page >= total_pages:
                break
            
            page += 1
        
        return all_contacts
    
    async def get_all_deals_paginated(self, max_pages: int = 100) -> List[Dict]:
        """
        Get all deals across multiple pages
        
        Args:
            max_pages: Maximum number of pages to fetch
        """
        all_deals = []
        page = 1
        
        while page <= max_pages:
            result = await self.get_all_deals(page=page, per_page=100)
            deals = result.get("deals", [])
            
            if not deals:
                break
            
            all_deals.extend(deals)
            
            # Check if there are more pages
            meta = result.get("meta", {})
            total_pages = meta.get("total_pages", 1)
            
            if page >= total_pages:
                break
            
            page += 1
        
        return all_deals
