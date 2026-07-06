import { forwardRef } from "react";
import { cn } from "@/src/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "outline" | "agent-0" | "agent-1" | "agent-2" | "agent-3";
}

const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors",
          {
            "bg-bg-secondary text-text-primary border border-border": variant === "default",
            "border border-border text-text-muted": variant === "outline",
            "bg-agent-0/20 text-agent-0 border border-agent-0/30": variant === "agent-0",
            "bg-agent-1/20 text-agent-1 border border-agent-1/30": variant === "agent-1",
            "bg-agent-2/20 text-agent-2 border border-agent-2/30": variant === "agent-2",
            "bg-agent-3/20 text-agent-3 border border-agent-3/30": variant === "agent-3",
          },
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";

export { Badge };
