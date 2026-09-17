import { useCallback, useEffect, useState } from "react";
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
import { Search, X, Code2 } from "lucide-react";

const NODE_WIDTH = 180;
const NODE_HEIGHT = 70;

function CustomNode({ data }) {
  const isFile = data.type === "file";

  return (
    <div
      className={`min-w-[180px] rounded-xl border px-4 py-3 shadow-xl ${
        isFile
          ? "border-white/20 bg-[#18181b]"
          : "border-white/10 bg-[#111113]"
      }`}
    >
      <Handle type="target" position={Position.Left} />

      <div className="flex items-center gap-2">
        <Code2 size={15} className="text-zinc-400" />

        <span className="text-sm font-medium text-zinc-200">
          {data.label}
        </span>
      </div>

      <p className="text-[11px] text-zinc-600 mt-1">
        {isFile ? "Python file" : "Function"}
      </p>

      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = {
  custom: CustomNode,
};


function getLayoutedElements(nodes, edges) {
  const graph = new dagre.graphlib.Graph();

  graph.setDefaultEdgeLabel(() => ({}));

  graph.setGraph({
    rankdir: "LR",
    nodesep: 80,
    ranksep: 150,
  });

  nodes.forEach((node) => {
    graph.setNode(node.id, {
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    });
  });

  edges.forEach((edge) => {
    graph.setEdge(edge.source, edge.target);
  });

  dagre.layout(graph);

  const layoutedNodes = nodes.map((node) => {
    const position = graph.node(node.id);

    return {
      ...node,
      position: {
        x: position.x - NODE_WIDTH / 2,
        y: position.y - NODE_HEIGHT / 2,
      },
    };
  });

  return {
    nodes: layoutedNodes,
    edges,
  };
}


export default function CodeMap() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadGraph() {
      try {
        const response = await fetch("/api/graph");

        if (!response.ok) {
          throw new Error("Failed to load graph");
        }

        const data = await response.json();

        if (data.error) {
          setNodes([]);
          setEdges([]);
          setLoading(false);
          return;
        }

        const formattedNodes = data.nodes.map((node) => ({
          id: node.id,
          type: "custom",
          data: {
            label:
              node.type === "file"
                ? node.id
                : node.type === "function"
                ? `${node.name}()`
                : node.name || node.id,

            type: node.type,
          },
          position: { x: 0, y: 0 },
        }));

        const formattedEdges = data.edges.map((edge, index) => ({
          id: `edge-${index}`,
          source: edge.source,
          target: edge.target,
          label: edge.type,
          type: "smoothstep",
        }));

        const layout = getLayoutedElements(
          formattedNodes,
          formattedEdges
        );

        setNodes(layout.nodes);
        setEdges(layout.edges);

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadGraph();
  }, []);


  const onNodeClick = useCallback(async (_, node) => {
    try {
      const response = await fetch(
        `/api/graph/node/${encodeURIComponent(node.id)}`
      );

      const data = await response.json();

      setSelectedNode(data);

    } catch (err) {
      console.error("Could not load node details:", err);
    }
  }, []);


  if (loading) {
    return (
      <div className="h-[calc(100vh-64px)] flex items-center justify-center">
        <p className="text-zinc-500">
          Loading codebase...
        </p>
      </div>
    );
  }


  if (error) {
    return (
      <div className="h-[calc(100vh-64px)] flex items-center justify-center">
        <p className="text-red-400">
          Backend connection failed.
        </p>
      </div>
    );
  }


  return (
    <div className="h-[calc(100vh-64px)] flex flex-col">

      {/* Header */}
      <div className="px-8 py-5 border-b border-white/10 flex items-center justify-between">

        <div>
          <h1 className="text-xl font-semibold">
            Code Map
          </h1>

          <p className="text-sm text-zinc-500 mt-1">
            Explore dependencies and relationships in your codebase.
          </p>
        </div>

        <div className="flex items-center gap-2 border border-white/10 bg-[#111113] rounded-lg px-3 py-2">

          <Search
            size={15}
            className="text-zinc-500"
          />

          <input
            placeholder="Search functions..."
            className="bg-transparent outline-none text-sm w-48 text-zinc-300 placeholder:text-zinc-600"
          />

        </div>

      </div>


      {/* Graph */}
      <div className="flex-1 relative">

        {nodes.length === 0 ? (

          <div className="h-full flex items-center justify-center">

            <div className="text-center">

              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl border border-white/10 flex items-center justify-center">

                <Code2
                  size={28}
                  className="text-zinc-600"
                />

              </div>

              <h3 className="text-zinc-300 font-medium">
                No repository analyzed
              </h3>

              <p className="text-zinc-600 text-sm mt-2">
                Analyze a Python repository to generate the code map.
              </p>

            </div>

          </div>

        ) : (

          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
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


        {/* Node Details */}
        {selectedNode && (

          <div className="absolute top-4 right-4 w-80 rounded-2xl border border-white/10 bg-[#111113] shadow-2xl overflow-hidden">

            <div className="flex items-center justify-between p-4 border-b border-white/10">

              <div>

                <p className="text-xs text-zinc-500">
                  Selected node
                </p>

                <h3 className="font-semibold mt-1">
                  {selectedNode.name
                    ? `${selectedNode.name}()`
                    : selectedNode.id}
                </h3>

              </div>

              <button
                onClick={() => setSelectedNode(null)}
                className="text-zinc-500 hover:text-white"
              >
                <X size={17} />
              </button>

            </div>


            <div className="p-4 space-y-5">

              <div>

                <p className="text-xs text-zinc-500 mb-2">
                  File
                </p>

                <p className="text-sm text-zinc-300">
                  {selectedNode.file || selectedNode.id}
                </p>

              </div>


              {selectedNode.type === "function" && (
                <>

                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Lines
                    </p>

                    <p className="text-sm text-zinc-300">
                      {selectedNode.line} -{" "}
                      {selectedNode.end_line}
                    </p>

                  </div>


                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Callees
                    </p>

                    {selectedNode.callees?.length > 0 ? (

                      <div className="space-y-1 text-sm text-zinc-300">

                        {selectedNode.callees.map((callee) => (
                          <p key={callee}>
                            → {callee}
                          </p>
                        ))}

                      </div>

                    ) : (

                      <p className="text-sm text-zinc-600">
                        No callees
                      </p>

                    )}

                  </div>


                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Callers
                    </p>

                    {selectedNode.callers?.length > 0 ? (

                      <div className="space-y-1 text-sm text-zinc-300">

                        {selectedNode.callers.map((caller) => (
                          <p key={caller}>
                            ← {caller}
                          </p>
                        ))}

                      </div>

                    ) : (

                      <p className="text-sm text-zinc-600">
                        No callers
                      </p>

                    )}

                  </div>


                  <div>

                    <p className="text-xs text-zinc-500 mb-2">
                      Source Code
                    </p>

                    <pre className="text-xs bg-black/40 border border-white/5 rounded-lg p-3 overflow-auto text-zinc-400 max-h-52">
                      {selectedNode.code || "No source available"}
                    </pre>

                  </div>

                </>
              )}

            </div>

          </div>

        )}

      </div>

    </div>
  );
}