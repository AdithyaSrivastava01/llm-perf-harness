"use client";

interface ReportCardProps {
  gradeLetter: string;
  gradeScore: number;
  passRate: number;
  totalCases: number;
  passed: number;
  failed: number;
  avgLatencyMs: number;
  metricAverages: Record<string, number>;
}

const gradeColors: Record<string, string> = {
  A: "text-green-400 border-green-400",
  B: "text-blue-400 border-blue-400",
  C: "text-yellow-400 border-yellow-400",
  D: "text-orange-400 border-orange-400",
  F: "text-red-400 border-red-400",
};

export function ReportCard({
  gradeLetter,
  gradeScore,
  passRate,
  totalCases,
  passed,
  failed,
  avgLatencyMs,
  metricAverages,
}: ReportCardProps) {
  const color = gradeColors[gradeLetter] || "text-gray-400 border-gray-400";
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-lg">
      <div className="flex items-center gap-4 mb-4">
        <div
          className={`text-5xl font-bold border-2 rounded-lg px-4 py-2 ${color}`}
        >
          {gradeLetter}
        </div>
        <div>
          <p className="text-2xl font-semibold text-white">{gradeScore}%</p>
          <p className="text-sm text-gray-400">Agent Quality Score</p>
        </div>
      </div>
      <div className="space-y-2 mb-4">
        {Object.entries(metricAverages).map(([name, score]) => (
          <div key={name} className="flex items-center gap-2">
            <span className="text-xs text-gray-400 w-40 truncate">{name}</span>
            <div className="flex-1 bg-gray-800 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${score >= 0.8 ? "bg-green-500" : score >= 0.6 ? "bg-yellow-500" : "bg-red-500"}`}
                style={{ width: `${Math.round(score * 100)}%` }}
              />
            </div>
            <span className="text-xs text-gray-300 w-10 text-right">
              {Math.round(score * 100)}%
            </span>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-sm">
        <div className="bg-gray-800 rounded p-2">
          <p className="text-white font-medium">
            {passed}/{totalCases}
          </p>
          <p className="text-gray-500 text-xs">Pass Rate</p>
        </div>
        <div className="bg-gray-800 rounded p-2">
          <p className="text-white font-medium">{Math.round(avgLatencyMs)}ms</p>
          <p className="text-gray-500 text-xs">Avg Latency</p>
        </div>
        <div className="bg-gray-800 rounded p-2">
          <p
            className={`font-medium ${failed > 0 ? "text-red-400" : "text-green-400"}`}
          >
            {failed}
          </p>
          <p className="text-gray-500 text-xs">Failures</p>
        </div>
      </div>
    </div>
  );
}
