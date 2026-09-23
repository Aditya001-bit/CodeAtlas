import { useCallback, useEffect, useMemo, useState } from "react";
import dagre from "@dagrejs/dagre";

import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

import {
  Search,
  X,
  Code2,
  ShieldAlert,
  Sparkles,
  Loader2,
  FolderTree,
  FileCode2,
  ArrowLeft,
  Network,
} from "lucide-react";


const NODE_WIDTH = 190;
const NODE_HEIGHT = 72;


// ============================================================
// CUSTOM GRAPH NODE
// ============================================================

function CustomNode({ data }) {

  const isFile =
    data.type === "file";

  const isClass =
    data.type === "class";

  return (
    <div
      className={`min-w-[190px] rounded-xl border px-4 py-3 shadow-xl ${
        isFile
          ? "border-white/20 bg-[#18181b]"
          : isClass
          ? "border-blue-500/20 bg-[#12151a]"
          : "border-white/10 bg-[#111113]"
      }`}
    >

      <Handle
        type="target"
        position={Position.Left}
      />

      <div className="flex items-center gap-2">

        {isFile ? (
          <FileCode2
            size={15}
            className="text-zinc-400"
          />
        ) : isClass ? (
          <Code2
            size={15}
            className="text-blue-400"
          />
        ) : (
          <Code2
            size={15}
            className="text-zinc-400"
          />
        )}

        <span className="text-sm font-medium text-zinc-200 truncate">
          {data.label}
        </span>

      </div>

      <p className="text-[11px] text-zinc-600 mt-1">
        {isFile
          ? "Python file"
          : isClass
          ? "Class"
          : "Function"}
      </p>

      <Handle
        type="source"
        position={Position.Right}
      />

    </div>
  );
}


const nodeTypes = {
  custom: CustomNode,
};


// ============================================================
// DAGRE GRAPH LAYOUT
// ============================================================

