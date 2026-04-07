/**
 * Toast 通知组件
 */
'use client';

import * as React from 'react';
import { ToastProvider, ToastViewport, Toast, ToastTitle, ToastDescription, ToastAction, ToastClose } from '@/components/ui/toast';
import { useAppStore } from '@/stores/useAppStore';
import { cn } from '@/lib/utils';

type ToastType = 'default' | 'destructive' | 'success' | 'info';

interface Toast {
  id: string;
  title?: string;
  description: string;
  type?: ToastType;
  action?: React.ReactElement<typeof ToastAction>;
}

export function Toaster() {
  const [toasts, setToasts] = React.useState<Toast[]>([]);
  const error = useAppStore((state) => state.error);

  React.useEffect(() => {
    if (error) {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [
        ...prev,
        { id, title: '错误', description: error, type: 'destructive' },
      ]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 3000);
    }
  }, [error]);

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastProvider>
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          variant={toast.type === 'destructive' ? 'destructive' : 'default'}
          open={true}
          onOpenChange={(open) => {
            if (!open) dismiss(toast.id);
          }}
        >
          {toast.title && <ToastTitle>{toast.title}</ToastTitle>}
          <ToastDescription>{toast.description}</ToastDescription>
          {toast.action}
          <ToastClose />
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  );
}

// 简单的 Toast  Hook
export function useToast() {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const toast = React.useCallback(
    ({ title, description, type = 'default' }: Omit<Toast, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, title, description, type }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 3000);

      return id;
    },
    []
  );

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, toast, dismiss };
}
