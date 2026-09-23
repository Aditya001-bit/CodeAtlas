import { useEffect, useState } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function RiskView() {
  const [risks, setRisks] = useState([]);
  const [loading, setLoading] = useState(true);

  // Gemini explanation state
  const [explanations, setExplanations] = useState({});
  const [explaining, setExplaining] = useState(null);
  const [expanded, setExpanded] = useState(null);

  // ---------------------------------------------------------
  // Load ML risk predictions
  // ---------------------------------------------------------

  useEffect(() => {
    async function loadRisks() {
      try {
        const response = await fetch("/api/risk");
        const data = await response.json();

        if (!data.error) {
          setRisks(data);
        }
      } catch (error) {
        console.error(
          "Failed to load risks:",
          error
        );
      } finally {
        setLoading(false);
      }
    }

    loadRisks();
  }, []);

  // ---------------------------------------------------------
  // Gemini explanation
  // ---------------------------------------------------------

  async function explainWithAI(nodeId) {
    setExplaining(nodeId);
    setExpanded(nodeId);

    try {
      const response = await fetch(
        `/api/risk/explain/${encodeURIComponent(nodeId)}`
      );

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error ||
            "Failed to generate explanation"
        );
      }

      setExplanations((prev) => ({
        ...prev,
        [nodeId]: data.explanation,
      }));
    } catch (error) {
      console.error(
        "Gemini explanation failed:",
        error
      );

      setExplanations((prev) => ({
        ...prev,
        [nodeId]:
          "AI explanation is currently unavailable. Please try again.",
      }));
    } finally {
      setExplaining(null);
    }
  }

  // ---------------------------------------------------------
  // Risk counts
  // ---------------------------------------------------------

  const high = risks.filter(
    (r) => r.risk_level === "High"
  ).length;

  const medium = risks.filter(
    (r) => r.risk_level === "Medium"
  ).length;

  const low = risks.filter(
    (r) => r.risk_level === "Low"
  ).length;

  // ---------------------------------------------------------
  // Loading
  // ---------------------------------------------------------

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center gap-3 text-zinc-400">
          <Loader2
            size={20}
            className="animate-spin"
          />
          Loading ML risk analysis...
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (
    <div className="p-8 max-w-7xl mx-auto">

      {/* Header */}
      <div className="mb-8">

        <div className="flex items-center gap-3 mb-2">

          <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">

            <ShieldAlert
              size={21}
              className="text-red-400"
            />

          </div>

          <h1 className="text-2xl font-semibold">
            Risk View
          </h1>

        </div>

        <p className="text-zinc-500 text-sm">
          ML-powered risk analysis of functions in your
          codebase.
        </p>

        <p className="text-zinc-600 text-xs mt-2">
          Random Forest predictions based on structural
          and graph features.
        </p>

      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">

        {/* High */}
        <div className="border border-red-500/20 bg-red-500/5 rounded-xl p-5">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-xs uppercase tracking-wider text-zinc-500">
                High Risk
              </p>

              <p className="text-3xl font-semibold text-red-400 mt-2">
                {high}
              </p>

            </div>

            <AlertTriangle
              size={22}
              className="text-red-400"
            />

          </div>

        </div>

        {/* Medium */}
        <div className="border border-yellow-500/20 bg-yellow-500/5 rounded-xl p-5">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-xs uppercase tracking-wider text-zinc-500">
                Medium Risk
              </p>

              <p className="text-3xl font-semibold text-yellow-400 mt-2">
                {medium}
              </p>

            </div>

            <AlertTriangle
              size={22}
              className="text-yellow-400"
            />

          </div>

        </div>

        {/* Low */}
        <div className="border border-emerald-500/20 bg-emerald-500/5 rounded-xl p-5">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-xs uppercase tracking-wider text-zinc-500">
                Low Risk
              </p>

              <p className="text-3xl font-semibold text-emerald-400 mt-2">
                {low}
              </p>

            </div>

            <CheckCircle2
              size={22}
              className="text-emerald-400"
            />

          </div>

        </div>

      </div>

      {/* Function list */}
      <div className="border border-white/10 rounded-2xl overflow-hidden bg-white/[0.02]">

        {/* Table Header */}
        <div className="grid grid-cols-[1.3fr_1.4fr_0.8fr_1.7fr_0.9fr_1fr] gap-4 px-5 py-4 border-b border-white/10 text-xs text-zinc-500 uppercase tracking-wider">

          <div>Function</div>
          <div>File</div>
          <div>Risk</div>
          <div>Signals</div>
          <div>Risk Index</div>
          <div>AI</div>

        </div>

        {/* Rows */}
        {risks.map((risk) => {

          const nodeId = risk.id;

          const isExplaining =
            explaining === nodeId;

          const isExpanded =
            expanded === nodeId;

          const explanation =
            explanations[nodeId];

          const riskScore = Number(
            risk.risk_score || 0
          );

          return (
            <div
              key={nodeId}
              className="border-b border-white/5 last:border-b-0"
            >

              {/* Main Row */}
              <div className="grid grid-cols-[1.3fr_1.4fr_0.8fr_1.7fr_0.9fr_1fr] gap-4 px-5 py-5 items-center hover:bg-white/[0.02] transition">

                {/* Function */}
                <div className="min-w-0">

                  <p className="text-sm font-medium text-white truncate">
                    {risk.function || "Module"}
                  </p>

                  <p className="text-xs text-zinc-600 truncate mt-1">
                    {nodeId}
                  </p>

                </div>

                {/* File */}
                <div className="text-sm text-zinc-400 truncate">
                  {risk.file}
                </div>

                {/* Risk */}
                <div>
                  <RiskBadge
                    level={risk.risk_level}
                  />
                </div>

                {/* Signals */}
                <div className="min-w-0">

                  {risk.reasons &&
                  risk.reasons.length > 0 ? (
                    <div className="space-y-1">

                      {risk.reasons
                        .slice(0, 2)
                        .map(
                          (
                            reason,
                            index
                          ) => (
                            <p
                              key={index}
                              className="text-xs text-zinc-400 truncate"
                            >
                              {reason}
                            </p>
                          )
                        )}

                    </div>
                  ) : (
                    <span className="text-xs text-zinc-600">
                      No strong signals
                    </span>
                  )}

                </div>

                {/* Risk Index */}
                <div className="text-sm">

                  <span
                    className={
                      risk.risk_level === "High"
                        ? "text-red-400 font-semibold"
                        : risk.risk_level ===
                          "Medium"
                        ? "text-yellow-400 font-semibold"
                        : "text-zinc-300"
                    }
                  >
                    {riskScore.toFixed(0)}
                  </span>

                  <span className="text-zinc-600">
                    {" "}
                    / 100
                  </span>

                </div>

                {/* AI Button */}
                <div>

                  <button
                    onClick={() =>
                      explanation
                        ? setExpanded(
                            isExpanded
                              ? null
                              : nodeId
                          )
                        : explainWithAI(
                            nodeId
                          )
                    }
                    disabled={isExplaining}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-purple-500/20 bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 hover:border-purple-500/30 transition text-xs disabled:opacity-50"
                  >

                    {isExplaining ? (
                      <>
                        <Loader2
                          size={14}
                          className="animate-spin"
                        />
                        Thinking...
                      </>
                    ) : explanation ? (
                      <>
                        {isExpanded ? (
                          <ChevronUp
                            size={14}
                          />
                        ) : (
                          <ChevronDown
                            size={14}
                          />
                        )}

                        AI Explanation
                      </>
                    ) : (
                      <>
                        <Sparkles
                          size={14}
                        />
                        Explain with AI
                      </>
                    )}

                  </button>

                </div>

              </div>

              {/* Gemini Explanation */}
              {isExpanded &&
                explanation && (
                  <div className="px-5 pb-5">

                    <div className="ml-0 rounded-xl border border-purple-500/20 bg-purple-500/5 p-5">

                      <div className="flex items-center gap-2 mb-3">

                        <Sparkles
                          size={17}
                          className="text-purple-400"
                        />

                        <span className="text-sm font-medium text-purple-300">
                          Gemini Analysis
                        </span>

                      </div>

                      <p className="text-sm leading-6 text-zinc-300">
                        {explanation}
                      </p>

                    </div>

                  </div>
                )}

            </div>
          );
        })}

        {/* Empty state */}
        {risks.length === 0 && (
          <div className="p-12 text-center">

            <ShieldAlert
              size={32}
              className="mx-auto text-zinc-700 mb-3"
            />

            <p className="text-zinc-500">
              No risk predictions available.
            </p>

            <p className="text-xs text-zinc-600 mt-1">
              Analyze a repository first.
            </p>

          </div>
        )}

      </div>

      {/* Footer */}
      {risks.length > 0 && (
        <div className="mt-4 flex items-center justify-between">

          <p className="text-xs text-zinc-600">
            {risks.length} functions analyzed by
            Random Forest.
          </p>

          <p className="text-xs text-zinc-600 flex items-center gap-1">
            <Sparkles size={12} />
            Gemini provides explanations, not risk predictions.
          </p>

        </div>
      )}

    </div>
  );
}


// ============================================================
// RISK BADGE
// ============================================================

function RiskBadge({ level }) {

  const normalized =
    String(level || "Low").toLowerCase();

  if (normalized === "high") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">

        <span className="w-1.5 h-1.5 rounded-full bg-red-400" />

        High

      </span>
    );
  }

  if (normalized === "medium") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">

        <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />

        Medium

      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">

      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />

      Low

    </span>
  );
}