function getLayoutedElements(
  nodes,
  edges
) {

  if (!nodes.length) {
    return {
      nodes: [],
      edges,
    };
  }

  const graph =
    new dagre.graphlib.Graph();

  graph.setDefaultEdgeLabel(
    () => ({})
  );

  graph.setGraph({
    rankdir: "LR",
    nodesep: 70,
    ranksep: 130,
    marginx: 30,
    marginy: 30,
  });

  nodes.forEach((node) => {

    graph.setNode(
      node.id,
      {
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
      }
    );

  });

  edges.forEach((edge) => {

    if (
      graph.hasNode(edge.source) &&
      graph.hasNode(edge.target)
    ) {

      graph.setEdge(
        edge.source,
        edge.target
      );

    }

  });

  dagre.layout(graph);

  return {

    nodes: nodes.map((node) => {

      const position =
        graph.node(node.id);

      return {
        ...node,

        position: position
          ? {
              x:
                position.x -
                NODE_WIDTH / 2,

              y:
                position.y -
                NODE_HEIGHT / 2,
            }
          : {
              x: 0,
              y: 0,
            },
      };

    }),

    edges,
  };
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


// ============================================================
// RISK COLOR
// ============================================================

function getRiskColor(level) {

  const normalized =
    String(level || "Low").toLowerCase();

  if (normalized === "high") {
    return "text-red-400";
  }

  if (normalized === "medium") {
    return "text-yellow-400";
  }

  return "text-emerald-400";
}


function getFileStats(selectedNode) {

  const localNodes =
    selectedNode?.local_graph?.nodes || [];

  const localEdges =
    selectedNode?.local_graph?.edges || [];

  const functions =
    localNodes.filter(
      (node) => node.type === "function"
    ).length;

  const classes =
    localNodes.filter(
      (node) => node.type === "class"
    ).length;

  const imports =
    localEdges.filter(
      (edge) =>
        String(
          edge.relation || edge.type || ""
        ).toUpperCase() === "IMPORTS"
    ).length;

  const calls =
    localEdges.filter(
      (edge) =>
        String(
          edge.relation || edge.type || ""
        ).toUpperCase() === "CALLS"
    ).length;

  const contains =
    localEdges.filter(
      (edge) =>
        String(
          edge.relation || edge.type || ""
        ).toUpperCase() === "CONTAINS"
    ).length;

  return {
    functions,
    classes,
    symbols: functions + classes,
    imports,
    calls,
    contains,
  };
}


// ============================================================
// MAIN CODE MAP
// ============================================================

export default function CodeMap({
  repository,
}) {

  const [view, setView] =
    useState("files");

  const [currentFile, setCurrentFile] =
    useState(null);

  const [files, setFiles] =
    useState([]);

  const [nodes, setNodes] =
    useState([]);

  const [edges, setEdges] =
    useState([]);

  const [selectedNode, setSelectedNode] =
    useState(null);

  const [risks, setRisks] =
    useState([]);

  const [search, setSearch] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [graphLoading, setGraphLoading] =
    useState(false);

  const [riskLoading, setRiskLoading] =
    useState(false);

  const [aiExplanation, setAiExplanation] =
    useState(null);

  const [explaining, setExplaining] =
    useState(false);

  const [error, setError] =
    useState(null);


  // ============================================================
  // LOAD FILE-LEVEL OVERVIEW
  // ============================================================

  useEffect(() => {

    if (!repository) {

      setFiles([]);
      setNodes([]);
      setEdges([]);
      setSelectedNode(null);
      setCurrentFile(null);
      setView("files");
      setLoading(false);

      return;
    }


    async function loadFiles() {

      try {

        setLoading(true);
        setError(null);

        const response =
          await fetch(
            "/api/graph/files"
          );

        const data =
          await response.json();

        if (
          !response.ok ||
          data.error
        ) {

          throw new Error(
            data.error ||
            "Failed to load files"
          );

        }

        setFiles(
          data.files || []
        );

      } catch (err) {

        console.error(err);

        setError(
          err.message ||
          "Failed to load codebase"
        );

      } finally {

        setLoading(false);

      }

    }


    loadFiles();

  }, [repository]);


  // ============================================================
  // LOAD RISK DATA
  // ============================================================

  useEffect(() => {

    async function loadRisks() {

      setRiskLoading(true);

      try {

        const response =
          await fetch(
            "/api/risk"
          );

        const data =
          await response.json();

        if (!data.error) {

          setRisks(
            Array.isArray(data)
              ? data
              : []
          );

        }

      } catch (err) {

        console.error(
          "Could not load risk predictions:",
          err
        );

      } finally {

        setRiskLoading(false);

      }

    }


    loadRisks();

  }, []);


  // ============================================================
  // BUILD REACT FLOW GRAPH
  // ============================================================

  function buildGraph(
    rawNodes = [],
    rawEdges = []
  ) {

    const formattedNodes =
      rawNodes.map((node) => ({

        id: node.id,

        type: "custom",

        data: {

          label:
            node.type === "file"
              ? node.name ||
                node.file ||
                node.id

              : node.type === "function"
              ? `${node.name}()`

              : node.name ||
                node.id,

          type: node.type,

        },

        position: {
          x: 0,
          y: 0,
        },

      }));


    const formattedEdges =
      rawEdges

        .map(
          (edge, index) => ({

            id:
              `edge-${index}-${edge.source}-${edge.target}`,

            source:
              edge.source,

            target:
              edge.target,

            label:
              edge.relation ||
              edge.type,

            type:
              "smoothstep",

          })
        )

        .filter(
          (edge) =>
            formattedNodes.some(
              (node) =>
                node.id ===
                edge.source
            ) &&
            formattedNodes.some(
              (node) =>
                node.id ===
                edge.target
            )
        );


    return getLayoutedElements(
      formattedNodes,
      formattedEdges
    );
  }


  // ============================================================
  // OPEN FILE
  // ============================================================

  const openFile =
    useCallback(
      async (file) => {

        try {

          setGraphLoading(true);
          setError(null);
          setSelectedNode(null);
          setAiExplanation(null);
          setCurrentFile(file);
          setSearch("");
          setView("file");


          const response =
            await fetch(
              `/api/graph/file/${encodeURIComponent(
                file.id
              )}`
            );

          const data =
            await response.json();


          if (
            !response.ok ||
            data.error
          ) {

            throw new Error(
              data.error ||
              "Failed to load file graph"
            );

          }


          const graph =
            buildGraph(
              data.nodes || [],
              data.edges || []
            );


          setNodes(
            graph.nodes
          );

          setEdges(
            graph.edges
          );

        } catch (err) {

          console.error(err);

          setError(
            err.message ||
            "Failed to load file"
          );

        } finally {

          setGraphLoading(false);

        }

      },
      []
    );


  // ============================================================
  // OPEN SELECTED FUNCTION / CLASS
  // ============================================================

  const openNode =
    useCallback(
      async (nodeId) => {

        try {

          setGraphLoading(true);
          setAiExplanation(null);


          const response =
            await fetch(
              `/api/graph/node/${encodeURIComponent(
                nodeId
              )}`
            );


          const data =
            await response.json();


          if (
            !response.ok ||
            data.error
          ) {

            throw new Error(
              data.error ||
              "Failed to load node"
            );

          }


          const risk =
            risks.find(
              (item) =>
                item.id === nodeId
            ) ||
            risks.find(
              (item) =>
                item.file ===
                  data.file &&
                item.function ===
                  data.name
            ) ||
            null;


          setSelectedNode({

            ...data,

            risk,

          });


          // ----------------------------------------------------
          // Local graph
          // ----------------------------------------------------

          if (
            data.local_graph
          ) {

            const graph =
              buildGraph(
                data.local_graph.nodes ||
                  [],
                data.local_graph.edges ||
                  []
              );


            setNodes(
              graph.nodes
            );

            setEdges(
              graph.edges
            );

          }


          setView("node");

        } catch (err) {

          console.error(
            "Could not load node details:",
            err
          );

          setError(
            err.message ||
            "Failed to load node"
          );

        } finally {

          setGraphLoading(false);

        }

      },

      [risks]
    );


  // ============================================================
  // REACT FLOW CLICK
  // ============================================================

  const onNodeClick =
    useCallback(
      (_, node) => {

        openNode(
          node.id
        );

      },
      [openNode]
    );


  // ============================================================
  // GO BACK
  // ============================================================

  async function goBack() {

    if (
      view === "node" &&
      currentFile
    ) {

      await openFile(
        currentFile
      );

      return;
    }


    setSelectedNode(null);
    setCurrentFile(null);
    setView("files");
    setNodes([]);
    setEdges([]);
    setSearch("");

  }


  // ============================================================
  // GEMINI EXPLANATION
  // ============================================================

  async function explainWithAI() {

    if (
      !selectedNode?.id
    ) {

      return;
    }


    setExplaining(true);
    setAiExplanation(null);


    try {

      const response =
        await fetch(
          `/api/risk/explain/${encodeURIComponent(
            selectedNode.id
          )}`
        );


      const data =
        await response.json();


      if (
        !response.ok ||
        data.error
      ) {

        throw new Error(
          data.error ||
          "Failed to generate explanation"
        );

      }


      setAiExplanation(
        data.explanation
      );

    } catch (err) {

      console.error(
        "Gemini explanation failed:",
        err
      );

      setAiExplanation(
        "AI explanation is currently unavailable. Please try again."
      );

    } finally {

      setExplaining(false);

    }

  }


  // ============================================================
  // SEARCH FILES / SYMBOLS
  // ============================================================

  const filteredFiles =
    useMemo(() => {

      const q =
        search
          .trim()
          .toLowerCase();

      if (!q) {
        return files;
      }


      return files.filter(
        (file) =>
          String(
            file.name || ""
          )
            .toLowerCase()
            .includes(q) ||

          String(
            file.file || ""
          )
            .toLowerCase()
            .includes(q) ||

          String(
            file.id || ""
          )
            .toLowerCase()
            .includes(q)
      );

    }, [
      files,
      search,
    ]);


  const visibleNodes =
    useMemo(() => {

      const q =
        search
          .trim()
          .toLowerCase();

      if (
        !q ||
        view !== "file"
      ) {

        return nodes;

      }


      return nodes.filter(
        (node) =>
          String(
            node.data?.label ||
            ""
          )
            .toLowerCase()
            .includes(q)
      );

    }, [
      nodes,
      search,
      view,
    ]);


  // ============================================================
  // NO REPOSITORY
  // ============================================================

  if (!repository) {

    return (

      <div className="h-[calc(100vh-64px)] flex items-center justify-center">

        <div className="text-center max-w-md px-6">

          <FolderTree
            size={42}
            className="mx-auto mb-4 text-zinc-600"
          />

          <h2 className="text-xl font-semibold text-zinc-300">
            No repository analyzed
          </h2>

          <p className="text-sm text-zinc-600 mt-2">
            Analyze a repository from
            the Dashboard first. The
            Code Map will then show
            that repository only.
          </p>

        </div>

      </div>

    );
  }


  // ============================================================
  // LOADING
  // ============================================================

  if (loading) {

    return (

      <div className="h-[calc(100vh-64px)] flex items-center justify-center">

        <div className="flex items-center gap-2 text-zinc-500">

          <Loader2
            size={16}
            className="animate-spin"
          />

          Loading codebase...

        </div>

      </div>

    );

  }


  // ============================================================
  // ERROR
  // ============================================================

  if (
    error &&
    !files.length
  ) {

    return (

      <div className="h-[calc(100vh-64px)] flex items-center justify-center">

        <div className="text-center">

          <p className="text-red-400">
            Backend connection failed.
          </p>

          <p className="text-xs text-zinc-600 mt-2">
            {error}
          </p>

        </div>

      </div>

    );

  }


  // ============================================================
  // MAIN UI
  // ============================================================

  return (

    <div className="h-[calc(100vh-64px)] flex flex-col">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="px-8 py-5 border-b border-white/10 flex items-center justify-between">

        <div className="flex items-center gap-4">

          {view !== "files" && (

            <button
              onClick={goBack}
              className="p-2 rounded-lg border border-white/10 hover:bg-white/5 text-zinc-400 hover:text-white"
              title="Go back"
            >

              <ArrowLeft
                size={17}
              />

            </button>

          )}


          <div>

            <div className="flex items-center gap-2">

              <Network
                size={18}
                className="text-zinc-400"
              />

              <h1 className="text-xl font-semibold">
                Code Map
              </h1>

            </div>


            <p className="text-sm text-zinc-500 mt-1">

              {view === "files"

                ? "Explore your repository file by file."

                : view === "file"

                ? `Explore symbols inside ${
                    currentFile?.name ||
                    "this file"
                  }.`

                : "Inspect local relationships, risk, and source code."

              }

            </p>

          </div>

        </div>


        {/* Search */}

        <div className="flex items-center gap-2 border border-white/10 bg-[#111113] rounded-lg px-3 py-2">

          <Search
            size={15}
            className="text-zinc-500"
          />

          <input
            value={search}
            onChange={(e) =>
              setSearch(
                e.target.value
              )
            }
            placeholder={
              view === "files"
                ? "Search files..."
                : "Search symbols..."
            }
            className="bg-transparent outline-none text-sm w-56 text-zinc-300 placeholder:text-zinc-600"
          />

        </div>

      </div>


      {/* ======================================================
          BREADCRUMB
      ====================================================== */}

      <div className="px-8 py-3 border-b border-white/5 flex items-center gap-2 text-xs text-zinc-500">

        <button
          onClick={() => {

            setSelectedNode(
              null
            );

            setCurrentFile(
              null
            );

            setView(
              "files"
            );

            setNodes([]);

            setEdges([]);

            setSearch("");

          }}
          className="hover:text-white"
        >

          Repository

        </button>


        {currentFile && (

          <>

            <span>
              /
            </span>

            <button
              onClick={() =>
                openFile(
                  currentFile
                )
              }
              className="hover:text-white truncate max-w-[450px]"
            >

              {
                currentFile.file ||
                currentFile.id
              }

            </button>

          </>

        )}


        {selectedNode && (

          <>

            <span>
              /
            </span>

            <span className="text-zinc-300">

              {
                selectedNode.name ||
                selectedNode.id
              }

            </span>

          </>

        )}

      </div>


      {/* ======================================================
          CONTENT
      ====================================================== */}

      <div className="flex-1 relative min-h-0">


        {/* ====================================================
            REPOSITORY FILE VIEW
        ==================================================== */}

        {view === "files" && (

          <div className="h-full overflow-auto p-8">

            {filteredFiles.length === 0 ? (

              <div className="h-full flex items-center justify-center">

                <div className="text-center">

                  <Code2
                    size={28}
                    className="mx-auto mb-3 text-zinc-600"
                  />

                  <p className="text-zinc-400">
                    No files found.
                  </p>

                </div>

              </div>

            ) : (

              <>

                <div className="flex items-center justify-between mb-5">

                  <div>

                    <p className="text-sm text-zinc-400">

                      {
                        filteredFiles.length.toLocaleString()
                      }{" "}
                      files

                    </p>

                    <p className="text-xs text-zinc-600 mt-1">

                      Click a file to inspect
                      its functions and classes.

                    </p>

                  </div>

                </div>


                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">

                  {filteredFiles.map(
                    (file) => (

                      <button
                        key={file.id}
                        onClick={() =>
                          openFile(
                            file
                          )
                        }
                        className="text-left rounded-xl border border-white/10 bg-[#111113] hover:bg-white/[0.04] hover:border-white/20 p-4 transition"
                      >

                        <div className="flex items-start gap-3">

                          <FolderTree
                            size={17}
                            className="text-zinc-500 mt-0.5 shrink-0"
                          />

                          <div className="min-w-0">

                            <p className="text-sm text-zinc-200 truncate">

                              {
                                file.name ||
                                file.id
                              }

                            </p>

                            <p className="text-[11px] text-zinc-600 mt-1 break-all line-clamp-2">

                              {
                                file.file ||
                                file.id
                              }

                            </p>

                            <div className="mt-3 text-[11px] text-zinc-500">

                              {
                                file.symbol_count ??
                                0
                              }{" "}
                              symbols

                            </div>

                          </div>

                        </div>

                      </button>

                    )
                  )}

                </div>

              </>

            )}

          </div>

        )}


        {/* ====================================================
            FILE / NODE GRAPH VIEW
        ==================================================== */}

        {view !== "files" && (

          <>

            {graphLoading ? (

              <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#09090b]/60">

                <div className="flex items-center gap-2 text-zinc-500">

                  <Loader2
                    size={16}
                    className="animate-spin"
                  />

                  Loading graph...

                </div>

              </div>

            ) : null}


            {visibleNodes.length === 0 ? (

              <div className="h-full flex items-center justify-center">

                <div className="text-center">

                  <Code2
                    size={28}
                    className="mx-auto mb-3 text-zinc-600"
                  />

                  <p className="text-zinc-400">
                    No matching symbols in this view.
                  </p>

                </div>

              </div>

            ) : (

              <ReactFlow
                nodes={visibleNodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodeClick={
                  onNodeClick
                }
                fitView
                fitViewOptions={{
                  padding: 0.2,
                }}
                proOptions={{
                  hideAttribution: true,
                }}
              >

                <Background
                  gap={20}
                  size={1}
                />

                <Controls />

                <MiniMap />

              </ReactFlow>

            )}

          </>

        )}


        {/* ====================================================
            ERROR BANNER
        ==================================================== */}

        {error &&
          files.length > 0 && (

            <div className="absolute bottom-4 left-4 z-20 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-2 text-xs text-red-300">

              {error}

            </div>

          )}


        {/* ====================================================
            SELECTED NODE PANEL
        ==================================================== */}

        {selectedNode && (

          <div className="absolute top-4 right-4 w-[390px] max-h-[calc(100%-32px)] rounded-2xl border border-white/10 bg-[#111113] shadow-2xl overflow-hidden z-20">


            {/* ------------------------------------------------
                PANEL HEADER
            ------------------------------------------------- */}

            <div className="flex items-center justify-between p-4 border-b border-white/10">

              <div className="min-w-0">

                <p className="text-xs text-zinc-500">
                  {selectedNode.type === "file"
                    ? "Selected file"
                    : "Selected symbol"}
                </p>

                <h3 className="font-semibold mt-1 truncate">

                  {selectedNode.type ===
                  "function"

                    ? `${selectedNode.name}()`

                    : selectedNode.name ||
                      selectedNode.id}

                </h3>

              </div>


              <button
                onClick={() => {

                  setSelectedNode(
                    null
                  );

                  setAiExplanation(
                    null
                  );

                }}
                className="text-zinc-500 hover:text-white"
              >

                <X
                  size={17}
                />

              </button>

            </div>


            <div className="p-4 space-y-5 overflow-y-auto max-h-[calc(100vh-210px)]">


              {/* ------------------------------------------------
                  FILE
              ------------------------------------------------- */}

              <div>

                <p className="text-xs text-zinc-500 mb-2">
                  File
                </p>

                <p className="text-sm text-zinc-300 break-all">

                  {
                    selectedNode.file ||
                    selectedNode.id
                  }

                </p>

              </div>


              {/* ------------------------------------------------
                  FILE DETAILS
              ------------------------------------------------- */}

              {selectedNode.type === "file" && (
                <>
                  <div>
                    <p className="text-xs text-zinc-500 mb-2">
                      File Type
                    </p>

                    <p className="text-sm text-zinc-300">
                      Python file
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-zinc-500 mb-2">
                      Path
                    </p>

                    <p className="text-sm text-zinc-300 break-all">
                      {selectedNode.id}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-zinc-500 mb-3">
                      Codebase Statistics
                    </p>

                    {(() => {
                      const stats =
                        getFileStats(selectedNode);

                      return (
                        <div className="grid grid-cols-2 gap-3">
                          <div className="rounded-lg border border-white/5 bg-black/20 p-3">
                            <p className="text-[11px] text-zinc-500">
                              Symbols
                            </p>

                            <p className="text-lg font-semibold mt-1 text-zinc-200">
                              {stats.symbols ||
                                currentFile?.symbol_count ||
                                0}
                            </p>
                          </div>

                          <div className="rounded-lg border border-white/5 bg-black/20 p-3">
                            <p className="text-[11px] text-zinc-500">
                              Functions
                            </p>

                            <p className="text-lg font-semibold mt-1 text-zinc-200">
                              {stats.functions}
                            </p>
                          </div>

                          <div className="rounded-lg border border-white/5 bg-black/20 p-3">
                            <p className="text-[11px] text-zinc-500">
                              Classes
                            </p>

                            <p className="text-lg font-semibold mt-1 text-zinc-200">
                              {stats.classes}
                            </p>
                          </div>

                          <div className="rounded-lg border border-white/5 bg-black/20 p-3">
                            <p className="text-[11px] text-zinc-500">
                              Imports
                            </p>

                            <p className="text-lg font-semibold mt-1 text-zinc-200">
                              {stats.imports ||
                                selectedNode.dependencies?.length ||
                                0}
                            </p>
                          </div>
                        </div>
                      );
                    })()}
                  </div>

                  <div>
                    <p className="text-xs text-zinc-500 mb-2">
                      Relationships
                    </p>

                    {(() => {
                      const stats =
                        getFileStats(selectedNode);

                      return (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-zinc-500">
                              Contains
                            </span>

                            <span className="text-zinc-300">
                              {stats.contains ||
                                stats.symbols}
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-sm">
                            <span className="text-zinc-500">
                              Imports
                            </span>

                            <span className="text-zinc-300">
                              {stats.imports ||
                                selectedNode.dependencies?.length ||
                                0}
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-sm">
                            <span className="text-zinc-500">
                              Calls
                            </span>

                            <span className="text-zinc-300">
                              {stats.calls}
                            </span>
                          </div>
                        </div>
                      );
                    })()}
                  </div>

                  <div>
                    <p className="text-xs text-zinc-500 mb-2">
                      Symbols in this file
                    </p>

                    {selectedNode.local_graph?.nodes
                      ?.filter(
                        (node) =>
                          node.type === "function" ||
                          node.type === "class"
                      )
                      .length > 0 ? (
                      <div className="space-y-1.5">
                        {selectedNode.local_graph.nodes
                          .filter(
                            (node) =>
                              node.type === "function" ||
                              node.type === "class"
                          )
                          .map((symbol) => (
                            <p
                              key={symbol.id}
                              className="text-sm text-zinc-300 break-all"
                            >
                              {symbol.type === "function"
                                ? `${symbol.name}()`
                                : symbol.name}
                            </p>
                          ))}
                      </div>
                    ) : (
                      <p className="text-sm text-zinc-600">
                        No functions or classes detected.
                      </p>
                    )}
                  </div>
                </>
              )}


              {/* ------------------------------------------------
                  FUNCTION DETAILS
              ------------------------------------------------- */}

              {selectedNode.type ===
                "function" && (

                <>


                  {/* --------------------------------------------
                      LINES
                  --------------------------------------------- */}

                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Lines
                    </p>

                    <p className="text-sm text-zinc-300">

                      {
                        selectedNode.line
                      }

                      {" - "}

                      {
                        selectedNode.end_line
                      }

                    </p>

                  </div>


                  {/* --------------------------------------------
                      RISK
                  --------------------------------------------- */}

                  <div className="border border-white/10 rounded-xl bg-white/[0.02] overflow-hidden">


                    {/* Risk Header */}

                    <div className="p-4 border-b border-white/10">

                      <div className="flex items-center justify-between">

                        <div className="flex items-center gap-2">

                          <ShieldAlert
                            size={16}
                            className={getRiskColor(
                              selectedNode.risk?.risk_level
                            )}
                          />

                          <p className="text-sm font-medium">
                            ML Risk Analysis
                          </p>

                        </div>


                        {selectedNode.risk && (

                          <RiskBadge
                            level={
                              selectedNode.risk
                                .risk_level
                            }
                          />

                        )}

                      </div>

                    </div>


                    {/* Risk Content */}

                    {riskLoading ? (

                      <div className="p-4 flex items-center gap-2 text-zinc-500 text-sm">

                        <Loader2
                          size={14}
                          className="animate-spin"
                        />

                        Loading risk prediction...

                      </div>

                    ) : selectedNode.risk ? (

                      <div className="p-4 space-y-4">


                        {/* --------------------------------------
                            RISK INDEX ONLY
                            
                            Risk Probability has intentionally
                            been removed from the primary UI.
                        --------------------------------------- */}

                        <div className="grid grid-cols-1 gap-3">

                          <div className="rounded-lg border border-white/5 bg-black/20 p-3">

                            <p className="text-[11px] text-zinc-500">
                              Risk Index
                            </p>

                            <p className="text-xl font-semibold mt-1">

                              {Number(
                                selectedNode.risk
                                  .risk_score ||
                                  0
                              ).toFixed(0)}

                              <span className="text-xs text-zinc-600 ml-1">
                                / 100
                              </span>

                            </p>

                          </div>

                        </div>


                        {/* --------------------------------------
                            MODEL SIGNALS
                        --------------------------------------- */}

                        {selectedNode.risk
                          .reasons
                          ?.length >
                          0 && (

                          <div>

                            <p className="text-xs text-zinc-500 mb-2">
                              Model Signals
                            </p>


                            <div className="space-y-1.5">

                              {selectedNode.risk
                                .reasons
                                .slice(
                                  0,
                                  4
                                )
                                .map(
                                  (
                                    reason,
                                    index
                                  ) => (

                                    <div
                                      key={
                                        index
                                      }
                                      className="text-xs text-zinc-400 bg-black/20 border border-white/5 rounded-lg px-3 py-2"
                                    >

                                      {
                                        reason
                                      }

                                    </div>

                                  )
                                )}

                            </div>

                          </div>

                        )}


                        {/* --------------------------------------
                            GEMINI BUTTON
                        --------------------------------------- */}

                        <button
                          onClick={
                            explainWithAI
                          }
                          disabled={
                            explaining
                          }
                          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-purple-500/20 bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 hover:border-purple-500/30 transition text-sm disabled:opacity-50"
                        >

                          {explaining ? (

                            <>

                              <Loader2
                                size={15}
                                className="animate-spin"
                              />

                              Gemini is analyzing...

                            </>

                          ) : (

                            <>

                              <Sparkles
                                size={15}
                              />

                              Explain Risk with AI

                            </>

                          )}

                        </button>


                        {/* --------------------------------------
                            GEMINI EXPLANATION
                        --------------------------------------- */}

                        {aiExplanation && (

                          <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-4">

                            <div className="flex items-center gap-2 mb-3">

                              <Sparkles
                                size={15}
                                className="text-purple-400"
                              />

                              <span className="text-xs font-medium text-purple-300">
                                Gemini Risk Explanation
                              </span>

                            </div>


                            <p className="text-xs leading-5 text-zinc-300">

                              {
                                aiExplanation
                              }

                            </p>

                          </div>

                        )}

                      </div>

                    ) : (

                      <div className="p-4">

                        <p className="text-xs text-zinc-600">

                          No ML risk prediction
                          is available for this node.

                        </p>

                      </div>

                    )}

                  </div>


                  {/* --------------------------------------------
                      CALLERS
                  --------------------------------------------- */}

                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Callers
                    </p>

                    {selectedNode.callers
                      ?.length > 0 ? (

                      <div className="space-y-1 text-sm text-zinc-300">

                        {selectedNode.callers.map(
                          (caller) => (

                            <p
                              key={caller}
                            >
                              ← {caller}
                            </p>

                          )
                        )}

                      </div>

                    ) : (

                      <p className="text-sm text-zinc-600">
                        No local callers
                      </p>

                    )}

                  </div>


                  {/* --------------------------------------------
                      CALLEES
                  --------------------------------------------- */}

                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Callees
                    </p>

                    {selectedNode.callees
                      ?.length > 0 ? (

                      <div className="space-y-1 text-sm text-zinc-300">

                        {selectedNode.callees.map(
                          (callee) => (

                            <p
                              key={callee}
                            >
                              → {callee}
                            </p>

                          )
                        )}

                      </div>

                    ) : (

                      <p className="text-sm text-zinc-600">
                        No local callees
                      </p>

                    )}

                  </div>


                  {/* --------------------------------------------
                      DEPENDENCIES
                  --------------------------------------------- */}

                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Dependencies
                    </p>

                    {selectedNode
                      .dependencies
                      ?.length > 0 ? (

                      <div className="space-y-1 text-sm text-zinc-300">

                        {selectedNode.dependencies.map(
                          (dependency) => (

                            <p
                              key={dependency}
                            >
                              ↳ {dependency}
                            </p>

                          )
                        )}

                      </div>

                    ) : (

                      <p className="text-sm text-zinc-600">
                        No dependencies
                      </p>

                    )}

                  </div>


                  {/* --------------------------------------------
                      SOURCE CODE
                  --------------------------------------------- */}

                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Source Code
                    </p>

                    <pre className="text-xs bg-black/40 border border-white/5 rounded-lg p-3 overflow-auto text-zinc-400 max-h-64 whitespace-pre-wrap">

                      {
                        selectedNode.code ||
                        "No source available"
                      }

                    </pre>

                  </div>

                </>

              )}


              {/* ------------------------------------------------
                  CLASS DETAILS
              ------------------------------------------------- */}

              {selectedNode.type ===
                "class" && (

                <div>

                  <p className="text-xs text-zinc-500 mb-2">
                    Symbol Type
                  </p>

                  <p className="text-sm text-zinc-300">
                    Python class
                  </p>

                </div>

              )}

            </div>

          </div>

        )}

      </div>

    </div>

  );
}