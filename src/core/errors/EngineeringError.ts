import { ERROR_DEFINITIONS, ErrorSeverity, ErrorCategory } from './errorCodes';

export interface EngineeringErrorPayload {
  code: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  title: string;
  message: string;
  remedySuggestion: string;
  objectId?: string;
  objectType?: 'node' | 'member' | 'slab' | 'section' | 'material' | 'load_pattern' | 'load_combo' | 'project';
  targetId?: string;
  timestamp: string;
  context?: Record<string, any>;
}

export class EngineeringError extends Error {
  public readonly code: string;
  public readonly category: ErrorCategory;
  public readonly severity: ErrorSeverity;
  public readonly title: string;
  public readonly remedySuggestion: string;
  public readonly objectId?: string;
  public readonly objectType?: EngineeringErrorPayload['objectType'];
  public readonly targetId?: string;
  public readonly timestamp: string;
  public readonly context?: Record<string, any>;

  constructor(
    code: string,
    params?: {
      objectId?: string;
      objectType?: EngineeringErrorPayload['objectType'];
      targetId?: string;
      details?: string;
      context?: Record<string, any>;
      customMessage?: string;
    }
  ) {
    const def = ERROR_DEFINITIONS[code] || {
      code,
      category: ErrorCategory.API_SYSTEM,
      severity: ErrorSeverity.ERROR,
      title: 'Structural Engineering Exception',
      messageTemplate: 'An engineering exception occurred: {details}',
      remedySuggestion: 'Check structural model inputs and rerun validation.'
    };

    let formattedMessage = params?.customMessage || def.messageTemplate;
    if (params?.objectId) formattedMessage = formattedMessage.replace(/\{objectId\}/g, params.objectId);
    if (params?.targetId) formattedMessage = formattedMessage.replace(/\{targetId\}/g, params.targetId);
    if (params?.details) formattedMessage = formattedMessage.replace(/\{details\}/g, params.details);
    if (params?.context) {
      Object.entries(params.context).forEach(([k, v]) => {
        formattedMessage = formattedMessage.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
      });
    }

    super(formattedMessage);
    this.name = 'EngineeringError';
    this.code = code;
    this.category = def.category;
    this.severity = def.severity;
    this.title = def.title;
    this.remedySuggestion = def.remedySuggestion;
    this.objectId = params?.objectId;
    this.objectType = params?.objectType;
    this.targetId = params?.targetId;
    this.timestamp = new Date().toISOString();
    this.context = params?.context;

    // Maintain prototype chain
    Object.setPrototypeOf(this, EngineeringError.prototype);
  }

  public toJSON(): EngineeringErrorPayload {
    return {
      code: this.code,
      category: this.category,
      severity: this.severity,
      title: this.title,
      message: this.message,
      remedySuggestion: this.remedySuggestion,
      objectId: this.objectId,
      objectType: this.objectType,
      targetId: this.targetId,
      timestamp: this.timestamp,
      context: this.context
    };
  }
}
