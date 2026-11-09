import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  Activity,
  ShieldCheck,
  RotateCcw,
  Sparkles,
  Send,
  BookOpen,
  History,
  AlertCircle,
  HardDrive,
  Cpu,
} from "lucide-react";
import {
  getApplicationSlots,
  getRuntimeHealth,
  runGoldenTests,
  activateSlot,
  rollbackSlot,
  listActivationEvents,
  executeChatCompletion,
  executeRagQuery,
} from "../api";
import type { RuntimeSlot, GoldenTestRun } from "../types";
import { SlotCard } from "../components/SlotCard";
import { GoldenTestResultsCard } from "../components/GoldenTestResultsCard";
import { SlotActivationModal } from "../components/SlotActivationModal";

export const RuntimeDashboardPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const appId = searchParams.get("app_id") || "default-app";
  const queryClient = useQueryClient();

  const [activeSlotToPromote, setActiveSlotToPromote] = useState<RuntimeSlot | null>(null);
  const [activeTestRun, setActiveTestRun] = useState<GoldenTestRun | null>(null);

  // Playground state
  const [chatPrompt, setChatPrompt] = useState("");
  const [chatResponse, setChatResponse] = useState<string | null>(null);
  const [isChatLoading, setIsChatLoading] = useState(false);

  const [ragQuery, setRagQuery] = useState("");
  const [ragResponse, setRagResponse] = useState<{ answer: string; citations: Array<{ snippet: string; score: number }> } | null>(null);
  const [isRagLoading, setIsRagLoading] = useState(false);

  // Health and slots queries
  const { data: health } = useQuery({
    queryKey: ["runtime-health", appId],
    queryFn: () => getRuntimeHealth(appId),
    refetchInterval: 10000,
  });

  const { data: slots = [], isLoading: isSlotsLoading } = useQuery({
    queryKey: ["runtime-slots", appId],
    queryFn: () => getApplicationSlots(appId),
  });

  const { data: activations = [] } = useQuery({
    queryKey: ["runtime-activations", appId],
    queryFn: () => listActivationEvents(appId),
  });

  // Mutations
  const goldenTestMutation = useMutation({
    mutationFn: (slotId: string) => runGoldenTests(slotId),
    onSuccess: (run) => {
      setActiveTestRun(run);
      queryClient.invalidateQueries({ queryKey: ["runtime-slots", appId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-health", appId] });
    },
  });

  const activateMutation = useMutation({
    mutationFn: (payload: { slot_name: RuntimeSlot["slot_name"]; reason: string }) =>
      activateSlot(appId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runtime-slots", appId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-health", appId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-activations", appId] });
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: (reason: string) => rollbackSlot(appId, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runtime-slots", appId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-health", appId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-activations", appId] });
    },
  });

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatPrompt.trim()) return;
    setIsChatLoading(true);
    setChatResponse(null);
    try {
      const res = await executeChatCompletion(
        {
          model: "local-model",
          messages: [{ role: "user", content: chatPrompt.trim() }],
        },
        appId
      );
      setChatResponse(res.choices[0]?.message.content || "Empty response.");
    } catch (err) {
      setChatResponse(`Error: ${err instanceof Error ? err.message : "Inference failed."}`);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleRagSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ragQuery.trim()) return;
    setIsRagLoading(true);
    setRagResponse(null);
    try {
      const res = await executeRagQuery({ query: ragQuery.trim() }, appId);
      setRagResponse(res);
    } catch (err) {
      setRagResponse({ answer: `Error: ${err instanceof Error ? err.message : "RAG query failed."}`, citations: [] });
    } finally {
      setIsRagLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto p-6">
      {/* Top Banner */}
      <div className="rounded-2xl border border-border bg-gradient-to-r from-card to-muted/40 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="w-4 h-4" /> Offline Execution Active
              </span>
              <span className="text-xs text-muted-foreground font-mono">
                Zero Outbound Telemetry
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
              <Activity className="w-7 h-7 text-primary" />
              Customer Runtime Console
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Local inferencing node operating on customer premises with Blue/Green deployment slots and acceptance gating.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="bg-card border border-border rounded-xl p-3 px-4 text-xs space-y-0.5">
              <div className="text-muted-foreground flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-primary" /> Runtime Engine
              </div>
              <div className="font-semibold text-foreground">{health?.engine || "MOCK_ENGINE"}</div>
            </div>

            <div className="bg-card border border-border rounded-xl p-3 px-4 text-xs space-y-0.5">
              <div className="text-muted-foreground flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-primary" /> Memory Usage
              </div>
              <div className="font-semibold text-foreground">
                {health?.memory_allocated_mb ? `${health.memory_allocated_mb} MB` : "—"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Blue / Green Slots Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-foreground">Blue / Green Runtime Slots</h2>
            <p className="text-xs text-muted-foreground">
              Live traffic serves from the active slot. Updates are staged, tested via Golden Tests, and promoted atomically.
            </p>
          </div>

          {slots.length >= 2 && (
            <button
              type="button"
              onClick={() => {
                const reason = prompt("Enter rollback reason for audit log:");
                if (reason) rollbackMutation.mutate(reason);
              }}
              disabled={rollbackMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-input bg-background hover:bg-muted text-foreground transition-colors disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Manual Rollback
            </button>
          )}
        </div>

        {isSlotsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 animate-pulse">
            <div className="h-64 rounded-xl border border-border bg-card" />
            <div className="h-64 rounded-xl border border-border bg-card" />
          </div>
        ) : slots.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-8 text-center bg-card">
            <AlertCircle className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm font-semibold text-foreground">No Runtime Slots Found</p>
            <p className="text-xs text-muted-foreground mt-1">
              Install an approved package from the Model Zoo or App Zoo to initialize deployment slots.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {slots.map((slot) => (
              <SlotCard
                key={slot.id}
                slot={slot}
                isActive={slot.status === "ACTIVE"}
                onRunGoldenTests={(slotId) => goldenTestMutation.mutate(slotId)}
                onActivate={(s) => setActiveSlotToPromote(s)}
                isLoading={goldenTestMutation.isPending || activateMutation.isPending}
              />
            ))}
          </div>
        )}
      </div>

      {/* Golden Test Acceptance Runner */}
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-foreground">Golden Acceptance Tests</h2>
        <GoldenTestResultsCard run={activeTestRun} isLoading={goldenTestMutation.isPending} />
      </div>

      {/* Offline Playground: Chat & RAG Testing */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chat Completions */}
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-border">
            <Sparkles className="w-5 h-5 text-primary" />
            <h3 className="text-base font-semibold text-foreground">Offline Chat Completion Test</h3>
          </div>

          <form onSubmit={handleChatSubmit} className="space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                Test Prompt (Evaluated completely offline)
              </label>
              <textarea
                rows={3}
                value={chatPrompt}
                onChange={(e) => setChatPrompt(e.target.value)}
                placeholder="Ask a question or try safety checks (e.g. 'How do I reset my password?')"
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isChatLoading || !chatPrompt.trim()}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                {isChatLoading ? "Evaluating..." : "Send Query"}
              </button>
            </div>
          </form>

          {chatResponse && (
            <div className="p-3.5 rounded-lg bg-muted/40 border border-border text-xs text-foreground font-mono whitespace-pre-wrap">
              {chatResponse}
            </div>
          )}
        </div>

        {/* Local Grounded RAG */}
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-border">
            <BookOpen className="w-5 h-5 text-primary" />
            <h3 className="text-base font-semibold text-foreground">Local Grounded RAG Query</h3>
          </div>

          <form onSubmit={handleRagSubmit} className="space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                Knowledge Base Query (Searches local vector store)
              </label>
              <textarea
                rows={3}
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder="Query internal knowledge documents (e.g. 'What are our remote work guidelines?')"
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isRagLoading || !ragQuery.trim()}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                {isRagLoading ? "Searching..." : "Execute Local RAG"}
              </button>
            </div>
          </form>

          {ragResponse && (
            <div className="space-y-3 p-3.5 rounded-lg bg-muted/40 border border-border text-xs">
              <p className="text-foreground">{ragResponse.answer}</p>
              {ragResponse.citations.length > 0 && (
                <div className="pt-2 border-t border-border/60 space-y-1.5">
                  <span className="font-semibold text-muted-foreground text-[10px] tracking-wider uppercase">
                    Grounded Citations
                  </span>
                  {ragResponse.citations.map((c, i) => (
                    <div key={i} className="p-2 rounded bg-background border border-border text-[11px] text-muted-foreground">
                      "{c.snippet}" (Score: {c.score})
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Activation & Rollback Audit History */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-border">
          <History className="w-5 h-5 text-primary" />
          <h3 className="text-base font-semibold text-foreground">Immutable Slot Activation History</h3>
        </div>

        {activations.length === 0 ? (
          <p className="text-xs text-muted-foreground py-2">No activation or rollback events recorded yet.</p>
        ) : (
          <div className="divide-y divide-border/60">
            {activations.map((ev) => (
              <div key={ev.id} className="py-2.5 flex items-center justify-between text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-foreground">
                      {ev.previous_slot_name} → {ev.new_slot_name}
                    </span>
                    <span className="font-mono text-muted-foreground">({ev.model_version_id})</span>
                  </div>
                  <p className="text-muted-foreground mt-0.5">{ev.switch_reason}</p>
                </div>
                <div className="text-right text-muted-foreground">
                  <div>{new Date(ev.created_at).toLocaleDateString()}</div>
                  <div className="text-[10px]">{new Date(ev.created_at).toLocaleTimeString()}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Promotion Confirmation Modal */}
      {activeSlotToPromote && (
        <SlotActivationModal
          slot={activeSlotToPromote}
          isOpen={!!activeSlotToPromote}
          onClose={() => setActiveSlotToPromote(null)}
          onConfirm={async (slot, reason) => {
            await activateMutation.mutateAsync({ slot_name: slot.slot_name, reason });
          }}
        />
      )}
    </div>
  );
};
