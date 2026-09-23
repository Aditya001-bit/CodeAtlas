import { useState } from "react";
import "./App.css";
import {
  LayoutDashboard,
  Network,
  ShieldAlert,
  MessageSquare,
  Upload,
  FolderGit2,
  Loader2,
} from "lucide-react";

import CodeMap from "./CodeMap";
import RiskView from "./RiskView";
import AskCodebase from "./AskCodebase";

function App() {
  const [activePage, setActivePage] = useState("Dashboard");

  const [stats, setStats] = useState({
    files: 0,
    nodes: 0,
    edges: 0,
    highRisk: 0,
  });

  const [repository, setRepository] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function analyzeRepository(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".zip")) {
      setError("Please upload a ZIP file.");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || "Analysis failed");
      }

      // --------------------------------------------------------
      // Get ML risk results for the newly analyzed repository
      // --------------------------------------------------------

      let highRiskCount = 0;

      try {
        const riskResponse = await fetch("/api/risk");
        const riskData = await riskResponse.json();

        if (Array.isArray(riskData)) {
          highRiskCount = riskData.filter(
            (item) => item.risk_level === "High"
          ).length;
        }
      } catch (riskError) {
        console.error(
          "Could not load risk predictions:",
          riskError
        );
      }

      // --------------------------------------------------------
      // Update dashboard statistics
      // --------------------------------------------------------

      setStats({
        files: data.files,
        nodes: data.nodes,
        edges: data.edges,
        highRisk: highRiskCount,
      });

      // This is the source of truth for the current
      // frontend session.
      setRepository(file.name);

      // Open Code Map after successful analysis.
      setActivePage("Code Map");

    } catch (err) {
      setError(
        err.message || "Analysis failed"
      );
    } finally {
      setUploading(false);
    }
  }

  const hasRepository = Boolean(repository);

  function openPage(page) {
    if (!hasRepository && page !== "Dashboard") {
      setActivePage("Dashboard");
      setError(
        "Analyze a repository before opening this view."
      );
      return;
    }

    setError("");
    setActivePage(page);
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex">

      {/* Sidebar */}
      <aside className="w-64 border-r border-white/10 bg-[#0d0d0f] p-5 flex flex-col">

        <div className="flex items-center gap-3 mb-10">

          <div className="w-9 h-9 rounded-lg bg-white text-black flex items-center justify-center font-bold">
            ◈
          </div>

          <div>
            <h1 className="font-semibold text-lg">
              CodeAtlas
            </h1>

            <p className="text-xs text-zinc-500">
              Code Intelligence
            </p>
          </div>

        </div>

        <div className="text-xs text-zinc-600 uppercase tracking-wider mb-3">
          Overview
        </div>

        <nav className="space-y-1">

          <NavItem
            icon={<LayoutDashboard size={18} />}
            label="Dashboard"
            active={activePage === "Dashboard"}
            onClick={() => openPage("Dashboard")}
          />

          <NavItem
            icon={<Network size={18} />}
            label="Code Map"
            active={activePage === "Code Map"}
            disabled={!hasRepository}
            onClick={() => openPage("Code Map")}
          />

          <NavItem
            icon={<ShieldAlert size={18} />}
            label="Risk View"
            active={activePage === "Risk View"}
            disabled={!hasRepository}
            onClick={() => openPage("Risk View")}
          />

          <NavItem
            icon={<MessageSquare size={18} />}
            label="Ask Codebase"
            active={activePage === "Ask Codebase"}
            disabled={!hasRepository}
            onClick={() => openPage("Ask Codebase")}
          />

        </nav>

        {/* Repository */}
        <div className="mt-auto">

          <div className="border border-white/10 rounded-xl p-4 bg-white/[0.02]">

            <div className="flex items-center gap-2 mb-2">

              <FolderGit2
                size={16}
                className="text-zinc-400"
              />

              <span className="text-sm">
                Repository
              </span>

            </div>

            <p className="text-sm text-zinc-400 truncate">
              {repository || "No repository loaded"}
            </p>

            {repository && (
              <p className="text-xs text-zinc-600 mt-1">
                {stats.files} files analyzed
              </p>
            )}

          </div>

        </div>

      </aside>

      {/* Main */}
      <main className="flex-1">

        {activePage === "Dashboard" && (
          <Dashboard
            stats={stats}
            uploading={uploading}
            error={error}
            onAnalyze={analyzeRepository}
            onCodeMap={() => openPage("Code Map")}
          />
        )}

        {activePage === "Code Map" && (
          <CodeMap repository={repository} />
        )}

        {activePage === "Risk View" && (
          <RiskView />
        )}

        {activePage === "Ask Codebase" && (
          <AskCodebase />
        )}

      </main>

    </div>
  );
}


