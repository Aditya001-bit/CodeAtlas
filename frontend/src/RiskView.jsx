import { useEffect, useMemo, useState } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Loader2,
  ChevronDown,
  ChevronUp,
  Search,
  BrainCircuit,
  Activity,
} from "lucide-react";

export default function RiskView() {
  const [risks, setRisks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("All");

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
        setLoading(true);
        setError(null);

        const response = await fetch("/api/risk");

        if (!response.ok) {
          throw new Error(
            `Risk API returned ${response.status}`
          );
        }

        const data = await response.json();

        if (!Array.isArray(data)) {
          throw new Error(
            data?.error || "Invalid risk response"
          );
        }

        setRisks(data);
      } catch (err) {
        console.error("Failed to load risks:", err);
        setError(
          err.message ||
            "Unable to load ML risk analysis."
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
    } catch (err) {
      console.error(
        "Gemini explanation failed:",
        err
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
  // Overall statistics
  // ---------------------------------------------------------

  const averageRisk = useMemo(() => {
    if (!risks.length) return 0;

    const total = risks.reduce(
      (sum, risk) =>
        sum + Number(risk.risk_probability || 0),
      0
    );

    return total / risks.length;
  }, [risks]);

  const maxRisk = useMemo(() => {
    if (!risks.length) return 0;

    return Math.max(
      ...risks.map((risk) =>
        Number(risk.risk_probability || 0)
      )
    );
  }, [risks]);

  // ---------------------------------------------------------
  // Search + filtering + sorting
  // ---------------------------------------------------------

  const filteredRisks = useMemo(() => {
    const query = search.trim().toLowerCase();

    const filtered = risks.filter((risk) => {
      const matchesSearch =
        !query ||
        String(risk.function || "")
          .toLowerCase()
          .includes(query) ||
        String(risk.file || "")
          .toLowerCase()
          .includes(query) ||
        String(risk.id || "")
          .toLowerCase()
          .includes(query);

      const matchesFilter =
        riskFilter === "All" ||
        risk.risk_level === riskFilter;

      return matchesSearch && matchesFilter;
    });

    const order = {
      High: 3,
      Medium: 2,
      Low: 1,
    };

    return [...filtered].sort((a, b) => {
      const levelDifference =
        (order[b.risk_level] || 0) -
        (order[a.risk_level] || 0);

      if (levelDifference !== 0) {
        return levelDifference;
      }

      return (
        Number(b.risk_probability || 0) -
        Number(a.risk_probability || 0)
      );
    });
  }, [risks, search, riskFilter]);

  // ---------------------------------------------------------
  // Loading
  // ---------------------------------------------------------

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="min-h-[400px] flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-2xl border border-purple-500/20 bg-purple-500/10 flex items-center justify-center">
              <Loader2
                size={24}
                className="text-purple-400 animate-spin"
              />
            </div>

            <div className="text-center">
              <p className="text-sm font-medium text-white">
                Running ML risk analysis
              </p>

              <p className="text-xs text-zinc-600 mt-1">
                Analyzing structural and graph features...
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------
  // Error
  // ---------------------------------------------------------

  if (error) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="border border-red-500/20 bg-red-500/5 rounded-2xl p-8 text-center">
          <ShieldAlert
            size={32}
            className="mx-auto text-red-400 mb-4"
          />

          <h2 className="text-lg font-semibold text-white">
            Risk analysis unavailable
          </h2>

          <p className="text-sm text-zinc-500 mt-2">
            {error}
          </p>

          <p className="text-xs text-zinc-700 mt-3">
            Make sure the CodeAtlas backend is running.
          </p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (
    <div className="p-8 max-w-7xl mx-auto">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="mb-8">

        <div className="flex items-center gap-3 mb-3">

          <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <ShieldAlert
              size={21}
              className="text-red-400"
            />
          </div>

          <div>
            <h1 className="text-2xl font-semibold text-white">
              Risk View
            </h1>

            <p className="text-xs text-zinc-600 mt-1">
              CodeAtlas ML Risk Predictor
            </p>
          </div>

        </div>

        <p className="text-sm text-zinc-500 max-w-2xl">
          Machine-learning risk predictions for functions
          based on structural and graph-level code features.
        </p>

        <div className="flex items-center gap-2 mt-3">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-purple-500/20 bg-purple-500/5 text-purple-300 text-xs">
            <BrainCircuit size={13} />
            Logistic Regression
          </span>

          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-blue-500/20 bg-blue-500/5 text-blue-300 text-xs">
            <Activity size={13} />
            Isotonic Calibration
          </span>

          <span className="text-xs text-zinc-700">
            {risks.length} functions analyzed
          </span>
        </div>

      </div>

      {/* =====================================================
          SUMMARY CARDS
      ===================================================== */}

      <div className="grid grid-cols-3 gap-4 mb-5">

        {/* High */}
        <SummaryCard
          label="High Risk"
          value={high}
          subtitle={
            risks.length
              ? `${((high / risks.length) * 100).toFixed(1)}% of functions`
              : "0%"
          }
          icon={
            <AlertTriangle
              size={22}
              className="text-red-400"
            />
          }
          valueClass="text-red-400"
          cardClass="border-red-500/20 bg-red-500/5"
        />

        {/* Medium */}
        <SummaryCard
          label="Medium Risk"
          value={medium}
          subtitle={
            risks.length
              ? `${((medium / risks.length) * 100).toFixed(1)}% of functions`
              : "0%"
          }
          icon={
            <AlertTriangle
              size={22}
              className="text-yellow-400"
            />
          }
          valueClass="text-yellow-400"
          cardClass="border-yellow-500/20 bg-yellow-500/5"
        />

        {/* Low */}
        <SummaryCard
          label="Low Risk"
          value={low}
          subtitle={
            risks.length
              ? `${((low / risks.length) * 100).toFixed(1)}% of functions`
              : "0%"
          }
          icon={
            <CheckCircle2
              size={22}
              className="text-emerald-400"
            />
          }
          valueClass="text-emerald-400"
          cardClass="border-emerald-500/20 bg-emerald-500/5"
        />

      </div>

      {/* =====================================================
          MODEL STATISTICS
      ===================================================== */}

      <div className="grid grid-cols-3 gap-4 mb-8">

        <StatCard
          label="Functions Analyzed"
          value={risks.length}
          description="Static analysis coverage"
        />

        <StatCard
          label="Average Risk"
          value={`${(averageRisk * 100).toFixed(2)}%`}
          description="Mean calibrated probability"
        />

        <StatCard
          label="Highest Risk"
          value={`${(maxRisk * 100).toFixed(2)}%`}
          description="Maximum predicted probability"
        />

      </div>

      {/* =====================================================
          FILTER BAR
      ===================================================== */}

      <div className="flex items-center justify-between gap-4 mb-4">

        {/* Search */}
        <div className="relative flex-1 max-w-xl">

          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600"
          />

          <input
            type="text"
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
            placeholder="Search function, file or symbol..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-white/10 bg-white/[0.03] text-sm text-white placeholder:text-zinc-700 outline-none focus:border-purple-500/30 focus:bg-white/[0.04] transition"
          />

        </div>

        {/* Risk filters */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl border border-white/10 bg-white/[0.02]">

          {["All", "High", "Medium", "Low"].map(
            (filter) => (
              <button
                key={filter}
                onClick={() =>
                  setRiskFilter(filter)
                }
                className={`px-3 py-1.5 rounded-lg text-xs transition ${
                  riskFilter === filter
                    ? "bg-white/10 text-white"
                    : "text-zinc-600 hover:text-zinc-300"
                }`}
              >
                {filter}
              </button>
            )
          )}

        </div>

      </div>

      {/* Result count */}
      <div className="flex items-center justify-between mb-3">

        <p className="text-xs text-zinc-600">
          Showing{" "}
          <span className="text-zinc-400">
            {filteredRisks.length}
          </span>{" "}
          of{" "}
          <span className="text-zinc-400">
            {risks.length}
          </span>{" "}
          functions
        </p>

        <p className="text-xs text-zinc-700">
          Sorted by risk severity
        </p>

      </div>

      {/* =====================================================
          FUNCTION TABLE
      ===================================================== */}

      <div className="border border-white/10 rounded-2xl overflow-hidden bg-white/[0.02]">

        {/* Table Header */}
        <div className="grid grid-cols-[1.3fr_1.4fr_0.8fr_1.7fr_0.9fr_1fr] gap-4 px-5 py-4 border-b border-white/10 bg-white/[0.015] text-xs text-zinc-600 uppercase tracking-wider">

          <div>Function</div>
          <div>File</div>
          <div>Risk</div>
          <div>ML Signals</div>
          <div>Probability</div>
          <div>AI</div>

        </div>

        {/* Rows */}
        {filteredRisks.map((risk) => {

          const nodeId = risk.id;

          const isExplaining =
            explaining === nodeId;

          const isExpanded =
            expanded === nodeId;

          const explanation =
            explanations[nodeId];

          const probability = Number(
            risk.risk_probability || 0
          );

          const riskIndex = Number(
            risk.risk_index ??
              risk.risk_score ??
              probability * 100
          );

          return (
            <div
              key={nodeId}
              className="border-b border-white/5 last:border-b-0"
            >

              {/* =================================================
                  MAIN ROW
              ================================================= */}

              <div className="grid grid-cols-[1.3fr_1.4fr_0.8fr_1.7fr_0.9fr_1fr] gap-4 px-5 py-5 items-center hover:bg-white/[0.02] transition">

                {/* Function */}
                <div className="min-w-0">

                  <p className="text-sm font-medium text-white truncate">
                    {risk.function || "Module"}
                  </p>

                  <p className="text-xs text-zinc-700 truncate mt-1">
                    {nodeId}
                  </p>

                </div>

                {/* File */}
                <div
                  className="text-sm text-zinc-400 truncate"
                  title={risk.file}
                >
                  {risk.file}
                </div>

                {/* Risk */}
                <div>
                  <RiskBadge
                    level={risk.risk_level}
                  />
                </div>

                {/* ML Signals */}
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
                              title={reason}
                            >
                              {reason}
                            </p>
                          )
                        )}

                    </div>
                  ) : (
                    <span className="text-xs text-zinc-700">
                      No strong signals
                    </span>
                  )}

                </div>

                {/* Probability */}
                <div className="min-w-0">

                  <div className="flex items-center justify-between mb-1">

                    <span
                      className={`text-sm font-semibold ${
                        risk.risk_level === "High"
                          ? "text-red-400"
                          : risk.risk_level ===
                            "Medium"
                          ? "text-yellow-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {(probability * 100).toFixed(1)}%
                    </span>

                  </div>

                  <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">

                    <div
                      className={`h-full rounded-full ${
                        risk.risk_level === "High"
                          ? "bg-red-400"
                          : risk.risk_level ===
                            "Medium"
                          ? "bg-yellow-400"
                          : "bg-emerald-400"
                      }`}
                      style={{
                        width: `${Math.min(
                          probability * 100,
                          100
                        )}%`,
                      }}
                    />

                  </div>

                  <p className="text-[10px] text-zinc-700 mt-1">
                    Index {riskIndex.toFixed(1)}/100
                  </p>

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
                        Explain
                      </>
                    )}

                  </button>

                </div>

              </div>

              {/* =================================================
                  GEMINI EXPLANATION
              ================================================= */}

              {isExpanded &&
                explanation && (
                  <div className="px-5 pb-5">

                    <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-5">

                      <div className="flex items-center justify-between mb-4">

                        <div className="flex items-center gap-2">

                          <Sparkles
                            size={17}
                            className="text-purple-400"
                          />

                          <span className="text-sm font-medium text-purple-300">
                            Gemini Analysis
                          </span>

                        </div>

                        <span className="text-[10px] text-purple-400/60 uppercase tracking-wider">
                          Explanation only
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

        {/* =====================================================
            EMPTY SEARCH STATE
        ===================================================== */}

        {filteredRisks.length === 0 &&
          risks.length > 0 && (
            <div className="p-12 text-center">

              <Search
                size={30}
                className="mx-auto text-zinc-700 mb-3"
              />

              <p className="text-zinc-500">
                No functions match your search.
              </p>

              <button
                onClick={() => {
                  setSearch("");
                  setRiskFilter("All");
                }}
                className="text-xs text-purple-400 hover:text-purple-300 mt-2"
              >
                Clear filters
              </button>

            </div>
          )}

        {/* =====================================================
            EMPTY STATE
        ===================================================== */}

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

      {/* =====================================================
          FOOTER
      ===================================================== */}

      {risks.length > 0 && (
        <div className="mt-4 flex items-center justify-between">

          <p className="text-xs text-zinc-600">
            {risks.length} functions analyzed using the
            CodeAtlas calibrated ML risk model.
          </p>

          <p className="text-xs text-zinc-600 flex items-center gap-1">
            <Sparkles size={12} />
            Gemini explains predictions; it does not determine risk.
          </p>

        </div>
      )}

    </div>
  );
}


// ============================================================
// SUMMARY CARD
// ============================================================

function SummaryCard({
  label,
  value,
  subtitle,
  icon,
  valueClass,
  cardClass,
}) {
  return (
    <div
      className={`border rounded-xl p-5 ${cardClass}`}
    >
      <div className="flex items-start justify-between">

        <div>
          <p className="text-xs uppercase tracking-wider text-zinc-500">
            {label}
          </p>

          <p
            className={`text-3xl font-semibold mt-2 ${valueClass}`}
          >
            {value}
          </p>

          <p className="text-xs text-zinc-700 mt-1">
            {subtitle}
          </p>
        </div>

        {icon}

      </div>
    </div>
  );
}


// ============================================================
// STAT CARD
// ============================================================

function StatCard({
  label,
  value,
  description,
}) {
  return (
    <div className="border border-white/10 bg-white/[0.02] rounded-xl p-4">

      <p className="text-xs uppercase tracking-wider text-zinc-600">
        {label}
      </p>

      <p className="text-xl font-semibold text-white mt-2">
        {value}
      </p>

      <p className="text-xs text-zinc-700 mt-1">
        {description}
      </p>

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