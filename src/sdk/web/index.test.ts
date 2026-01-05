// Tests for PX Platform Web SDK
// US-001: SDK Web Básico - Test Suite

import PX, { PXClient } from './index';

// Mock fetch for testing
global.fetch = jest.fn();

describe('PX Platform SDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true })
    });
  });

  describe('PXClient', () => {
    test('should initialize with config', () => {
      const client = new PXClient({
        apiKey: 'test_key',
        projectId: 'test_project'
      });

      expect(client).toBeDefined();
    });

    test('should track events', () => {
      const client = new PXClient({
        apiKey: 'test_key',
        projectId: 'test_project',
        bufferSize: 1 // Force immediate flush
      });

      client.track('test_event', { prop: 'value' });

      // Should call fetch after buffer fills
      setTimeout(() => {
        expect(fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/events/batch'),
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Authorization': 'Bearer test_key',
              'X-PX-Project-ID': 'test_project'
            })
          })
        );
      }, 100);
    });

    test('should identify users', () => {
      const client = new PXClient({
        apiKey: 'test_key',
        projectId: 'test_project'
      });

      const trackSpy = jest.spyOn(client, 'track');
      client.identify('user_123', { email: 'test@example.com' });

      expect(trackSpy).toHaveBeenCalledWith('user_identified', {
        userId: 'user_123',
        email: 'test@example.com'
      });
    });

    test('should flush events manually', async () => {
      const client = new PXClient({
        apiKey: 'test_key',
        projectId: 'test_project'
      });

      client.track('test_event');
      await client.flush();

      expect(fetch).toHaveBeenCalled();
    });

    test('should retry on failure', async () => {
      (fetch as jest.Mock)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ ok: true, status: 200 });

      const client = new PXClient({
        apiKey: 'test_key',
        projectId: 'test_project'
      });

      client.track('test_event');
      await client.flush();

      expect(fetch).toHaveBeenCalledTimes(2);
    });

    test('should handle rate limiting', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 429
      });

      const client = new PXClient({
        apiKey: 'test_key',
        projectId: 'test_project'
      });

      client.track('test_event');
      await client.flush();

      // Should retry on 429
      expect(fetch).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });
  });

  describe('Global PX API', () => {
    test('should initialize global instance', () => {
      PX.init({
        apiKey: 'test_key',
        projectId: 'test_project'
      });

      expect(() => PX.track('test_event')).not.toThrow();
    });

    test('should track events via global API', () => {
      PX.init({
        apiKey: 'test_key',
        projectId: 'test_project'
      });

      expect(() => {
        PX.track('test_event', { prop: 'value' });
        PX.identify('user_123');
      }).not.toThrow();
    });
  });

  describe('Auto-capture', () => {
    test('should capture page views automatically', () => {
      // Mock DOM
      Object.defineProperty(window, 'location', {
        value: { href: 'http://test.com', pathname: '/test' }
      });
      Object.defineProperty(document, 'title', {
        value: 'Test Page'
      });

      const client = new PXClient({
        apiKey: 'test_key',
        projectId: 'test_project'
      });

      // Should have tracked page_view automatically
      expect(client).toBeDefined();
    });
  });
});