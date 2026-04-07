import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productApi, groupBuyApi, orderApi, couponApi, organizerApi, notificationApi, analyticsApi, aiToolsApi } from '@/services/api'
import type { ProductFilter, OrderFilter } from '@/types'

// Products
export function useProducts(filter?: ProductFilter) {
  return useQuery({
    queryKey: ['products', filter],
    queryFn: () => productApi.getList(filter),
  })
}

export function useProduct(id: number) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => productApi.getById(id),
    enabled: !!id,
  })
}

export function useHotProducts(limit = 10) {
  return useQuery({
    queryKey: ['hotProducts', limit],
    queryFn: () => productApi.getHot(limit),
  })
}

export function useCreateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: productApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useUpdateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => productApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useDeleteProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: productApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

// Group Buys
export function useGroupBuys(status?: string) {
  return useQuery({
    queryKey: ['groupBuys', status],
    queryFn: () => groupBuyApi.getList(status),
  })
}

export function useGroupBuy(id: number) {
  return useQuery({
    queryKey: ['groupBuy', id],
    queryFn: () => groupBuyApi.getById(id),
    enabled: !!id,
  })
}

export function useGroupPrediction(id: number) {
  return useQuery({
    queryKey: ['groupPrediction', id],
    queryFn: () => groupBuyApi.getPrediction(id),
    enabled: !!id,
  })
}

export function useBatchPredictions() {
  return useQuery({
    queryKey: ['batchPredictions'],
    queryFn: () => groupBuyApi.getBatchPredictions(),
  })
}

export function useCreateGroupBuy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: groupBuyApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groupBuys'] })
    },
  })
}

export function useJoinGroupBuy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, userId }: { id: number; userId: string }) => groupBuyApi.join(id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groupBuys'] })
    },
  })
}

// Orders
export function useOrders(filter?: OrderFilter) {
  return useQuery({
    queryKey: ['orders', filter],
    queryFn: () => orderApi.getList(filter),
  })
}

export function useOrder(id: number) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: () => orderApi.getById(id),
    enabled: !!id,
  })
}

export function useCreateOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: orderApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

// Coupons
export function useCouponTemplates() {
  return useQuery({
    queryKey: ['couponTemplates'],
    queryFn: () => couponApi.getTemplates(),
  })
}

export function useUserCoupons(userId: string) {
  return useQuery({
    queryKey: ['userCoupons', userId],
    queryFn: () => couponApi.getUserCoupons(userId),
    enabled: !!userId,
  })
}

export function useClaimCoupon() {
  return useMutation({
    mutationFn: couponApi.claim,
  })
}

// Organizer
export function useOrganizerProfile(userId: string) {
  return useQuery({
    queryKey: ['organizerProfile', userId],
    queryFn: () => organizerApi.getProfile(userId),
    enabled: !!userId,
  })
}

export function useOrganizerRanking() {
  return useQuery({
    queryKey: ['organizerRanking'],
    queryFn: () => organizerApi.getRanking(),
  })
}

export function useCommissionRecords(userId: string) {
  return useQuery({
    queryKey: ['commissionRecords', userId],
    queryFn: () => organizerApi.getCommissionRecords(userId),
    enabled: !!userId,
  })
}

// Notifications
export function useNotifications(userId: string, unreadOnly = false) {
  return useQuery({
    queryKey: ['notifications', userId, unreadOnly],
    queryFn: () => notificationApi.getList(userId, unreadOnly),
    enabled: !!userId,
  })
}

export function useMarkNotificationsRead() {
  return useMutation({
    mutationFn: notificationApi.markAsRead,
  })
}

export function useMarkAllNotificationsRead() {
  return useMutation({
    mutationFn: notificationApi.markAllAsRead,
  })
}

// Analytics
export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboardStats'],
    queryFn: () => analyticsApi.getDashboardStats(),
  })
}

// AI Tools
export function useStockAlert(threshold = 10) {
  return useQuery({
    queryKey: ['stockAlert', threshold],
    queryFn: () => aiToolsApi.getStockAlert(threshold),
  })
}

export function useDynamicPrice(productId: number, communityId: string) {
  return useQuery({
    queryKey: ['dynamicPrice', productId, communityId],
    queryFn: () => aiToolsApi.getDynamicPrice(productId, communityId),
    enabled: !!productId && !!communityId,
  })
}
