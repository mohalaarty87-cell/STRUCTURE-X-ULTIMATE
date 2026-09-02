import { Router, Request, Response } from 'express';
import { projectRepository } from '../repository/ProjectRepository';
import { ModelIntegrityValidator } from '../../core/validation/ModelIntegrityValidator';
import { UNIT_SYSTEMS } from '../../core/units/unitSystem';
import { UnitConverter } from '../../core/units/unitConverter';
import { logger } from '../../core/logging/Logger';
import { config } from '../../config';
import { EngineeringError } from '../../core/errors/EngineeringError';
import { runAllVerificationSuites } from '../../test/testRunner';

export const apiRouter = Router();

// 1. Health & System Info
apiRouter.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    system: 'STRUCTURE-X ULTIMATE',
    version: config.version,
    phase: 'PHASE 01 — PROJECT FOUNDATION',
    environment: config.env,
    uptimeSeconds: process.uptime(),
    memoryUsageMB: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
    features: config.features,
    timestamp: new Date().toISOString()
  });
});

// 2. Project Management Endpoints
apiRouter.get('/projects', (req: Request, res: Response) => {
  try {
    const list = projectRepository.listProjects();
    res.json({ success: true, count: list.length, data: list });
  } catch (err: any) {
    logger.error('API', 'Failed to list projects', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

apiRouter.post('/projects', (req: Request, res: Response) => {
  try {
    const { metadata, initialModel } = req.body || {};
    const newProject = projectRepository.createProject(metadata || {}, initialModel);
    res.status(201).json({ success: true, data: newProject });
  } catch (err: any) {
    logger.error('API', 'Failed to create project', err);
    res.status(400).json({ success: false, error: err.message });
  }
});

apiRouter.get('/projects/:id', (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const project = projectRepository.getProject(id);
    res.json({ success: true, data: project });
  } catch (err: any) {
    if (err instanceof EngineeringError) {
      res.status(404).json({ success: false, error: err.toJSON() });
    } else {
      res.status(404).json({ success: false, error: err.message });
    }
  }
});

apiRouter.put('/projects/:id', (req: Request, res: Response) => {
  try {
    const model = req.body;
    if (!model || !model.metadata || model.metadata.id !== req.params.id) {
      return res.status(400).json({ success: false, error: 'Project ID in URL does not match body metadata' });
    }
    const saved = projectRepository.saveProject(model);
    res.json({ success: true, data: saved });
  } catch (err: any) {
    logger.error('API', 'Failed to save project', err);
    res.status(400).json({ success: false, error: err.message });
  }
});

apiRouter.delete('/projects/:id', (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    projectRepository.deleteProject(id);
    res.json({ success: true, message: `Project ${id} deleted` });
  } catch (err: any) {
    res.status(404).json({ success: false, error: err.message });
  }
});

// 3. Model Integrity Validation Endpoint
apiRouter.post('/projects/:id/validate', (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const model = req.body && req.body.metadata ? req.body : projectRepository.getProject(id);
    const report = ModelIntegrityValidator.validate(model);
    res.json({ success: true, report });
  } catch (err: any) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// 4. Units System Endpoints
apiRouter.get('/units/systems', (req: Request, res: Response) => {
  res.json({ success: true, data: UNIT_SYSTEMS });
});

apiRouter.post('/units/convert', (req: Request, res: Response) => {
  try {
    const { value, dimension, fromUnit, toUnit } = req.body;
    if (typeof value !== 'number' || !dimension || !fromUnit || !toUnit) {
      return res.status(400).json({ success: false, error: 'Missing required parameters (value, dimension, fromUnit, toUnit)' });
    }

    let converted = value;
    switch (dimension) {
      case 'LENGTH':
        converted = UnitConverter.convertLength(value, fromUnit, toUnit);
        break;
      case 'FORCE':
        converted = UnitConverter.convertForce(value, fromUnit, toUnit);
        break;
      case 'MOMENT':
        converted = UnitConverter.convertMoment(value, fromUnit, toUnit);
        break;
      case 'STRESS':
        converted = UnitConverter.convertStress(value, fromUnit, toUnit);
        break;
      case 'DISTRIBUTED_FORCE':
        converted = UnitConverter.convertDistributedForce(value, fromUnit, toUnit);
        break;
      case 'AREA_FORCE':
        converted = UnitConverter.convertAreaForce(value, fromUnit, toUnit);
        break;
      case 'TEMPERATURE':
        converted = UnitConverter.convertTemperature(value, fromUnit, toUnit);
        break;
      default:
        return res.status(400).json({ success: false, error: `Unsupported dimension: ${dimension}` });
    }

    res.json({ success: true, original: { value, unit: fromUnit }, converted: { value: converted, unit: toUnit } });
  } catch (err: any) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// 5. Diagnostics & Audit Logs
apiRouter.get('/logs', (req: Request, res: Response) => {
  const limit = parseInt(req.query.limit as string) || 100;
  const module = req.query.module as string | undefined;
  const logs = logger.getRecentLogs(limit, module);
  res.json({ success: true, count: logs.length, data: logs });
});

// 6. Automated Testing & Verification Endpoint
apiRouter.get('/tests/run', (req: Request, res: Response) => {
  try {
    const report = runAllVerificationSuites();
    res.json({ success: true, report });
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message });
  }
});

