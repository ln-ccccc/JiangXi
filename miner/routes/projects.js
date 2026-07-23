import { Router } from 'express';

import { projectApi as defaultProjectApi } from '../services/projectBackend.js';
import { buildProjectExportFeatures } from '../services/projectExportFeatures.js';

function relayJson(res, upstream) {
  res.status(upstream.status || 200).json(upstream.body);
}

function requestCookie(req) {
  return req.headers.cookie || '';
}

export function createProjectRoutes({
  projectApi = defaultProjectApi,
  getMinesData = () => [],
} = {}) {
  const router = Router();

  router.get('/', async (req, res) => {
    try {
      const upstream = await projectApi.listProjects({
        name: req.query.name ?? null,
        region: req.query.region ?? null,
        status: req.query.status ?? null,
        monitor_year: req.query.monitor_year ?? null,
      }, requestCookie(req));
      relayJson(res, upstream);
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.post('/', async (req, res) => {
    try {
      relayJson(res, await projectApi.createProject(req.body || {}, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.get('/:projectId', async (req, res) => {
    try {
      relayJson(res, await projectApi.getProjectDetail(req.params.projectId, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.patch('/:projectId', async (req, res) => {
    try {
      relayJson(res, await projectApi.updateProject(req.params.projectId, req.body || {}, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.put('/:projectId/mines', async (req, res) => {
    try {
      relayJson(res, await projectApi.replaceProjectMines(req.params.projectId, req.body || {}, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.post('/:projectId/datasets', async (req, res) => {
    try {
      relayJson(res, await projectApi.createProjectDataset(req.params.projectId, req.body || {}, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.get('/:projectId/timeline', async (req, res) => {
    try {
      relayJson(res, await projectApi.getProjectTimeline(req.params.projectId, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.post('/:projectId/archive', async (req, res) => {
    try {
      relayJson(res, await projectApi.archiveProject(req.params.projectId, req.body || {}, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.post('/:projectId/restore', async (req, res) => {
    try {
      relayJson(res, await projectApi.restoreProject(req.params.projectId, req.body || {}, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.post('/:projectId/exports', async (req, res) => {
    try {
      const projectId = Number(req.params.projectId);
      const payload = { ...(req.body || {}) };
      const format = String(payload.format || '').toLowerCase();
      if (!Array.isArray(payload.features) && (format === 'geojson' || format === 'shp')) {
        const detailUpstream = await projectApi.getProjectDetail(projectId, requestCookie(req));
        const detailBody = detailUpstream?.body || {};
        if (!detailBody?.data) {
          return relayJson(res, detailUpstream);
        }
        payload.features = buildProjectExportFeatures({
          projectDetail: detailBody.data,
          minesData: getMinesData(),
        });
      }
      relayJson(res, await projectApi.createProjectExport(projectId, payload, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.get('/:projectId/exports', async (req, res) => {
    try {
      relayJson(res, await projectApi.listProjectExports(req.params.projectId, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.post('/:projectId/backups', async (req, res) => {
    try {
      relayJson(res, await projectApi.createProjectBackup(req.params.projectId, req.body || {}, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.get('/:projectId/backups', async (req, res) => {
    try {
      relayJson(res, await projectApi.listProjectBackups(req.params.projectId, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  router.post('/:projectId/backups/:backupId/restore', async (req, res) => {
    try {
      relayJson(res, await projectApi.restoreProjectBackup(req.params.projectId, req.params.backupId, req.body || {}, requestCookie(req)));
    } catch (error) {
      res.status(502).json({ success: false, code: 1, msg: error?.message || String(error) });
    }
  });

  return router;
}
