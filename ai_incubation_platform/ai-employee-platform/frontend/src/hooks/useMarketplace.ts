/**
 * 市场数据 Hook
 */
import { useState, useCallback, useEffect } from 'react';
import { marketplaceApi } from '@/services';
import { type MarketplaceFilters } from '@/services/marketplaceApi';
import type { AIEmployee } from '@/types/employee';

export const useMarketplace = (initialFilters: MarketplaceFilters = {}) => {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<MarketplaceFilters>(initialFilters);

  // 获取市场数据
  const fetchMarketplace = useCallback(async (searchFilters?: MarketplaceFilters) => {
    setLoading(true);
    setError(null);
    try {
      const data = await marketplaceApi.list(searchFilters || filters);
      setEmployees(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取市场数据失败');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // 搜索
  const search = useCallback(async (searchFilters?: MarketplaceFilters) => {
    setLoading(true);
    setError(null);
    try {
      const data = await marketplaceApi.search(searchFilters || filters);
      setEmployees(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜索失败');
      return [];
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // 更新筛选条件
  const updateFilters = useCallback((newFilters: Partial<MarketplaceFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  // 重置筛选
  const resetFilters = useCallback(() => {
    setFilters(initialFilters);
  }, [initialFilters]);

  // 获取排行榜
  const getRankings = useCallback(async (type: 'top_rated' | 'most_hired' | 'newest' | 'trending', limit: number = 10) => {
    try {
      return await marketplaceApi.getRankings(type, limit);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取排行榜失败');
      return [];
    }
  }, []);

  // 获取精选推荐
  const getFeatured = useCallback(async (limit: number = 10) => {
    try {
      return await marketplaceApi.getFeatured(limit);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取推荐失败');
      return [];
    }
  }, []);

  // 获取市场统计
  const getStats = useCallback(async () => {
    try {
      return await marketplaceApi.getStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取统计失败');
      return null;
    }
  }, []);

  // 自动获取
  useEffect(() => {
    fetchMarketplace();
  }, [fetchMarketplace]);

  return {
    // 状态
    employees,
    loading,
    error,
    filters,

    // 方法
    fetchMarketplace,
    search,
    updateFilters,
    resetFilters,
    getRankings,
    getFeatured,
    getStats,
    setError,
  };
};
