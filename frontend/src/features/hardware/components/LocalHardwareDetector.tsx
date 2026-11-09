import React, { useState } from "react";
import { detectHardware, runBenchmark } from "../api";
import type { BenchmarkRun, LocalHardwareSnapshot } from "../types";

interface Props {
  workspaceId: string;
  initialSnapshot: LocalHardwareSnapshot | null;
  initialBenchmark: BenchmarkRun | null;
}

export const LocalHardwareDetector: React.FC<Props> = ({
  workspaceId,
  initialSnapshot,
  initialBenchmark,
}) => {
  const [snapshot, setSnapshot] = useState<LocalHardwareSnapshot | null>(initialSnapshot);
  const [benchmark, setBenchmark] = useState<BenchmarkRun | null>(initialBenchmark);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [matrixSize, setMatrixSize] = useState<number>(300);
  const [iterations, setIterations] = useState<number>(5);
  const [error, setError] = useState<string | null>(null);

  const handleDetect = async () => {
    setIsDetecting(true);
    setError(null);
    try {
      const snap = await detectHardware(workspaceId);
      setSnapshot(snap);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to inspect local hardware.");
    } finally {
      setIsDetecting(false);
    }
  };

  const handleBenchmark = async () => {
    setIsBenchmarking(true);
    setError(null);
    try {
      const bench = await runBenchmark(workspaceId, {
        matrix_size: matrixSize,
        iterations: iterations,
      });
      setBenchmark(bench);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run CPU benchmark.");
    } finally {
      setIsBenchmarking(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Hardware Inspection Card */}
      <div className="p-6 rounded-xl border border-neutral-800 bg-neutral-900/60">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="text-lg font-medium text-neutral-100">
              Host Workstation Inspection
            </h3>
            <p className="text-sm text-neutral-400 mt-1">
              Safely inspect CPU, system memory, OS, and GPU presence via standard platform APIs.
            </p>
          </div>
          <button
            type="button"
            onClick={handleDetect}
            disabled={isDetecting}
            className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors disabled:opacity-50"
          >
            {isDetecting ? "Inspecting Host..." : "Inspect Local Hardware"}
          </button>
        </div>

        {snapshot ? (
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 pt-5 border-t border-neutral-800">
            <div className="p-3.5 rounded-lg bg-neutral-950/60 border border-neutral-800/80">
              <span className="text-xs text-neutral-500 block">CPU Model</span>
              <span className="text-sm font-medium text-neutral-200 mt-0.5 block truncate" title={snapshot.cpu_model}>
                {snapshot.cpu_model}
              </span>
              <span className="text-xs text-neutral-400 mt-1 block">
                {snapshot.physical_cores ?? "?"} Physical / {snapshot.logical_cores ?? "?"} Logical Cores
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-neutral-950/60 border border-neutral-800/80">
              <span className="text-xs text-neutral-500 block">System RAM</span>
              <span className="text-sm font-medium text-neutral-200 mt-0.5 block">
                {(snapshot.system_ram_mb / 1024).toFixed(1)} GB Total
              </span>
              <span className="text-xs text-emerald-400 mt-1 block">
                {(snapshot.available_ram_mb / 1024).toFixed(1)} GB Available
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-neutral-950/60 border border-neutral-800/80">
              <span className="text-xs text-neutral-500 block">Operating System</span>
              <span className="text-sm font-medium text-neutral-200 mt-0.5 block">
                {snapshot.os_name} {snapshot.os_release}
              </span>
              <span className="text-xs text-neutral-400 mt-1 block">
                Arch: {snapshot.architecture}
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-neutral-950/60 border border-neutral-800/80">
              <span className="text-xs text-neutral-500 block">NVIDIA Accelerator</span>
              <span className="text-sm font-medium text-neutral-200 mt-0.5 block">
                {snapshot.has_nvidia_gpu ? "Detected" : "Not Present"}
              </span>
              <span className="text-xs text-neutral-400 mt-1 block">
                {snapshot.has_nvidia_gpu ? "CUDA Compatible" : "CPU Fallback Mode"}
              </span>
            </div>
          </div>
        ) : (
          <div className="mt-5 p-4 rounded-lg bg-neutral-950/40 border border-neutral-800/60 text-center text-sm text-neutral-500">
            No local hardware snapshot recorded yet. Click &quot;Inspect Local Hardware&quot; to inspect your host.
          </div>
        )}
      </div>

      {/* Safe Opt-in CPU Benchmark */}
      <div className="p-6 rounded-xl border border-neutral-800 bg-neutral-900/60">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="text-lg font-medium text-neutral-100">
              Safe Opt-In CPU Compute Benchmark
            </h3>
            <p className="text-sm text-neutral-400 mt-1">
              Deterministic matrix arithmetic benchmark with bounded runtime and explicit memory reclamation.
            </p>
          </div>
          <button
            type="button"
            onClick={handleBenchmark}
            disabled={isBenchmarking}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-500 rounded-lg transition-colors disabled:opacity-50"
          >
            {isBenchmarking ? "Running Benchmark..." : "Run Safe CPU Benchmark"}
          </button>
        </div>

        {/* Benchmark parameters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5 pt-4 border-t border-neutral-800 text-xs">
          <div>
            <label className="text-neutral-400 block mb-1">Matrix Dimension (Clamped 50..500)</label>
            <input
              type="number"
              value={matrixSize}
              onChange={(e) => setMatrixSize(Math.max(50, Math.min(500, parseInt(e.target.value) || 50)))}
              className="w-full px-3 py-1.5 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-purple-500"
            />
          </div>
          <div>
            <label className="text-neutral-400 block mb-1">Iterations (1..10)</label>
            <input
              type="number"
              value={iterations}
              onChange={(e) => setIterations(Math.max(1, Math.min(10, parseInt(e.target.value) || 1)))}
              className="w-full px-3 py-1.5 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-purple-500"
            />
          </div>
        </div>

        {benchmark && (
          <div className="mt-5 p-4 rounded-xl bg-purple-950/20 border border-purple-900/40">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wide">
                Latest Benchmark Result ({benchmark.status})
              </span>
              <span className="text-xs text-neutral-400 font-mono">
                {new Date(benchmark.completed_at).toLocaleTimeString()}
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 text-xs">
              <div>
                <span className="text-neutral-500 block">Duration</span>
                <span className="text-neutral-200 font-mono font-medium text-sm">
                  {benchmark.duration_ms.toFixed(1)} ms
                </span>
              </div>
              <div>
                <span className="text-neutral-500 block">Compute Throughput</span>
                <span className="text-purple-300 font-mono font-medium text-sm">
                  {(benchmark.operations_per_second / 1_000_000).toFixed(2)} MFLOPS
                </span>
              </div>
              <div>
                <span className="text-neutral-500 block">RAM Tracked</span>
                <span className="text-neutral-300 font-mono">
                  {benchmark.ram_before_mb} MB &rarr; {benchmark.ram_after_mb} MB
                </span>
              </div>
              <div>
                <span className="text-neutral-500 block">Evidence Tier</span>
                <span className="text-emerald-400 font-mono font-semibold">
                  {benchmark.evidence_type}
                </span>
              </div>
            </div>
            <p className="text-xs text-neutral-400 mt-3 pt-3 border-t border-purple-900/30">
              <span className="font-semibold text-neutral-300">Methodology: </span>
              {benchmark.limitations}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
