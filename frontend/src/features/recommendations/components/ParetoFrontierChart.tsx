import React, { useState } from "react";
import { Star, Info } from "lucide-react";
import type { RecommendationCandidateResponse } from "../types";

interface ParetoFrontierChartProps {
  candidates: RecommendationCandidateResponse[];
}

export const ParetoFrontierChart: React.FC<ParetoFrontierChartProps> = ({ candidates }) => {
  const [xAxisKey, setXAxisKey] = useState<string>("latency_p95_ms");
  const [yAxisKey, setYAxisKey] = useState<string>("aggregate_score");
  const [hoveredCandidate, setHoveredCandidate] = useState<RecommendationCandidateResponse | null>(null);

  const axisOptions: { key: string; label: string; unit: string; direction: "MAXIMIZE" | "MINIMIZE" }[] = [
    { key: "aggregate_score", label: "Quality Score", unit: "pts", direction: "MAXIMIZE" },
    { key: "latency_p95_ms", label: "P95 Latency", unit: "ms", direction: "MINIMIZE" },
    { key: "latency_p50_ms", label: "P50 Latency", unit: "ms", direction: "MINIMIZE" },
    { key: "required_ram_mb", label: "Peak RAM", unit: "MB", direction: "MINIMIZE" },
    { key: "artifact_size_mb", label: "Artifact Size", unit: "MB", direction: "MINIMIZE" },
    { key: "estimated_cost_usd", label: "Estimated Cost", unit: "USD", direction: "MINIMIZE" },
  ];

  const xOption = axisOptions.find((a) => a.key === xAxisKey) || axisOptions[1];
  const yOption = axisOptions.find((a) => a.key === yAxisKey) || axisOptions[0];

  // Extract numerical points
  const points = candidates
    .map((c) => {
      const raw = c.objective_values;
      const xVal = Number(raw[xAxisKey]);
      const yVal = Number(raw[yAxisKey]);
      if (isNaN(xVal) || isNaN(yVal)) return null;
      return {
        candidate: c,
        x: xVal,
        y: yVal,
        isFrontier: c.pareto_frontier_member,
        isEligible: c.eligibility_status === "ELIGIBLE",
      };
    })
    .filter((p): p is NonNullable<typeof p> => p !== null);

  // Compute SVG Bounds
  const width = 640;
  const height = 360;
  const padding = 60;

  const xVals = points.map((p) => p.x);
  const yVals = points.map((p) => p.y);

  const minX = xVals.length > 0 ? Math.min(...xVals) : 0;
  const maxX = xVals.length > 0 ? Math.max(...xVals) : 100;
  const minY = yVals.length > 0 ? Math.min(...yVals) : 0;
  const maxY = yVals.length > 0 ? Math.max(...yVals) : 100;

  // Add margin
  const rangeX = maxX === minX ? 1 : maxX - minX;
  const rangeY = maxY === minY ? 1 : maxY - minY;

  const domainMinX = minX - rangeX * 0.1;
  const domainMaxX = maxX + rangeX * 0.1;
  const domainMinY = Math.max(0, minY - rangeY * 0.1);
  const domainMaxY = maxY + rangeY * 0.1;

  const scaleX = (x: number) =>
    padding + ((x - domainMinX) / (domainMaxX - domainMinX)) * (width - 2 * padding);
  const scaleY = (y: number) =>
    height - padding - ((y - domainMinY) / (domainMaxY - domainMinY)) * (height - 2 * padding);

  // Frontier points sorted for trade-off curve
  const frontierPoints = points
    .filter((p) => p.isFrontier)
    .sort((a, b) => a.x - b.x);

  return (
    <div className="space-y-6">
      {/* Chart Configuration Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 border border-neutral-800 rounded-xl bg-neutral-950/40">
        <div className="flex items-center gap-4 text-xs">
          <div>
            <label className="text-neutral-400 block mb-1 font-medium">Y-Axis Metric</label>
            <select
              value={yAxisKey}
              onChange={(e) => setYAxisKey(e.target.value)}
              className="px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-neutral-100 font-medium focus:outline-none focus:border-emerald-500"
            >
              {axisOptions.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label} ({opt.unit}) — {opt.direction === "MAXIMIZE" ? "Higher is better" : "Lower is better"}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-neutral-400 block mb-1 font-medium">X-Axis Metric</label>
            <select
              value={xAxisKey}
              onChange={(e) => setXAxisKey(e.target.value)}
              className="px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-neutral-100 font-medium focus:outline-none focus:border-emerald-500"
            >
              {axisOptions.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label} ({opt.unit}) — {opt.direction === "MAXIMIZE" ? "Higher is better" : "Lower is better"}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-neutral-400">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-emerald-400/40 inline-block" />
            <span>Pareto Frontier Optimal</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-neutral-500 inline-block" />
            <span>Dominated</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full border border-red-400 bg-red-950/40 inline-block" />
            <span>Ineligible</span>
          </div>
        </div>
      </div>

      {/* SVG Scatter Plot */}
      <div className="relative border border-neutral-800 rounded-xl bg-neutral-950 p-4 overflow-hidden shadow-inner">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none"
        >
          {/* Grid lines */}
          <line
            x1={padding}
            y1={height - padding}
            x2={width - padding}
            y2={height - padding}
            stroke="#333"
            strokeWidth="1"
          />
          <line
            x1={padding}
            y1={padding}
            x2={padding}
            y2={height - padding}
            stroke="#333"
            strokeWidth="1"
          />

          {/* Sub-grid guides */}
          {[0.25, 0.5, 0.75].map((fraction) => {
            const yGuide = padding + (height - 2 * padding) * fraction;
            const xGuide = padding + (width - 2 * padding) * fraction;
            return (
              <React.Fragment key={fraction}>
                <line
                  x1={padding}
                  y1={yGuide}
                  x2={width - padding}
                  y2={yGuide}
                  stroke="#222"
                  strokeDasharray="3 3"
                />
                <line
                  x1={xGuide}
                  y1={padding}
                  x2={xGuide}
                  y2={height - padding}
                  stroke="#222"
                  strokeDasharray="3 3"
                />
              </React.Fragment>
            );
          })}

          {/* Directional labels */}
          <text
            x={padding}
            y={padding - 15}
            fill="#10b981"
            fontSize="10"
            fontWeight="bold"
          >
            {yOption.direction === "MAXIMIZE" ? "↑ More Desirable (Higher)" : "↓ More Desirable (Lower)"}
          </text>
          <text
            x={width - padding}
            y={height - padding + 35}
            textAnchor="end"
            fill="#10b981"
            fontSize="10"
            fontWeight="bold"
          >
            {xOption.direction === "MINIMIZE" ? "← More Desirable (Lower)" : "→ More Desirable (Higher)"}
          </text>

          {/* Axis Titles */}
          <text
            x={width / 2}
            y={height - 15}
            textAnchor="middle"
            fill="#a3a3a3"
            fontSize="11"
            fontWeight="500"
          >
            {xOption.label} ({xOption.unit})
          </text>
          <text
            transform={`rotate(-90 20 ${height / 2})`}
            x={20}
            y={height / 2}
            textAnchor="middle"
            fill="#a3a3a3"
            fontSize="11"
            fontWeight="500"
          >
            {yOption.label} ({yOption.unit})
          </text>

          {/* Pareto Frontier connecting polyline */}
          {frontierPoints.length > 1 && (
            <polyline
              points={frontierPoints.map((p) => `${scaleX(p.x)},${scaleY(p.y)}`).join(" ")}
              fill="none"
              stroke="#10b981"
              strokeWidth="2"
              strokeDasharray="4 2"
              opacity="0.85"
            />
          )}

          {/* Candidate Scatter Points */}
          {points.map((p, idx) => {
            const cx = scaleX(p.x);
            const cy = scaleY(p.y);
            const isHovered = hoveredCandidate?.id === p.candidate.id;

            if (p.isFrontier) {
              return (
                <g
                  key={idx}
                  onMouseEnter={() => setHoveredCandidate(p.candidate)}
                  onMouseLeave={() => setHoveredCandidate(null)}
                  className="cursor-pointer"
                >
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isHovered ? 9 : 6}
                    fill="#10b981"
                    stroke="#ffffff"
                    strokeWidth="2"
                    className="transition-all"
                  />
                  <text
                    x={cx}
                    y={cy - 12}
                    textAnchor="middle"
                    fill="#34d399"
                    fontSize="9"
                    fontWeight="bold"
                  >
                    {p.candidate.candidate_label.split(" - ")[1] || `Trial #${idx + 1}`}
                  </text>
                </g>
              );
            }

            if (!p.isEligible) {
              return (
                <circle
                  key={idx}
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 6 : 4}
                  fill="#7f1d1d"
                  stroke="#ef4444"
                  strokeWidth="1.5"
                  strokeDasharray="2 2"
                  onMouseEnter={() => setHoveredCandidate(p.candidate)}
                  onMouseLeave={() => setHoveredCandidate(null)}
                  className="cursor-pointer"
                />
              );
            }

            return (
              <circle
                key={idx}
                cx={cx}
                cy={cy}
                r={isHovered ? 6 : 4}
                fill="#525252"
                stroke="#737373"
                strokeWidth="1"
                onMouseEnter={() => setHoveredCandidate(p.candidate)}
                onMouseLeave={() => setHoveredCandidate(null)}
                className="cursor-pointer transition-all hover:fill-neutral-300"
              />
            );
          })}
        </svg>

        {/* Floating Tooltip */}
        {hoveredCandidate && (
          <div className="absolute top-4 right-4 bg-neutral-900/95 border border-neutral-700 p-3 rounded-lg text-xs shadow-xl max-w-xs pointer-events-none backdrop-blur space-y-1">
            <span className="font-semibold text-neutral-100 block">
              {hoveredCandidate.candidate_label}
            </span>
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="text-neutral-400">Status:</span>
              <span
                className={
                  hoveredCandidate.pareto_frontier_member
                    ? "text-emerald-400 font-bold"
                    : "text-neutral-400"
                }
              >
                {hoveredCandidate.pareto_frontier_member ? "Pareto Frontier (Optimal)" : "Dominated"}
              </span>
            </div>
            <div className="text-[11px] text-neutral-300 space-y-0.5 pt-1 border-t border-neutral-800">
              <div>
                {yOption.label}:{" "}
                <span className="font-mono text-neutral-100">
                  {String(hoveredCandidate.objective_values[yAxisKey] ?? "N/A")} {yOption.unit}
                </span>
              </div>
              <div>
                {xOption.label}:{" "}
                <span className="font-mono text-neutral-100">
                  {String(hoveredCandidate.objective_values[xAxisKey] ?? "N/A")} {xOption.unit}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Accessible Tabular Dominance Relationships */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-emerald-500" />
          <h4 className="text-sm font-semibold text-neutral-200">
            Pareto Dominance Graph &amp; Non-Dominated Frontier
          </h4>
        </div>
        <p className="text-xs text-neutral-400">
          A candidate strictly dominates another when it is at least as good across all selected dimensions and strictly superior in at least one. Non-dominated configurations form the optimal frontier.
        </p>

        <div className="border border-neutral-800 rounded-lg overflow-x-auto bg-neutral-950/40">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-neutral-800 bg-neutral-900/50 text-neutral-400">
                <th className="py-2.5 px-3">Candidate</th>
                <th className="py-2.5 px-3">Frontier Status</th>
                <th className="py-2.5 px-3">Dominates (Superior to)</th>
                <th className="py-2.5 px-3">Dominated By (Inferior to)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/40">
              {candidates.map((cand) => (
                <tr key={cand.id} className="hover:bg-neutral-900/30">
                  <td className="py-2 px-3 font-medium text-neutral-200">
                    {cand.candidate_label}
                  </td>
                  <td className="py-2 px-3">
                    {cand.pareto_frontier_member ? (
                      <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                        <Star className="w-3 h-3 fill-emerald-400" /> Optimal Frontier
                      </span>
                    ) : (
                      <span className="text-neutral-500">Non-Frontier</span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-neutral-400">
                    {cand.dominates.length > 0
                      ? `${cand.dominates.length} configuration(s)`
                      : "None"}
                  </td>
                  <td className="py-2 px-3 text-neutral-400">
                    {cand.dominated_by.length > 0
                      ? `${cand.dominated_by.length} configuration(s)`
                      : "None (Non-dominated)"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
