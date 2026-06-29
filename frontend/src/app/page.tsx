"use client";
import { CopilotChat } from "@copilotkit/react-ui";

export default function Home() {
  return (
    <div className="flex h-screen bg-gray-950">
      <aside className="w-64 border-r border-gray-800 p-4">
        <h1 className="text-xl font-bold text-white mb-4">Agent Evals</h1>
        <p className="text-sm text-gray-400">
          Chat with the eval harness to test and evaluate your AI agents.
        </p>
      </aside>
      <main className="flex-1 flex flex-col">
        <CopilotChat
          className="flex-1"
          instructions="You are the Agent-Evals Meta-Harness. Help users evaluate their AI agents."
          labels={{
            title: "Eval Harness",
            initial: "Hello! I can help you evaluate AI agents. Try asking me to list available agents.",
            placeholder: "Ask about agents, run evals, or explore results...",
          }}
        />
      </main>
    </div>
  );
}
