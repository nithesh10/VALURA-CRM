
import { Request, Response } from 'express';
import { FreshworksService } from '../services/freshworksService';
import { AnalyticsService } from '../services/analyticsService';

export async function getAllOpportunities(req: Request, res: Response) {
  const page = parseInt(req.query.page as string) || 1;
  const per_page = parseInt(req.query.per_page as string) || 25;
  const pipelineId = req.query.pipeline_id as string | undefined;
  try {
    // Fetch deals, users, and stages in parallel
    // Fetch deals (which includes users in response)
    const data = await FreshworksService.getAllDeals(page, per_page);
    const deals = data.deals || [];
    const users = data.users || [];
    const stagesResp = await FreshworksService.makeRequest('selector/deal_stages');
    const stages = stagesResp.deal_stages || [];

    // debug: log full responses to diagnose empty data
    console.debug('users response:', JSON.stringify(users).slice(0, 200));
    console.debug('stages response:', JSON.stringify(stages).slice(0, 200));

    // Build lookup maps for quick enrichment
    const ownerMap: Record<string, any> = {};
    for (const user of users) {
      if (user.id) ownerMap[String(user.id)] = user;
    }
    const stageMap: Record<string, any> = {};
    for (const stage of stages) {
      if (stage.id) stageMap[String(stage.id)] = stage;
    }

    // debug log counts (can remove later)
    console.debug('owners fetched', Object.keys(ownerMap).length, 'stages fetched', Object.keys(stageMap).length);
    // Enrich deals
    let enrichedDeals = deals.map((deal: any) => {
      return {
        ...deal,
        owner_name: deal.owner_id && ownerMap[String(deal.owner_id)] ? ownerMap[String(deal.owner_id)].display_name : '',
        stage_name: deal.deal_stage_id && stageMap[String(deal.deal_stage_id)] ? stageMap[String(deal.deal_stage_id)].name : '',
      };
    });
    if (pipelineId) enrichedDeals = enrichedDeals.filter((d: any) => d.deal_pipeline_id == pipelineId);
    res.json({ success: true, data: enrichedDeals, meta: data.meta || {} });
  } catch (e) {
    res.status(500).json({ success: false, error: (e as Error).message });
  }
}

export async function getOpportunitiesByStage(req: Request, res: Response) {
  const pipelineId = req.query.pipeline_id as string | undefined;
  try {
    // fetch all deals and optionally filter by pipeline
    const allDeals = await FreshworksService.getAllDealsPaginated();
    const filteredDeals = pipelineId
      ? allDeals.filter((d: any) => d.deal_pipeline_id == pipelineId)
      : allDeals;

    // group by stage name (use deal_stage.name when available)
    const grouped: Record<string, { count: number; total_value: number; leads: any[] }> = {};
    for (const deal of filteredDeals) {
      let stageName = 'Unknown';
      if (deal.deal_stage && typeof deal.deal_stage === 'object' && deal.deal_stage.name) {
        stageName = deal.deal_stage.name;
      } else if (deal.stage_name) {
        stageName = deal.stage_name;
      }
      if (!grouped[stageName]) grouped[stageName] = { count: 0, total_value: 0, leads: [] };
      grouped[stageName].count++;
      grouped[stageName].total_value += parseFloat(deal.amount || '0') || 0;
      grouped[stageName].leads.push(deal);
    }

    const topStages = Object.entries(grouped)
      .map(([stage, obj]) => ({ stage, count: obj.count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    res.json({ success: true, data: grouped, top_stages: topStages });
  } catch (e) {
    res.status(500).json({ success: false, error: (e as Error).message });
  }
}

export async function getLeadsBySalesOwner(req: Request, res: Response) {
  const pipelineId = req.query.pipeline_id as string | undefined;
  try {
    // Fetch all deals (opportunities)
    const deals = await AnalyticsService.getDashboardSummary(pipelineId);
    // Group by owner with count, total_value, and leads
    const grouped: Record<string, { count: number, total_value: number, leads: any[] }> = {};
    const allDeals = await FreshworksService.getAllDealsPaginated();
    const filteredDeals = pipelineId ? allDeals.filter((d: any) => d.deal_pipeline_id == pipelineId) : allDeals;
    for (const deal of filteredDeals) {
      let ownerName = 'Unassigned';
      // Use enriched owner_name field from getAllDealsPaginated enrichment
      if (deal.owner_name && deal.owner_name.trim()) {
        ownerName = deal.owner_name;
      } else if (deal.owner && typeof deal.owner === 'object') {
        ownerName = deal.owner.display_name || deal.owner.email || `Owner ${deal.owner.id}`;
      }
      if (!grouped[ownerName]) grouped[ownerName] = { count: 0, total_value: 0, leads: [] };
      grouped[ownerName].count++;
      grouped[ownerName].total_value += parseFloat(deal.amount || '0') || 0;
      grouped[ownerName].leads.push(deal);
    }
    // Prepare top owners
    const topOwners = Object.entries(grouped)
      .map(([owner, obj]) => ({ owner, count: obj.count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
    res.json({ success: true, data: grouped, top_owners: topOwners });
  } catch (e) {
    res.status(500).json({ success: false, error: (e as Error).message });
  }
}
