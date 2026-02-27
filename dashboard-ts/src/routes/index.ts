import { Router } from 'express';
import contactsRouter from './contacts';
import opportunitiesRouter from './opportunities';
import pipelinesRouter from './pipelines';
import summaryRouter from './summary';

const router = Router();

router.use('/contacts', contactsRouter);
router.use('/opportunities', opportunitiesRouter);
router.use('/pipelines', pipelinesRouter);
router.use('/summary', summaryRouter);

export default router;
