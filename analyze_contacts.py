import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def fetch_all_contacts():
    """Fetch all contacts from the view"""
    domain = os.getenv("FRESHWORKS_DOMAIN")
    api_key = os.getenv("FRESHWORKS_API_KEY")
    view_id = os.getenv("CONTACTS_VIEW_ID")
    
    base_url = f"https://{domain}.myfreshworks.com/crm/sales/api"
    headers = {
        "Authorization": f"Token token={api_key}",
        "Content-Type": "application/json"
    }
    
    all_contacts = []
    page = 1
    
    async with httpx.AsyncClient() as client:
        while page <= 2:
            response = await client.get(
                f"{base_url}/contacts/view/{view_id}",
                headers=headers,
                params={"page": page, "per_page": 100}
            )
            data = response.json()
            contacts = data.get("contacts", [])
            
            if not contacts:
                break
            
            all_contacts.extend(contacts)
            page += 1
    
    return all_contacts

async def fetch_all_deals():
    """Fetch all deals from the view"""
    domain = os.getenv("FRESHWORKS_DOMAIN")
    api_key = os.getenv("FRESHWORKS_API_KEY")
    view_id = os.getenv("DEALS_VIEW_ID")
    
    base_url = f"https://{domain}.myfreshworks.com/crm/sales/api"
    headers = {
        "Authorization": f"Token token={api_key}",
        "Content-Type": "application/json"
    }
    
    all_deals = []
    page = 1
    
    async with httpx.AsyncClient() as client:
        while page <= 2:
            response = await client.get(
                f"{base_url}/deals/view/{view_id}",
                headers=headers,
                params={"page": page, "per_page": 100}
            )
            data = response.json()
            deals = data.get("deals", [])
            
            if not deals:
                break
            
            all_deals.extend(deals)
            page += 1
    
    return all_deals

async def main():
    contacts = await fetch_all_contacts()
    deals = await fetch_all_deals()
    
    print(f"\n=== DATA SUMMARY ===")
    print(f"Total contacts: {len(contacts)}")
    print(f"Total deals: {len(deals)}")
    
    # Build deal names set (normalized)
    deal_names = set()
    for deal in deals:
        if deal.get("name"):
            deal_names.add(deal["name"].strip().lower())
    
    print(f"Unique deal names: {len(deal_names)}")
    
    # Match contacts to deals
    contacts_with_deals = []
    contacts_without_deals = []
    
    for contact in contacts:
        first_name = (contact.get("first_name") or "").strip()
        last_name = (contact.get("last_name") or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        full_name_lower = full_name.lower()
        
        # Check if contact name exactly matches a deal name
        if full_name_lower in deal_names:
            contacts_with_deals.append((full_name, contact.get("id"), "exact"))
        else:
            # Check for partial matches (fuzzy)
            found = False
            for deal_name in deal_names:
                if len(full_name_lower) >= 5 and len(deal_name) >= 5:
                    if full_name_lower in deal_name or deal_name in full_name_lower:
                        contacts_with_deals.append((full_name, contact.get("id"), "fuzzy"))
                        found = True
                        break
            
            if not found:
                contacts_without_deals.append((full_name, contact.get("id")))
    
    print(f"\n=== MATCHING RESULTS ===")
    print(f"Contacts WITH deals (exact match): {len([c for c in contacts_with_deals if c[2] == 'exact'])}")
    print(f"Contacts WITH deals (fuzzy match): {len([c for c in contacts_with_deals if c[2] == 'fuzzy'])}")
    print(f"Contacts WITH deals (total): {len(contacts_with_deals)}")
    print(f"Contacts WITHOUT deals: {len(contacts_without_deals)}")
    
    print(f"\n=== Expected vs Actual ===")
    print(f"Expected contacts without deals: {len(contacts) - len(deals)}")
    print(f"Actual contacts without deals: {len(contacts_without_deals)}")
    print(f"Difference: {abs((len(contacts) - len(deals)) - len(contacts_without_deals))}")
    
    print(f"\n=== Contacts WITHOUT deals (first 20) ===")
    for i, (name, contact_id) in enumerate(contacts_without_deals[:20], 1):
        print(f"{i}. {name} (ID: {contact_id})")
    
    # Check if there are deals with multiple contacts
    print(f"\n=== Deal Name Analysis ===")
    # Count how many contacts match each deal name
    deal_contact_count = {}
    for deal_name in deal_names:
        count = 0
        for contact in contacts:
            first_name = (contact.get("first_name") or "").strip()
            last_name = (contact.get("last_name") or "").strip()
            full_name = f"{first_name} {last_name}".strip().lower()
            
            if full_name == deal_name or (len(full_name) >= 5 and len(deal_name) >= 5 and (full_name in deal_name or deal_name in full_name)):
                count += 1
        
        if count > 1:
            deal_contact_count[deal_name] = count
    
    if deal_contact_count:
        print(f"Deals with multiple contact matches: {len(deal_contact_count)}")
        for deal_name, count in list(deal_contact_count.items())[:10]:
            print(f"  '{deal_name}' -> {count} contacts")
    else:
        print("No deals with multiple contact matches")

if __name__ == "__main__":
    asyncio.run(main())
