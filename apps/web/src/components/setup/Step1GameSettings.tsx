"use client";

import { useSetupStore } from "@/src/store/useSetupStore";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { Settings, Info } from "lucide-react";

export function Step1GameSettings() {
  const { topic, secretWord, maxRounds, setTopic, setSecretWord, setMaxRounds, nextStep } =
    useSetupStore();

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    if (topic.trim() && secretWord.trim()) {
      nextStep();
    }
  };

  return (
    <form onSubmit={handleNext} className="space-y-6 animate-fade-in">
      <div className="bg-bg-secondary/40 backdrop-blur-md p-6 rounded-2xl border border-border/80 space-y-6">
        <div className="flex items-center space-x-3 border-b border-border pb-4">
          <Settings className="w-6 h-6 text-agent-0" />
          <h3 className="text-xl font-bold text-text-primary">Game parameters</h3>
        </div>

        <div className="space-y-4">
          {/* Discussion Topic */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-text-muted uppercase tracking-wider">
              Discussion Topic
            </label>
            <Input
              placeholder="e.g. Programming Languages, Food, Countries..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
              className="bg-bg-primary/50 focus:ring-2 focus:ring-agent-0/50"
            />
            <p className="text-xs text-text-muted flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-agent-0" />
              This is the general theme that players will be discussing.
            </p>
          </div>

          {/* Secret Word */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-text-muted uppercase tracking-wider">
              Secret Word (for Villagers)
            </label>
            <Input
              placeholder="e.g. Python, Pizza, Japan..."
              value={secretWord}
              onChange={(e) => setSecretWord(e.target.value)}
              required
              className="bg-bg-primary/50 focus:ring-2 focus:ring-agent-0/50"
            />
            <p className="text-xs text-text-muted flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-agent-0" />
              The Imposter will receive a slightly different word or no word depending on role assignments.
            </p>
          </div>

          {/* Max Rounds */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-text-muted uppercase tracking-wider">
              Max Rounds
            </label>
            <select
              value={maxRounds}
              onChange={(e) => setMaxRounds(Number(e.target.value))}
              className="w-full bg-bg-primary/50 border border-border rounded-lg px-4 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-agent-0/50"
            >
              {[3, 4, 5, 6].map((rounds) => (
                <option key={rounds} value={rounds} className="bg-bg-primary">
                  {rounds} Rounds
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="flex justify-end pt-4">
        <Button
          type="submit"
          variant="agent-0"
          size="lg"
          disabled={!topic.trim() || !secretWord.trim()}
          className="w-full sm:w-auto px-8 py-3 bg-gradient-to-r from-agent-0 to-agent-1 text-white shadow-lg shadow-agent-0/20 hover:shadow-agent-0/40 hover:-translate-y-0.5 transition-all duration-200"
        >
          Next: Setup Roster
        </Button>
      </div>
    </form>
  );
}
