"use client";
import { useState } from "react";
import { ReportCard } from "@/components/report-card";
import { CaseDetail } from "@/components/case-detail";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Step = "input" | "probing" | "confirm" | "running" | "done";

export default function QuickEvalPage() {
  const [step, setStep] = useState<Step>("input");
  const [url, setUrl] = useState("");
  const [authHeader, setAuthHeader] = useState("");
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleProbe() {
    setStep("probing");
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/probe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint_url: url,
          auth_header: authHeader || null,
        }),
      });
      const data = await res.json();
      if (!data.reachable) {
        setError(data.error || "Agent not reachable");
        setStep("input");
        return;
      }
      setCapabilities(data.detected_capabilities);
      setStep("confirm");
    } catch (e: any) {
      setError(e.message);
      setStep("input");
    }
  }

  async function handleEval() {
    setStep("running");
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/quick-eval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint_url: url,
          auth_header: authHeader || null,
          capabilities,
          num_cases: 5,
        }),
      });
      const data = await res.json();
      setResult(data);
      setStep("done");
    } catch (e: any) {
      setError(e.message);
      setStep("confirm");
    }
  }

  function toggleCap(cap: string) {
    setCapabilities((prev) =>
      prev.includes(cap) ? prev.filter((c) => c !== cap) : [...prev, cap],
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        <h1 className="text-3xl font-bold text-white mb-2">Quick Eval</h1>
        <p className="text-gray-400 mb-8">
          Paste your agent endpoint. Get a quality report in 2 minutes.
        </p>
        {error && (
          <div className="bg-red-900/50 border border-red-700 rounded p-3 mb-4 text-red-300 text-sm">
            {error}
          </div>
        )}
        {step === "input" && (
          <div className="space-y-4">
            <input
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500"
              placeholder="https://your-agent.com/v1/chat/completions"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <input
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500"
              placeholder="Bearer sk-... (optional)"
              value={authHeader}
              onChange={(e) => setAuthHeader(e.target.value)}
            />
            <button
              className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-3 font-medium disabled:opacity-50"
              onClick={handleProbe}
              disabled={!url}
            >
              Scan Agent
            </button>
          </div>
        )}
        {step === "probing" && (
          <div className="text-center py-8">
            <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-400">Probing agent capabilities...</p>
          </div>
        )}
        {step === "confirm" && (
          <div className="space-y-4">
            <p className="text-gray-300">
              Detected capabilities — confirm or adjust:
            </p>
            <div className="flex gap-2 flex-wrap">
              {["text", "tools", "rag"].map((cap) => (
                <button
                  key={cap}
                  className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${capabilities.includes(cap) ? "bg-blue-600 border-blue-500 text-white" : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-500"}`}
                  onClick={() => toggleCap(cap)}
                >
                  {cap}
                </button>
              ))}
            </div>
            <button
              className="w-full bg-green-600 hover:bg-green-700 text-white rounded-lg py-3 font-medium"
              onClick={handleEval}
            >
              Run Eval
            </button>
          </div>
        )}
        {step === "running" && (
          <div className="text-center py-8">
            <div className="animate-spin h-8 w-8 border-2 border-green-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-400">Running evaluation...</p>
          </div>
        )}
        {step === "done" && result && (
          <div>
            <ReportCard
              gradeLetter={result.grade_letter}
              gradeScore={result.grade_score}
              passRate={result.pass_rate}
              totalCases={result.total_cases}
              passed={result.passed}
              failed={result.failed}
              avgLatencyMs={result.avg_latency_ms}
              metricAverages={result.metric_averages}
            />
            <CaseDetail results={result.results} />
            <button
              className="mt-4 w-full bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2 text-sm"
              onClick={() => {
                setStep("input");
                setResult(null);
              }}
            >
              Evaluate Another Agent
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
