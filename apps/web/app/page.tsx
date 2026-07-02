export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-[#0f0f11] text-[#fafafa] px-4">
      <main className="w-full max-w-md p-8 rounded-2xl border border-[#27272a]/60 bg-[#18181b]/40 backdrop-blur-md shadow-2xl flex flex-col items-center text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-cyan-500 to-fuchsia-500 flex items-center justify-center mb-6 shadow-lg shadow-cyan-500/20">
          <span className="text-2xl font-bold text-[#fafafa]">🕵️</span>
        </div>
        
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-[#fafafa] to-[#71717a] bg-clip-text text-transparent mb-2">
          AUE
        </h1>
        
        <p className="text-lg font-medium text-cyan-400/90 mb-4">
          Agentic Undercover Environment
        </p>
        
        <p className="text-sm text-[#71717a] leading-relaxed mb-8 max-w-xs">
          A behavioral laboratory and evaluation benchmark for LLM deception, trust, and reasoning.
        </p>

        <a
          href="#"
          className="group relative w-full h-12 flex items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-fuchsia-500 text-sm font-semibold text-[#fafafa] shadow-lg shadow-cyan-500/10 hover:shadow-cyan-500/25 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
        >
          Setup New Game
          <span className="ml-2 group-hover:translate-x-1 transition-transform duration-200">
            →
          </span>
        </a>
      </main>
    </div>
  );
}
