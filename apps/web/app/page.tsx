import { SetupWizard } from "@/src/components/setup/SetupWizard";
import { APIMonitor } from "@/src/components/game/APIMonitor";

export default function Home() {
  return (
    <div className="min-h-screen bg-bg-primary py-12 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-7xl space-y-8">
        <div className="text-center mb-6">
          <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-agent-0 to-agent-1 sm:text-5xl animate-pulse">
            Agentic Undercover
          </h1>
          <p className="mt-3 max-w-2xl mx-auto text-xl text-text-muted sm:mt-4">
            Configure the LLM agents, set the topic, and watch them debate to find the imposter.
          </p>
        </div>
        
        <SetupWizard />

        <div className="max-w-4xl mx-auto">
          <APIMonitor />
        </div>
      </div>
    </div>
  );
}
