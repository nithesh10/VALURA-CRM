import { FreshworksService } from './src/services/freshworksService';

(async () => {
  try {
    const data = await FreshworksService.getAllDeals(1, 5);
    console.log('result keys:', Object.keys(data));
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error('error fetching deals:', e);
  }
})();
