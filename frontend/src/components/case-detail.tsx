"use client";
import { useState } from "react";

interface MetricScore {
  name: string;
  score: number;
  passed: boolean;
  threshold: number;
}
interface CaseResult {
  test_case_id: string;
  passed: boolean;
  latency_ms: number;
  metrics: MetricScore[];
}

export function CaseDetail({ results }: { results: CaseResult[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  return (
    <div className="space-y-2 mt-4">
      <h3 className="text-sm font-medium text-gray-400">Test Cases</h3>
      {results.map((r) => (
        <div
          key={r.test_case_id}
          className="bg-gray-900 border border-gray-700 rounded"
        >
          <button
            className="w-full flex items-center justify-between p-3 text-left"
            onClick={() =>
              setExpanded(expanded === r.test_case_id ? null : r.test_case_id)
            }
          >
            <div className="flex items-center gap-2">
              <span
                className={`text-xs px-2 py-0.5 rounded ${r.passed ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}
              >
                {r.passed ? "PASS" : "FAIL"}
              </span>
              <span className="text-sm text-gray-300 font-mono">
                {r.test_case_id}
              </span>
            </div>
            <span className="text-xs text-gray-500">
              {Math.round(r.latency_ms)}ms
            </span>
          </button>
          {expanded === r.test_case_id && (
            <div className="px-3 pb-3 space-y-1">
              {r.metrics.map((m) => (
                <div key={m.name} className="flex items-center gap-2 text-xs">
                  <span
                    className={m.passed ? "text-green-400" : "text-red-400"}
                  >
                    {m.passed ? "✓" : "✗"}
                  </span>
                  <span className="text-gray-400">{m.name}:</span>
                  <span className="text-gray-200">
                    {(m.score * 100).toFixed(1)}%
                  </span>
                  <span className="text-gray-600">
                    (threshold: {(m.threshold * 100).toFixed(0)}%)
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
