import axios from 'axios';
import dotenv from 'dotenv';
dotenv.config();

const DOMAIN = process.env.FRESHWORKS_DOMAIN;
const API_KEY = process.env.FRESHWORKS_API_KEY;
const CONTACTS_VIEW_ID = process.env.CONTACTS_VIEW_ID || '402014829835';
const DEALS_VIEW_ID = process.env.DEALS_VIEW_ID || '402014829847';

const BASE_URL = `https://${DOMAIN}.myfreshworks.com/crm/sales/api`;

const headers = {
  'Authorization': `Token token=${API_KEY}`,
  'Content-Type': 'application/json',
};

export class FreshworksService {

    // Build lookup maps for owners and stages
    static async getOwnerAndStageMaps() {
      // Fetch all owners
      let owners: any[] = [];
      try {
        owners = await this.getAllOwners();
      } catch (e) {
        console.warn('Could not fetch owners:', e);
      }
      const ownerMap: Record<string, any> = {};
      for (const owner of owners) {
        if (owner.id) {
          ownerMap[String(owner.id)] = owner;
        }
      }

      // Fetch all stages
      let stages: any[] = [];
      try {
        stages = await this.getDealStages();
      } catch (e) {
        console.warn('Could not fetch stages:', e);
      }
      const stageMap: Record<string, any> = {};
      for (const stage of stages) {
        if (stage.id) {
          stageMap[String(stage.id)] = stage;
        }
      }
      return { ownerMap, stageMap };
    }
  static async makeRequest(endpoint: string, params: any = {}) {
    const url = `${BASE_URL}/${endpoint}`;
    try {
      const response = await axios.get(url, { headers, params });
      // debug: log first 500 chars of response for each endpoint
      console.debug(`[API] ${endpoint}:`, JSON.stringify(response.data).slice(0, 500));
      return response.data;
    } catch (error) {
      let errorMsg: any = error;
      let errorInfo: any = {};
      if (errorMsg && typeof errorMsg === 'object') {
        errorInfo = {
          url,
          params,
          error: (errorMsg as any).response ? (errorMsg as any).response.data : (errorMsg as any).message
        };
      } else {
        errorInfo = { url, params, error: String(errorMsg) };
      }
      console.error('Freshworks API error:', errorInfo);
      throw error;
    }
  }

  // Fetch all users (owners) from Freshworks
  static async getAllOwners() {
    // Freshworks API endpoint for users/owners - use selector/users (not just /users which fails with 400)
    const result = await this.makeRequest('selector/users');
    // result.users is expected
    console.debug('getAllOwners result keys:', Object.keys(result));
    return result.users || result || [];
  }

  // Build lookup maps for owners and stages


  static async getAllContacts(page = 1, per_page = 25, view_id?: string) {
    const endpoint = `contacts/view/${view_id || CONTACTS_VIEW_ID}`;
    return this.makeRequest(endpoint, { page, per_page });
  }

  static async getAllDeals(page = 1, per_page = 25, view_id?: string, include = 'owner,sales_account') {
    const endpoint = `deals/view/${view_id || DEALS_VIEW_ID}`;
    return this.makeRequest(endpoint, { page, per_page, include });
  }

  static async getAllDealsPaginated(maxPages = 100) {
    let allDeals: any[] = [];
    let page = 1;
    // Build empty owner map; will fill as we fetch pages (use embedded users)
    const ownerMap: Record<string, any> = {};
    // Fetch stages map once since it doesn't change per page
    const { stageMap } = await this.getOwnerAndStageMaps();
    while (page <= maxPages) {
      const result = await this.getAllDeals(page, 100);
      // accumulate any users from the page into ownerMap
      if (result.users && Array.isArray(result.users)) {
        for (const u of result.users) {
          if (u && u.id) {
            ownerMap[String(u.id)] = u;
          }
        }
      }
      let deals = result.deals || [];
      // Enrich each deal with owner and stage info
      deals = deals.map((deal: any) => {
        // Attach owner object if possible (using owner_id & ownerMap)
        if (deal.owner_id && ownerMap[String(deal.owner_id)]) {
          deal.owner = ownerMap[String(deal.owner_id)];
        }
        // Attach deal_stage object if possible
        if (deal.deal_stage_id && stageMap[String(deal.deal_stage_id)]) {
          deal.deal_stage = stageMap[String(deal.deal_stage_id)];
        }
        return deal;
      });
      if (!deals.length) break;
      allDeals = allDeals.concat(deals);
      const meta = result.meta || {};
      if (page >= (meta.total_pages || 1)) break;
      page++;
    }
    return allDeals;
  }

  static async getDealStages() {
    const result = await this.makeRequest('selector/deal_stages');
    return result.deal_stages || [];
  }

  static async getSalesAccount(accountId: string) {
    const result = await this.makeRequest(`sales_accounts/${accountId}`);
    return result.sales_account;
  }

  static async getPipelines() {
    try {
      // Try selector/deal_pipelines
      const result = await this.makeRequest('selector/deal_pipelines');
      console.debug('raw selector/deal_pipelines result keys:', Object.keys(result));
      console.debug('raw result:', JSON.stringify(result).slice(0, 500));
      let pipelines = result.deal_pipelines || result.pipelines || [];
      
      if (!pipelines.length) {
        console.warn('No pipelines from selector/deal_pipelines, trying deal_pipelines');
        // Try alternate endpoint
        const altResult = await this.makeRequest('deal_pipelines');
        console.debug('deal_pipelines response:', JSON.stringify(altResult).slice(0, 500));
        pipelines = altResult.deal_pipelines || altResult.pipelines || [];
      }
      
      console.debug('extracted pipelines count:', pipelines.length);
      if (pipelines.length > 0) {
        console.debug('pipelines data:', JSON.stringify(pipelines).slice(0, 500));
      }
      return pipelines;
    } catch (e: any) {
      console.error('Error fetching pipelines:', e.message || e);
      return [];
    }
  }
}
