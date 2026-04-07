/**
 * 员工管理 Hook
 */
import { useState, useCallback, useEffect } from 'react';
import { employeeApi } from '@/services';
import type { AIEmployee, AIEmployeeCreate, EmployeeStatus, EmployeeSearchParams } from '@/types/employee';

interface UseEmployeesOptions {
  autoFetch?: boolean;
  status?: EmployeeStatus;
}

export const useEmployees = (options: UseEmployeesOptions = {}) => {
  const { autoFetch = true, status } = options;
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 获取员工列表
  const fetchEmployees = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await employeeApi.list(status);
      setEmployees(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取员工列表失败');
    } finally {
      setLoading(false);
    }
  }, [status]);

  // 获取员工详情
  const fetchEmployee = useCallback(async (employeeId: string): Promise<AIEmployee | null> => {
    try {
      return await employeeApi.get(employeeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取员工详情失败');
      return null;
    }
  }, []);

  // 创建员工
  const createEmployee = useCallback(async (data: AIEmployeeCreate, ownerId: string): Promise<AIEmployee | null> => {
    try {
      const employee = await employeeApi.create(data, ownerId);
      await fetchEmployees();
      return employee;
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建员工失败');
      return null;
    }
  }, [fetchEmployees]);

  // 上架员工
  const publishEmployee = useCallback(async (employeeId: string): Promise<boolean> => {
    try {
      await employeeApi.publish(employeeId);
      await fetchEmployees();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : '上架员工失败');
      return false;
    }
  }, [fetchEmployees]);

  // 下线员工
  const offlineEmployee = useCallback(async (employeeId: string): Promise<boolean> => {
    try {
      await employeeApi.offline(employeeId);
      await fetchEmployees();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : '下线员工失败');
      return false;
    }
  }, [fetchEmployees]);

  // 搜索员工
  const searchEmployees = useCallback(async (params: EmployeeSearchParams): Promise<AIEmployee[]> => {
    try {
      return await employeeApi.search(params);
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜索员工失败');
      return [];
    }
  }, []);

  // 自动获取
  useEffect(() => {
    if (autoFetch) {
      fetchEmployees();
    }
  }, [autoFetch, fetchEmployees]);

  return {
    // 状态
    employees,
    loading,
    error,

    // 方法
    fetchEmployees,
    fetchEmployee,
    createEmployee,
    publishEmployee,
    offlineEmployee,
    searchEmployees,
    setError,
  };
};
