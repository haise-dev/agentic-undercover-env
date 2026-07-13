"use client";

import { useSetupStore } from "@/src/store/useSetupStore";
import { Step1GameSettings } from "./Step1GameSettings";
import { Step2AgentConfig } from "./Step2AgentConfig";
import { Step3Review } from "./Step3Review";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Settings, Users, Play, HelpCircle } from "lucide-react";
import clsx from "clsx";

export function SetupWizard() {
  const { currentStep } = useSetupStore();

  const steps = [
    { number: 1, label: "Game Parameters", icon: Settings, color: "text-agent-0 border-agent-0 bg-agent-0/10" },
    { number: 2, label: "Configure Agents", icon: Users, color: "text-agent-1 border-agent-1 bg-agent-1/10" },
    { number: 3, label: "Review & Launch", icon: Play, color: "text-agent-2 border-agent-2 bg-agent-2/10" },
  ];

  return (
    <Card className="w-full max-w-4xl mx-auto shadow-xl bg-bg-secondary/20 backdrop-blur-xl border border-border/80 overflow-hidden">
      {/* Progress Header */}
      <div className="bg-bg-secondary/40 border-b border-border/80 px-6 py-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <CardTitle className="text-2xl font-black bg-gradient-to-r from-agent-0 to-agent-2 bg-clip-text text-transparent">
            New Undercover Episode
          </CardTitle>
          
          {/* Progress Bar / Steps indicator */}
          <div className="flex items-center space-x-2.5 sm:space-x-4">
            {steps.map((step, idx) => {
              const StepIcon = step.icon;
              const isActive = currentStep === step.number;
              const isCompleted = currentStep > step.number;

              return (
                <div key={step.number} className="flex items-center">
                  <div
                    className={clsx(
                      "flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-full border text-xs font-bold transition-all duration-300",
                      isActive
                        ? `${step.color} shadow-sm scale-105`
                        : isCompleted
                        ? "text-green-400 border-green-500/50 bg-green-500/10"
                        : "text-text-muted border-border bg-transparent"
                    )}
                  >
                    <StepIcon className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">{step.label}</span>
                    <span className="sm:hidden">{step.number}</span>
                  </div>
                  {idx < steps.length - 1 && (
                    <div
                      className={clsx(
                        "w-4 sm:w-6 h-[2px] mx-1 sm:mx-2 rounded",
                        currentStep > step.number ? "bg-green-500/50" : "bg-border"
                      )}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <CardContent className="p-6">
        {currentStep === 1 && <Step1GameSettings />}
        {currentStep === 2 && <Step2AgentConfig />}
        {currentStep === 3 && <Step3Review />}
      </CardContent>
    </Card>
  );
}
