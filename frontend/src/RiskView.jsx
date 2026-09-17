import { useEffect, useState } from "react";
import { ShieldAlert, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function RiskView() {
  const [risks, setRisks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRisks() {
      try {
        const response = await fetch("/api/risk");
        const data = await response.json();

        if (!data.error) {
          setRisks(data);
        }
      } catch (error) {
        console.error("Failed to load risks:", error);
      } finally {
        setLoading(false);
      }
    }

    loadRisks();
  }, []);

  const high = risks.filter((r) => r.level === "HIGH").length;
  const medium = risks.filter((r) => r.level === "MEDIUM").length;
  const low = risks.filter((r) => r.level === "LOW").length;

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <p className="text-zinc-500">Loading risk analysis...</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
            <ShieldAlert size={20} className="text-zinc-300" />
          </div>

          <div>
            <h1 className="text-2xl font-semibold">
              Risk View
            </h1>

            <p className="text-sm text-zinc-500 mt-1">
              Identify functions that may require attention.
            </p>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4 mb-8">

        <RiskSummary
          label="High Risk"
          value={high}
          icon={<AlertTriangle size={18} />}
        />

        <RiskSummary
          label="Medium Risk"
          value={medium}
          icon={<AlertTriangle size={18} />}
        />

        <RiskSummary
          label="Low Risk"
          value={low}
          icon={<CheckCircle2 size={18} />}
        />

      </div>

      {/* Risk table */}
      <div className="border border-white/10 rounded-2xl bg-[#0d0d0f] overflow-hidden">

        <div className="p-5 border-b border-white/10">
          <h2 className="font-medium">
            Function Risk Analysis
          </h2>

          <p className="text-sm text-zinc-500 mt-1">
            Structural risk scores for analyzed functions.
          </p>
        </div>

        {risks.length === 0 ? (

          <div className="p-12 text-center text-zinc-500">
            No risk data available.
          </div>

        ) : (

          <div className="divide-y divide-white/5">

            {risks.map((risk) => (

              <div
                key={risk.node_id}
                className="p-5 flex items-center justify-between hover:bg-white/[0.02] transition"
              >

                <div className="flex items-center gap-4">

                  <div className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center">
                    <ShieldAlert
                      size={17}
                      className="text-zinc-400"
                    />
                  </div>

                  <div>
                    <p className="text-sm font-medium text-zinc-200">
                      {risk.node_id}
                    </p>

                    <div className="flex gap-2 mt-2 flex-wrap">
                      {risk.reasons.map((reason) => (
                        <span
                          key={reason}
                          className="text-xs text-zinc-500 bg-white/5 px-2 py-1 rounded"
                        >
                          {reason}
                        </span>
                      ))}
                    </div>
                  </div>

                </div>


                <div className="flex items-center gap-6">

                  <div className="text-right">
                    <p className="text-xs text-zinc-600">
                      Score
                    </p>

                    <p className="text-lg font-semibold">
                      {risk.score}
                    </p>
                  </div>

                  <RiskBadge level={risk.level} />

                </div>

              </div>

            ))}

          </div>

        )}

      </div>

    </div>
  );
}


function RiskSummary({ label, value, icon }) {
  return (
    <div className="border border-white/10 rounded-xl bg-[#0d0d0f] p-5">

      <div className="flex items-center justify-between">

        <p className="text-sm text-zinc-500">
          {label}
        </p>

        <span className="text-zinc-500">
          {icon}
        </span>

      </div>

      <p className="text-2xl font-semibold mt-3">
        {value}
      </p>

    </div>
  );
}


function RiskBadge({ level }) {
  const styles = {
    HIGH: "bg-red-500/10 text-red-400 border-red-500/20",
    MEDIUM: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    LOW: "bg-green-500/10 text-green-400 border-green-500/20",
  };

  return (
    <span
      className={`px-3 py-1.5 rounded-lg border text-xs font-medium ${
        styles[level] || styles.LOW
      }`}
    >
      {level}
    </span>
  );
}