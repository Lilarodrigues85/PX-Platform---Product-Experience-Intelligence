// PX Platform Web SDK
// US-001: SDK Web Básico

interface PXConfig {
  apiKey: string;
  projectId: string;
  endpoint?: string;
  bufferSize?: number;
  flushInterval?: number;
  debug?: boolean;
}

interface PXEvent {
  event: string;
  userId?: string;
  sessionId?: string;
  timestamp?: string;
  properties?: Record<string, any>;
}

class PXClient {
  private config: PXConfig;
  private buffer: PXEvent[] = [];
  private sessionId: string;
  private flushTimer?: NodeJS.Timeout;

  constructor(config: PXConfig) {
    this.config = {
      endpoint: 'https://api.px-platform.com',
      bufferSize: 100,
      flushInterval: 5000,
      debug: false,
      ...config
    };
    this.sessionId = this.generateSessionId();
    this.startAutoFlush();
    this.setupAutoCapture();
  }

  // Track custom events
  track(event: string, properties: Record<string, any> = {}): void {
    const pxEvent: PXEvent = {
      event,
      sessionId: this.sessionId,
      timestamp: new Date().toISOString(),
      properties: {
        ...properties,
        url: window.location.href,
        referrer: document.referrer,
        user_agent: navigator.userAgent
      }
    };

    this.addToBuffer(pxEvent);
  }

  // Identify user
  identify(userId: string, traits: Record<string, any> = {}): void {
    this.track('user_identified', { userId, ...traits });
  }

  // Add event to buffer
  private addToBuffer(event: PXEvent): void {
    this.buffer.push(event);
    
    if (this.buffer.length >= this.config.bufferSize!) {
      this.flush();
    }
  }

  // Flush events to API
  async flush(): Promise<void> {
    if (this.buffer.length === 0) return;

    const events = this.buffer.splice(0);
    
    try {
      await this.sendEvents(events);
      if (this.config.debug) {
        console.log(`PX: Flushed ${events.length} events`);
      }
    } catch (error) {
      // Retry logic - add back to buffer
      this.buffer.unshift(...events);
      if (this.config.debug) {
        console.error('PX: Failed to send events:', error);
      }
    }
  }

  // Send events to API with retry
  private async sendEvents(events: PXEvent[], retries = 3): Promise<void> {
    const payload = { events };
    
    for (let i = 0; i < retries; i++) {
      try {
        const response = await fetch(`${this.config.endpoint}/api/v1/events/batch`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.config.apiKey}`,
            'X-PX-Project-ID': this.config.projectId,
            'Content-Encoding': 'gzip'
          },
          body: JSON.stringify(payload)
        });

        if (response.ok) return;
        
        if (response.status === 429) {
          // Rate limited - wait and retry
          await this.sleep(Math.pow(2, i) * 1000);
          continue;
        }
        
        throw new Error(`HTTP ${response.status}`);
      } catch (error) {
        if (i === retries - 1) throw error;
        await this.sleep(Math.pow(2, i) * 1000);
      }
    }
  }

  // Auto-capture page views, clicks, scrolls
  private setupAutoCapture(): void {
    // Page view
    this.track('page_view', {
      title: document.title,
      path: window.location.pathname
    });

    // Click tracking
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      this.track('click', {
        element: target.tagName.toLowerCase(),
        text: target.textContent?.slice(0, 100),
        x: e.clientX,
        y: e.clientY
      });
    });

    // Scroll tracking
    let scrollTimeout: NodeJS.Timeout;
    document.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        const scrollPercent = Math.round(
          (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
        );
        this.track('scroll', { scroll_percent: scrollPercent });
      }, 500);
    });

    // Page unload
    window.addEventListener('beforeunload', () => {
      this.flush();
    });
  }

  // Auto-flush timer
  private startAutoFlush(): void {
    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.config.flushInterval);
  }

  // Utilities
  private generateSessionId(): string {
    return 'sess_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Cleanup
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    this.flush();
  }
}

// Global instance
let px: PXClient | null = null;

// Main API
const PX = {
  init(config: PXConfig): void {
    px = new PXClient(config);
  },

  track(event: string, properties?: Record<string, any>): void {
    px?.track(event, properties);
  },

  identify(userId: string, traits?: Record<string, any>): void {
    px?.identify(userId, traits);
  },

  flush(): Promise<void> {
    return px?.flush() || Promise.resolve();
  }
};

export default PX;
export { PXClient, PXConfig, PXEvent };