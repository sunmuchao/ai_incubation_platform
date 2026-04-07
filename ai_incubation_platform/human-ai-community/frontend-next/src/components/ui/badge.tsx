import * as React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'ai' | 'human';
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    const baseStyles =
      'inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2';

    const variants = {
      default: 'border-transparent bg-primary text-primary-foreground shadow',
      secondary: 'border-transparent bg-secondary text-secondary-foreground',
      destructive: 'border-transparent bg-destructive text-destructive-foreground shadow',
      outline: 'text-foreground',
      ai: 'border-transparent bg-blue-500/20 text-blue-400',
      human: 'border-transparent bg-green-500/20 text-green-400',
    };

    return (
      <div ref={ref} className={cn(baseStyles, variants[variant], className)} {...props} />
    );
  }
);
Badge.displayName = 'Badge';

export { Badge };
