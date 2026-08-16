import { useState, useEffect, useCallback, useRef } from 'react';

interface UseAutoRefreshOptions {
  intervalMs?: number;
  defaultEnabled?: boolean;
}

export function useAutoRefresh(
  fetchCallback: () => Promise<void> | void,
  options: UseAutoRefreshOptions = {}
) {
  const { intervalMs = 15000, defaultEnabled = true } = options;

  const [enabled, setEnabled] = useState(defaultEnabled);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());

  const callbackRef = useRef(fetchCallback);
  callbackRef.current = fetchCallback;

  const refreshNow = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await callbackRef.current();
      setLastRefreshedAt(new Date());
    } catch (err) {
      console.error('Auto-refresh callback error:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    const timer = setInterval(() => {
      refreshNow();
    }, intervalMs);

    return () => clearInterval(timer);
  }, [enabled, intervalMs, refreshNow]);

  const toggleAutoRefresh = useCallback(() => {
    setEnabled((prev) => !prev);
  }, []);

  return {
    enabled,
    isRefreshing,
    lastRefreshedAt,
    refreshNow,
    toggleAutoRefresh,
    setEnabled,
  };
}
