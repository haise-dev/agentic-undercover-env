import { type ReactNode } from "react";

interface AppShellProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export function AppShell({ sidebar, children }: AppShellProps) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-bg-primary text-text-primary">
      {/* Sidebar - fixed width on desktop, hidden or drawer on mobile (simplifying to hidden on small screens for now) */}
      <aside className="hidden md:flex w-72 flex-col border-r border-border bg-bg-secondary/50 backdrop-blur-xl">
        {sidebar}
      </aside>

      {/* Main Content Area */}
      <main className="flex flex-1 flex-col overflow-y-auto">
        <div className="mx-auto w-full max-w-5xl flex-1 p-4 md:p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
