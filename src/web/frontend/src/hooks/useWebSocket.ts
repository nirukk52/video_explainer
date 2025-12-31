import { useEffect, useRef, useState, useCallback } from 'react';
import type { Job, WebSocketMessage } from '../types';

interface UseWebSocketOptions {
  projectId?: string;
  onJobUpdate?: (job: Job) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { projectId, onJobUpdate } = options;
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/ws`);

    ws.onopen = () => {
      setIsConnected(true);
      // Subscribe to project updates if projectId is provided
      if (projectId) {
        ws.send(JSON.stringify({ type: 'subscribe', project_id: projectId }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        if (message.type === 'job_update' && message.job && onJobUpdate) {
          onJobUpdate(message.job);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [projectId, onJobUpdate]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const subscribe = useCallback((pid: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', project_id: pid }));
    }
  }, []);

  const unsubscribe = useCallback((pid: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'unsubscribe', project_id: pid }));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Subscribe when projectId changes
  useEffect(() => {
    if (projectId && isConnected) {
      subscribe(projectId);
    }
  }, [projectId, isConnected, subscribe]);

  return {
    isConnected,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
  };
}
