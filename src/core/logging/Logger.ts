export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  AUDIT = 4
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'AUDIT';
  module: string;
  message: string;
  data?: any;
}

export class Logger {
  private static instance: Logger;
  private minLevel: LogLevel = LogLevel.DEBUG;
  private ringBuffer: LogEntry[] = [];
  private maxBufferSize: number = 1000;
  private listeners: ((entry: LogEntry) => void)[] = [];

  private constructor() {}

  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  public setMinLevel(level: LogLevel): void {
    this.minLevel = level;
  }

  public subscribe(listener: (entry: LogEntry) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  public getRecentLogs(limit: number = 100, module?: string): LogEntry[] {
    let logs = this.ringBuffer;
    if (module) {
      logs = logs.filter(l => l.module.toLowerCase() === module.toLowerCase());
    }
    return logs.slice(-limit);
  }

  public clear(): void {
    this.ringBuffer = [];
  }

  private log(level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'AUDIT', levelValue: LogLevel, module: string, message: string, data?: any): void {
    if (levelValue < this.minLevel) return;

    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      timestamp: new Date().toISOString(),
      level,
      module,
      message,
      data
    };

    this.ringBuffer.push(entry);
    if (this.ringBuffer.length > this.maxBufferSize) {
      this.ringBuffer.shift();
    }

    // Console output in dev/server
    const formatted = `[${entry.timestamp}] [${level}] [${module}] ${message}`;
    if (level === 'ERROR') {
      console.error(formatted, data || '');
    } else if (level === 'WARN') {
      console.warn(formatted, data || '');
    } else {
      console.log(formatted, data || '');
    }

    // Notify listeners
    this.listeners.forEach(fn => {
      try {
        fn(entry);
      } catch (err) {
        // Ignore subscriber failure
      }
    });
  }

  public debug(module: string, message: string, data?: any): void {
    this.log('DEBUG', LogLevel.DEBUG, module, message, data);
  }

  public info(module: string, message: string, data?: any): void {
    this.log('INFO', LogLevel.INFO, module, message, data);
  }

  public warn(module: string, message: string, data?: any): void {
    this.log('WARN', LogLevel.WARN, module, message, data);
  }

  public error(module: string, message: string, data?: any): void {
    this.log('ERROR', LogLevel.ERROR, module, message, data);
  }

  public audit(module: string, message: string, data?: any): void {
    this.log('AUDIT', LogLevel.AUDIT, module, message, data);
  }
}

export const logger = Logger.getInstance();
