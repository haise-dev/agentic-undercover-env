import { forwardRef } from "react";
import { cn } from "@/src/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "agent-0" | "agent-1" | "agent-2" | "agent-3";
  size?: "sm" | "md" | "lg";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-text-muted disabled:pointer-events-none disabled:opacity-50",
          {
            "bg-text-primary text-bg-primary hover:bg-text-primary/90": variant === "primary",
            "bg-bg-secondary text-text-primary border border-border hover:bg-border-hover": variant === "secondary",
            "bg-red-500 text-white hover:bg-red-500/90": variant === "danger",
            "hover:bg-bg-secondary hover:text-text-primary": variant === "ghost",
            "bg-agent-0/20 text-agent-0 border border-agent-0/50 hover:bg-agent-0/30 shadow-glow-0": variant === "agent-0",
            "bg-agent-1/20 text-agent-1 border border-agent-1/50 hover:bg-agent-1/30 shadow-glow-1": variant === "agent-1",
            "bg-agent-2/20 text-agent-2 border border-agent-2/50 hover:bg-agent-2/30 shadow-glow-2": variant === "agent-2",
            "bg-agent-3/20 text-agent-3 border border-agent-3/50 hover:bg-agent-3/30 shadow-glow-3": variant === "agent-3",
            
            "h-8 px-3 text-xs": size === "sm",
            "h-10 px-4 py-2 text-sm": size === "md",
            "h-12 px-8 text-base": size === "lg",
          },
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
