"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import { AttackGraph, BlastRadius, GraphNode, getAttackGraph, getBlastRadius } from "@/lib/api";

const NODE_COLOR: Record<string, string> = {
  finding: "#dc2626",
  chain: "#2563eb",
  step: "#16a34a",
};

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#ca8a04",
  low: "#2563eb",
  info: "#6b7280",
};

const IMPACT_BADGE: Record<string, string> = {
  critical: "text-red-600 bg-red-50",
  high: "text-orange-600 bg-orange-50",
  medium: "text-yellow-600 bg-yellow-50",
  low: "text-blue-600 bg-blue-50",
};

interface Props {
  scanId: string;
}

export default function AttackGraphView({ scanId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [graph, setGraph] = useState<AttackGraph | null>(null);
  const [blastRadius, setBlastRadius] = useState<BlastRadius[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"graph" | "blast">("graph");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([getAttackGraph(scanId), getBlastRadius(scanId)])
      .then(([g, br]) => {
        if (!cancelled) { setGraph(g); setBlastRadius(br); }
      })
      .catch((e) => { if (!cancelled) setError(e.message ?? "Failed to load graph"); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [scanId]);

  useEffect(() => {
    if (!containerRef.current || !graph || activeTab !== "graph") return;

    const elements: ElementDefinition[] = [];

    for (const node of graph.nodes) {
      elements.push({
        data: {
          id: node.id,
          label: node.label.length > 35 ? node.label.slice(0, 32) + "…" : node.label,
          fullLabel: node.label,
          nodeType: node.type,
          severity: node.severity,
          surface: node.surface,
          riskScore: node.risk_score,
        },
      });
    }

    for (const edge of graph.edges) {
      elements.push({
        data: {
          id: `${edge.source}__${edge.relation}__${edge.target}`,
          source: edge.source,
          target: edge.target,
          relation: edge.relation,
        },
      });
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      layout: { name: "breadthfirst", directed: true, spacingFactor: 1.3, padding: 40 },
      minZoom: 0.2,
      maxZoom: 2.5,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (el: cytoscape.NodeSingular) => {
              const t = el.data("nodeType");
              if (t === "finding") return SEVERITY_COLOR[el.data("severity")] ?? SEVERITY_COLOR.info;
              return NODE_COLOR[t] ?? "#6b7280";
            },
            label: "data(label)",
            color: "#111827",
            "font-size": "10px",
            "text-valign": "bottom",
            "text-margin-y": 5,
            "text-wrap": "wrap",
            "text-max-width": "90px",
            width: (el: cytoscape.NodeSingular) => el.data("nodeType") === "chain" ? 52 : 38,
            height: (el: cytoscape.NodeSingular) => el.data("nodeType") === "chain" ? 52 : 38,
            shape: (el: cytoscape.NodeSingular) => {
              const t = el.data("nodeType");
              if (t === "chain") return "diamond";
              if (t === "step") return "round-rectangle";
              return "ellipse";
            },
            "border-width": 0,
          },
        },
        {
          selector: "node:selected",
          style: { "border-width": 3, "border-color": "#1d4ed8", "border-style": "solid" },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#9ca3af",
            "target-arrow-color": "#9ca3af",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(relation)",
            "font-size": "8px",
            color: "#9ca3af",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.8,
            "text-background-padding": "2px",
          },
        },
      ],
    });

    cy.on("tap", "node", (evt) => {
      const d = evt.target.data();
      setSelectedNode({
        id: d.id,
        label: d.fullLabel,
        type: d.nodeType,
        severity: d.severity,
        surface: d.surface,
        risk_score: d.riskScore,
      });
    });

    cy.on("tap", (evt) => { if (evt.target === cy) setSelectedNode(null); });

    cy.ready(() => {
      if (cy.nodes().length <= 2) { cy.zoom(1.2); cy.center(); }
    });

    cyRef.current = cy;
    return () => { cy.destroy(); cyRef.current = null; };
  }, [graph, activeTab]);

  if (loading) return <p className="text-sm text-gray-400 text-center py-8">Loading attack graph…</p>;
  if (error) return <p className="text-sm text-red-500 text-center py-8">{error}</p>;
  if (!graph || graph.nodes.length === 0)
    return <p className="text-sm text-gray-400 text-center py-8">No graph data — run a scan first.</p>;

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full inline-block bg-red-600" /> Finding
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rotate-45 inline-block bg-blue-600" style={{clipPath:"polygon(50% 0,100% 50%,50% 100%,0 50%)"}} /> Chain
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded inline-block bg-green-600" /> Step
        </span>
        <span className="ml-auto">{graph.nodes.length} nodes · {graph.edges.length} edges</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-100">
        {(["graph", "blast"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`text-sm px-3 py-1.5 border-b-2 transition-colors ${
              activeTab === tab
                ? "border-blue-500 text-blue-600 font-medium"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "graph" ? "Attack Graph" : `Blast Radius (${blastRadius.length})`}
          </button>
        ))}
      </div>

      {activeTab === "graph" && (
        <div className="flex gap-3" style={{ height: 460 }}>
          <div ref={containerRef} className="flex-1 border border-gray-100 rounded min-h-0" />
          {selectedNode && (
            <div className="w-56 shrink-0 p-3 bg-gray-50 rounded border border-gray-100 text-sm space-y-2 overflow-y-auto">
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: NODE_COLOR[selectedNode.type] ?? "#6b7280" }}
                />
                <span className="text-xs font-mono uppercase text-gray-400">{selectedNode.type}</span>
              </div>
              <p className="font-medium leading-snug">{selectedNode.label}</p>
              {selectedNode.severity && (
                <p className="text-xs">
                  <span className="text-gray-400">Severity: </span>
                  <span className={`font-semibold ${IMPACT_BADGE[selectedNode.severity] ?? ""} px-1.5 py-0.5 rounded`}>
                    {selectedNode.severity}
                  </span>
                </p>
              )}
              {selectedNode.surface && (
                <p className="text-xs">
                  <span className="text-gray-400">Surface: </span>
                  <span className="font-mono text-purple-600">{selectedNode.surface}</span>
                </p>
              )}
              {selectedNode.risk_score !== null && selectedNode.risk_score !== undefined && (
                <p className="text-xs">
                  <span className="text-gray-400">Risk score: </span>
                  <span className="font-mono">{selectedNode.risk_score}</span>
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === "blast" && (
        <div className="space-y-2">
          {blastRadius.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">No blast radius data.</p>
          ) : (
            blastRadius.map((br) => (
              <div key={br.finding_id} className="border rounded p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{br.finding_title}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${IMPACT_BADGE[br.max_impact] ?? ""}`}>
                      {br.max_impact}
                    </span>
                    <span className="text-xs text-gray-400">{br.chains_affected} chain{br.chains_affected !== 1 ? "s" : ""}</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {br.chain_titles.map((t, i) => (
                    <span key={i} className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">{t}</span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
