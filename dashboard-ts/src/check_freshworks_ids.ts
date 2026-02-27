import axios from 'axios';
import dotenv from 'dotenv';
dotenv.config();

const DOMAIN = process.env.FRESHWORKS_DOMAIN;
const API_KEY = process.env.FRESHWORKS_API_KEY;
const BASE_URL = `https://${DOMAIN}.myfreshworks.com/crm/sales/api`;
const headers = {
  'Authorization': `Token token=${API_KEY}`,
  'Content-Type': 'application/json',
};

async function fetchData() {
  // Fetch deals
  const dealsResp = await axios.get(`${BASE_URL}/deals/view/${process.env.DEALS_VIEW_ID}`, { headers, params: { page: 1, per_page: 10 } });
  const deals: any[] = dealsResp.data.deals || [];

  // Fetch owners
  const ownersResp = await axios.get(`${BASE_URL}/users`, { headers });
  const owners = ownersResp.data.users || [];

  // Fetch stages
  const stagesResp = await axios.get(`${BASE_URL}/selector/deal_stages`, { headers });
  const stages = stagesResp.data.deal_stages || [];

  // Print IDs for comparison
  console.log('Deal owner_ids:', deals.map((d: any) => d.owner_id));
  console.log('Deal deal_stage_ids:', deals.map((d: any) => d.deal_stage_id));
  console.log('Owner IDs:', owners.map((o: any) => o.id));
  console.log('Stage IDs:', stages.map((s: any) => s.id));
}

fetchData();