function Dashboard({
  stats,
  uploading,
  error,
  onAnalyze,
  onCodeMap,
}) {
  return (
    <>
      <header className="h-16 border-b border-white/10 flex items-center justify-between px-8">

        <h2 className="font-medium">
          Dashboard
        </h2>

        <label className="cursor-pointer">

          <input
            type="file"
            accept=".zip"
            className="hidden"
            disabled={uploading}
            onChange={(e) => {
              onAnalyze(e.target.files[0]);
              e.target.value = "";
            }}
          />

          <span
            className={`flex items-center gap-2 bg-white text-black px-4 py-2 rounded-lg text-sm font-medium transition ${
              uploading
                ? "opacity-60 cursor-not-allowed"
                : "hover:bg-zinc-200"
            }`}
          >

            {uploading ? (
              <>
                <Loader2
                  size={16}
                  className="animate-spin"
                />

                Analyzing...
              </>
            ) : (
              <>
                <Upload size={16} />

                Analyze Repository
              </>
            )}

          </span>

        </label>

      </header>

      <section className="p-8 max-w-7xl mx-auto">

        <div className="mb-8">

          <h1 className="text-3xl font-semibold tracking-tight">
            Codebase Overview
          </h1>

          <p className="text-zinc-500 mt-2">
            Understand your Python codebase, dependencies and risks.
          </p>

        </div>

        {error && (
          <div className="mb-5 border border-red-500/20 bg-red-500/5 text-red-400 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-3 gap-4 mb-6">

          <StatCard
            label="Files"
            value={stats.files}
          />

          <StatCard
            label="Nodes"
            value={stats.nodes}
          />

          <StatCard
            label="High Risk"
            value={stats.highRisk}
          />

        </div>

        <div className="border border-white/10 rounded-2xl bg-[#0d0d0f] overflow-hidden">

          <div className="p-5 border-b border-white/10 flex items-center justify-between">

            <div>

              <h3 className="font-medium">
                Dependency Graph
              </h3>

              <p className="text-sm text-zinc-500 mt-1">
                Visualize relationships inside your codebase.
              </p>

            </div>

            <button
              onClick={onCodeMap}
              disabled={stats.files === 0}
              className={`text-sm ${
                stats.files === 0
                  ? "text-zinc-700 cursor-not-allowed"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              Open Code Map →
            </button>

          </div>

          <div className="h-[420px] flex items-center justify-center">

            {stats.files === 0 ? (
              <div className="text-center">

                <Network
                  size={40}
                  className="text-zinc-600 mx-auto mb-4"
                />

                <h3 className="text-zinc-300 font-medium">
                  No repository analyzed
                </h3>

                <p className="text-zinc-600 text-sm mt-2">
                  Upload a Python repository to generate the graph.
                </p>

              </div>
            ) : (
              <div className="text-center">

                <Network
                  size={40}
                  className="text-zinc-400 mx-auto mb-4"
                />

                <h3 className="text-zinc-300 font-medium">
                  Repository analyzed
                </h3>

                <p className="text-zinc-500 text-sm mt-2">
                  {stats.files} files · {stats.nodes} nodes ·{" "}
                  {stats.edges} relationships
                </p>

                <button
                  onClick={onCodeMap}
                  className="mt-5 px-4 py-2 rounded-lg bg-white text-black text-sm font-medium"
                >
                  Explore Code Map
                </button>

              </div>
            )}

          </div>

        </div>

      </section>
    </>
  );
}


function NavItem({
  icon,
  label,
  active,
  onClick,
  disabled = false,
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={
        disabled
          ? "Analyze a repository before opening this view"
          : undefined
      }
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition ${
        disabled
          ? "text-zinc-700 cursor-not-allowed"
          : active
          ? "bg-white/10 text-white"
          : "text-zinc-500 hover:bg-white/5 hover:text-zinc-200"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}


function StatCard({
  label,
  value,
}) {
  return (
    <div className="border border-white/10 rounded-xl bg-[#0d0d0f] p-5">

      <p className="text-sm text-zinc-500">
        {label}
      </p>

      <p className="text-2xl font-semibold mt-2">
        {value}
      </p>

    </div>
  );
}


export default App;