from typing import Dict, List, Optional, Any
from collections import defaultdict

class AnalyticsService:
    """Service for CRM analytics and data processing"""
    
    def __init__(self, freshworks_service):
        self.freshworks = freshworks_service
    
    async def get_contacts_without_opportunities(self, pipeline_id: Optional[int] = None) -> List[Dict]:
        """
        Get all contacts that are not associated with any opportunities/deals
        
        Args:
            pipeline_id: Optional filter for specific pipeline
        """
        # Get all contacts and deals
        contacts = await self.freshworks.get_all_contacts_paginated()
        deals = await self.freshworks.get_all_deals_paginated()
        
        # Filter deals by pipeline if specified
        if pipeline_id:
            deals = [d for d in deals if d.get("deal_pipeline_id") == int(pipeline_id)]
        
        # Extract contact IDs from deals
        contact_ids_in_deals = set()
        
        # Build a set of deal names for faster lookup (normalized)
        deal_names_set = set()
        
        for deal in deals:
            # Check for contact_id or sales_account_id
            if deal.get("contact_id"):
                contact_ids_in_deals.add(deal["contact_id"])
            if deal.get("sales_account_id"):
                contact_ids_in_deals.add(deal["sales_account_id"])
            
            # Check in contacts array if present
            if deal.get("contacts"):
                for contact in deal["contacts"]:
                    if contact.get("id"):
                        contact_ids_in_deals.add(contact["id"])
            
            # Add deal name to set for matching (normalized)
            if deal.get("name"):
                # Normalize: lowercase, trim, remove extra spaces
                normalized_name = " ".join(deal["name"].strip().lower().split())
                deal_names_set.add(normalized_name)
        
        # Filter contacts not in deals
        contacts_without_deals = []
        for contact in contacts:
            contact_id = contact.get("id")
            
            # Check if linked by ID first (fastest check)
            if contact_id in contact_ids_in_deals:
                continue
            
            # Build contact full name for name-based matching
            first_name = (contact.get("first_name") or "").strip()
            last_name = (contact.get("last_name") or "").strip()
            full_name = f"{first_name} {last_name}".strip()
            
            # Skip contacts without a meaningful name
            if not full_name or len(full_name) < 2:
                contacts_without_deals.append(contact)
                continue
            
            # Normalize contact name
            full_name_normalized = " ".join(full_name.lower().split())
            
            # Check if the exact contact name matches any deal name
            if full_name_normalized in deal_names_set:
                continue
            
            # Check for partial matches (one contains the other)
            found_match = False
            for deal_name in deal_names_set:
                # Check if contact name is contained in deal name or vice versa
                # This handles cases like "John Doe" matching "John Doe Investment"
                if full_name_normalized in deal_name or deal_name in full_name_normalized:
                    found_match = True
                    break
                
                # Also check individual name components for better matching
                # e.g., "Mukesh" should match "Mukesh Kumar" or just "Mukesh"
                contact_parts = full_name_normalized.split()
                deal_parts = deal_name.split()
                
                # If all contact name parts are in the deal name, consider it a match
                if all(part in deal_parts for part in contact_parts if len(part) >= 3):
                    found_match = True
                    break
            
            if not found_match:
                contacts_without_deals.append(contact)
        
        return contacts_without_deals
    
    async def get_contacts_by_source(self, source_filter: Optional[str] = None, pipeline_id: Optional[int] = None) -> Dict[str, List[Dict]]:
        """
        Group contacts by source type using sales accounts from deals, tags, and deal stages
        
        Args:
            source_filter: Optional filter for specific source type
            pipeline_id: Optional filter for specific pipeline
        """
        contacts = await self.freshworks.get_all_contacts_paginated()
        deals = await self.freshworks.get_all_deals_paginated()
        
        # Filter deals by pipeline if specified
        if pipeline_id:
            deals = [d for d in deals if d.get("deal_pipeline_id") == int(pipeline_id)]
        
        # Build a map of normalized deal names to their sales account names
        deal_name_to_source = {}
        
        for deal in deals:
            deal_name = deal.get("name", "").strip().lower()
            normalized_deal_name = " ".join(deal_name.split())
            
            # Priority 1: Get sales account name (most reliable)
            sales_account_id = deal.get("sales_account_id")
            if sales_account_id:
                sales_account = await self.freshworks.get_sales_account(sales_account_id)
                if sales_account and sales_account.get("name"):
                    account_name = sales_account["name"].strip()
                    deal_name_to_source[normalized_deal_name] = account_name
                    continue
            
            # Priority 2: Use stage name if it indicates a source
            stage_name = deal.get("deal_stage", {}).get("name") if isinstance(deal.get("deal_stage"), dict) else None
            if stage_name and any(keyword in stage_name.lower() for keyword in ["walk", "online", "referral", "reference", "lead"]):
                deal_name_to_source[normalized_deal_name] = stage_name
        
        # Group contacts by source
        grouped = defaultdict(list)
        
        for contact in contacts:
            # Build contact full name
            first_name = (contact.get("first_name") or "").strip()
            last_name = (contact.get("last_name") or "").strip()
            full_name = f"{first_name} {last_name}".strip()
            full_name_normalized = " ".join(full_name.lower().split())
            
            # Priority 1: Check if contact has tags (e.g., "Priyesh Reference")
            tags = contact.get("tags", [])
            if tags and len(tags) > 0:
                for tag in tags:
                    source_key = str(tag).strip()
                    grouped[source_key].append(contact)
                continue
            
            # Priority 2: Try to match contact with deal by name
            matched_source = None
            
            # Exact match
            if full_name_normalized in deal_name_to_source:
                matched_source = deal_name_to_source[full_name_normalized]
            else:
                # Partial match - check if contact name is in deal name or vice versa
                for deal_name, source_name in deal_name_to_source.items():
                    if full_name_normalized in deal_name or deal_name in full_name_normalized:
                        matched_source = source_name
                        break
                    
                    # Also check individual name parts for better matching
                    contact_parts = full_name_normalized.split()
                    deal_parts = deal_name.split()
                    
                    if all(part in deal_parts for part in contact_parts if len(part) >= 3):
                        matched_source = source_name
                        break
            
            # Categorize based on matched source
            if matched_source:
                grouped[matched_source].append(contact)
            else:
                # No match found
                grouped["No Source"].append(contact)
        
        # Convert to regular dict
        result = dict(grouped)
        
        # Apply filter if specified
        if source_filter:
            if source_filter in result:
                return {source_filter: result[source_filter]}
            return {source_filter: []}
        
        return result
    
    async def get_opportunities_by_stage(self, stage_filter: Optional[str] = None, pipeline_id: Optional[int] = None) -> Dict[str, List[Dict]]:
        """
        Group opportunities by stage
        
        Args:
            stage_filter: Optional filter for specific stage
            pipeline_id: Optional filter for specific pipeline
        """
        deals = await self.freshworks.get_all_deals_paginated()
        
        # Filter deals by pipeline if specified
        if pipeline_id:
            deals = [d for d in deals if d.get("deal_pipeline_id") == int(pipeline_id)]
        
        # Group by stage
        grouped = defaultdict(list)
        
        for deal in deals:
            stage = deal.get("deal_stage_id") or deal.get("stage") or "Unknown"
            stage_name = deal.get("deal_stage", {}).get("name") if isinstance(deal.get("deal_stage"), dict) else str(stage)
            
            grouped[stage_name].append(deal)
        
        # Convert to regular dict
        result = dict(grouped)
        
        # Apply filter if specified
        if stage_filter:
            if stage_filter in result:
                return {stage_filter: result[stage_filter]}
            return {stage_filter: []}
        
        return result
    
    async def get_leads_by_sales_owner(self, owner_id: Optional[int] = None, pipeline_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get leads/opportunities grouped by sales owner with all details
        
        Args:
            owner_id: Optional filter for specific sales owner
            pipeline_id: Optional filter for specific pipeline
        """
        deals = await self.freshworks.get_all_deals_paginated()
        
        # Filter deals by pipeline if specified
        if pipeline_id:
            deals = [d for d in deals if d.get("deal_pipeline_id") == int(pipeline_id)]
        
        # Group by owner
        grouped = defaultdict(lambda: {
            "owner_info": {},
            "leads": [],
            "total_value": 0,
            "count": 0
        })
        
        for deal in deals:
            owner = deal.get("owner") or deal.get("owner_id")
            
            if isinstance(owner, dict):
                owner_name = owner.get("display_name") or owner.get("email") or f"Owner {owner.get('id')}"
                owner_key = str(owner.get("id", "unknown"))
            else:
                owner_name = f"Owner {owner}" if owner else "Unassigned"
                owner_key = str(owner) if owner else "unassigned"
            
            # Skip if filtering by specific owner
            if owner_id is not None and owner_key != str(owner_id):
                continue
            
            grouped[owner_name]["owner_info"] = {
                "id": owner_key,
                "name": owner_name
            }
            grouped[owner_name]["leads"].append(deal)
            grouped[owner_name]["count"] += 1
            
            # Add to total value if available
            amount = deal.get("amount") or deal.get("deal_value") or 0
            grouped[owner_name]["total_value"] += float(amount) if amount else 0
        
        return dict(grouped)
    
    async def get_opportunities_by_advisor(self, advisor_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get opportunities grouped by advisor (sales owner) with stage breakdown
        
        Args:
            advisor_id: Optional filter for specific advisor
        """
        deals = await self.freshworks.get_all_deals_paginated()
        
        # Group by advisor with stage breakdown
        grouped = defaultdict(lambda: {
            "advisor_info": {},
            "opportunities": [],
            "stages": defaultdict(lambda: {"count": 0, "deals": [], "total_value": 0}),
            "total_count": 0,
            "total_value": 0
        })
        
        for deal in deals:
            owner = deal.get("owner") or deal.get("owner_id")
            
            if isinstance(owner, dict):
                advisor_name = owner.get("display_name") or owner.get("email") or f"Advisor {owner.get('id')}"
                advisor_key = str(owner.get("id", "unknown"))
            else:
                advisor_name = f"Advisor {owner}" if owner else "Unassigned"
                advisor_key = str(owner) if owner else "unassigned"
            
            # Skip if filtering by specific advisor
            if advisor_id is not None and advisor_key != str(advisor_id):
                continue
            
            # Get stage information
            stage = deal.get("deal_stage_id") or deal.get("stage") or "Unknown"
            stage_name = deal.get("deal_stage", {}).get("name") if isinstance(deal.get("deal_stage"), dict) else str(stage)
            
            # Get deal value
            amount = deal.get("amount") or deal.get("deal_value") or 0
            deal_value = float(amount) if amount else 0
            
            # Update advisor info
            grouped[advisor_name]["advisor_info"] = {
                "id": advisor_key,
                "name": advisor_name
            }
            grouped[advisor_name]["opportunities"].append(deal)
            grouped[advisor_name]["total_count"] += 1
            grouped[advisor_name]["total_value"] += deal_value
            
            # Update stage info
            grouped[advisor_name]["stages"][stage_name]["count"] += 1
            grouped[advisor_name]["stages"][stage_name]["deals"].append(deal)
            grouped[advisor_name]["stages"][stage_name]["total_value"] += deal_value
        
        # Convert defaultdicts to regular dicts
        result = {}
        for advisor, data in grouped.items():
            result[advisor] = {
                "advisor_info": data["advisor_info"],
                "opportunities": data["opportunities"],
                "stages": dict(data["stages"]),
                "total_count": data["total_count"],
                "total_value": data["total_value"]
            }
        
        return result
    
    async def get_all_sales_owners(self) -> List[Dict]:
        """Get list of all unique sales owners from deals"""
        deals = await self.freshworks.get_all_deals_paginated()
        
        owners = {}
        for deal in deals:
            owner = deal.get("owner")
            if isinstance(owner, dict):
                owner_id = owner.get("id")
                if owner_id and owner_id not in owners:
                    owners[owner_id] = {
                        "id": owner_id,
                        "name": owner.get("display_name") or owner.get("email"),
                        "email": owner.get("email")
                    }
        
        return list(owners.values())
    
    async def get_all_stages(self) -> List[str]:
        """Get list of all unique deal stages"""
        deals = await self.freshworks.get_all_deals_paginated()
        
        stages = set()
        for deal in deals:
            stage_name = deal.get("deal_stage", {}).get("name") if isinstance(deal.get("deal_stage"), dict) else str(deal.get("deal_stage_id", "Unknown"))
            stages.add(stage_name)
        
        return sorted(list(stages))
    
    async def get_dashboard_summary(self, pipeline_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get aggregated summary data for the dashboard
        Returns total contacts, opportunities, sources breakdown, top stages, and top owners
        
        Args:
            pipeline_id: Optional filter for specific pipeline
        """
        # Get all data in parallel for efficiency
        contacts = await self.freshworks.get_all_contacts_paginated()
        deals = await self.freshworks.get_all_deals_paginated()
        
        # Filter deals by pipeline if specified
        if pipeline_id:
            deals = [d for d in deals if d.get("deal_pipeline_id") == int(pipeline_id)]
        
        contacts_without_opps = await self.get_contacts_without_opportunities(pipeline_id=pipeline_id)
        sources_grouped = await self.get_contacts_by_source(pipeline_id=pipeline_id)
        
        # Calculate total opportunity value
        total_value = sum(float(deal.get("amount") or deal.get("deal_value") or 0) for deal in deals)
        
        # Get stage distribution with counts and values
        stage_stats = defaultdict(lambda: {"count": 0, "total_value": 0})
        for deal in deals:
            stage_name = deal.get("deal_stage", {}).get("name") if isinstance(deal.get("deal_stage"), dict) else "Unknown"
            stage_stats[stage_name]["count"] += 1
            stage_stats[stage_name]["total_value"] += float(deal.get("amount") or deal.get("deal_value") or 0)
        
        # Sort stages by count and get top 10
        top_stages = sorted(
            [{"stage": stage, "count": stats["count"], "total_value": stats["total_value"]} 
             for stage, stats in stage_stats.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        
        # Get owner distribution with counts and values
        owner_stats = defaultdict(lambda: {"count": 0, "total_value": 0})
        for deal in deals:
            owner = deal.get("owner")
            if isinstance(owner, dict):
                owner_name = owner.get("display_name") or owner.get("email") or f"Owner {owner.get('id')}"
            else:
                owner_name = f"Owner {owner}" if owner else "Unassigned"
            
            owner_stats[owner_name]["count"] += 1
            owner_stats[owner_name]["total_value"] += float(deal.get("amount") or deal.get("deal_value") or 0)
        
        # Sort owners by count and get top 10
        top_owners = sorted(
            [{"owner": owner, "count": stats["count"], "total_value": stats["total_value"]} 
             for owner, stats in owner_stats.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        
        # Get sources breakdown (count per source)
        sources_breakdown = {source: len(contacts_list) for source, contacts_list in sources_grouped.items()}
        
        return {
            "total_contacts": len(contacts),
            "total_opportunities": len(deals),
            "contacts_without_opportunities": len(contacts_without_opps),
            "total_opportunity_value": total_value,
            "sources_breakdown": sources_breakdown,
            "top_stages": top_stages,
            "top_owners": top_owners
        }
