import { Request, Response } from 'express';
import { FreshworksService } from '../services/freshworksService';

export async function getAllPipelines(req: Request, res: Response) {
  try {
    const pipelines = await FreshworksService.getPipelines();
    console.debug('getPipelines response:', JSON.stringify(pipelines).slice(0, 300));
    console.debug('pipeline count:', pipelines.length);
    res.json({ success: true, data: pipelines });
  } catch (e) {
    console.error('Error in getAllPipelines:', e);
    res.status(500).json({ success: false, error: (e as Error).message });
  }
}
