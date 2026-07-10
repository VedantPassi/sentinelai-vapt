"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import { AgentChain, AgentFinding, ChainStep } from "@/lib/api";

interface ChainGraphProps {
  chains: AgentChain[];
  findings: AgentFinding[];
}

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

function buildElements(
  chain: AgentChain,
  findingsById: Map<string, AgentFinding>
): ElementDefinition[] {
  const elements: ElementDefinition[] = [];
  const sorted = [...chain.steps].sort((a, b) => a.step - b.step);

  sorted.forEach((step) => {
    const finding = step.finding_id ? findingsById.get(step.finding_id) : undefined;
    const label = finding
      ? (finding.title.length > 40 ? finding.title.slice(0, 37) + "…" : finding.title)
      : `Step ${step.step}`;
    const severity = finding?.severity ?? "info";

    elements.push({
      data: {
        id: `step-${step.step}`,
        label,
        fullAction: step.action,
        mitreId: step.mitre_id,
        severity,
        findingId: step.finding_id,
        unresolved: Boolean(step.finding_id) && !finding,
      },
    });
  });

  for (let i = 0; i < sorted.length - 1; i++) {
    elements.push({
      data: {
        id: `edge-${i}`,
        source: `step-${sorted[i].step}`,
        target: `step-${sorted[i + 1].step}`,
        label: sorted[i + 1].mitre_id ?? "",
      },
    });
  }

  return elements;
}

export default function ChainGraph({ chains, findings }: ChainGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [selectedChainId, setSelectedChainId] = useState<string | null>(
    chains[0]?.id ?? null
  );
  const [selectedNode, setSelectedNode] = useState<{
    label: string;
    fullAction: string;
    mitreId: string | null;
    severity: string;
    unresolved: boolean;
  } | null>(null);

  const selectedChain = chains.find((c) => c.id === selectedChainId) ?? null;

  useEffect(() => {
    if (!containerRef.current || !selectedChain) return;

    const findingsById = new Map(findings.map((f) => [f.id, f]));
    const elements = buildElements(selectedChain, findingsById);

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      layout: {
        name: "breadthfirst",
        directed: true,
        spacingFactor: 1.4,
        padding: 30,
      },
      style: [
        {
          selector: "node",
          style: {
            "background-color": (el) =>
              SEVERITY_COLOR[el.data("severity")] ?? SEVERITY_COLOR.info,
            "border-width": (el) => (el.data("unresolved") ? 2 : 0),
            "border-color": "#9ca3af",
            "border-style": "dashed",
            label: "data(label)",
            color: "#111827",
            "font-size": "11px",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-wrap": "wrap",
            "text-max-width": "100px",
            width: 36,
            height: 36,
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#9ca3af",
            "target-arrow-color": "#9ca3af",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "9px",
            color: "#6b7280",
            "text-background-color": "#ffffff",
            "text-background-opacity": 1,
            "text-background-padding": "2px",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#1d4ed8",
            "border-style": "solid",
          },
        },
      ],
    });

    cy.on("tap", "node", (evt) => {
      const d = evt.target.data();
      setSelectedNode({
        label: d.label,
        fullAction: d.fullAction,
        mitreId: d.mitreId,
        severity: d.severity,
        unresolved: d.unresolved,
      });
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) setSelectedNode(null);
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [selectedChain, findings]);

  if (chains.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        No attack chains identified for this scan.
      </p>
    );
  }

  return (
    <div className="flex gap-4 h-[500px]">
      {/* Chain selector */}
      <div className="w-56 shrink-0 overflow-y-auto space-y-1 border-r border-gray-100 pr-3">
        {chains.map((chain) => (
          <button
            key={chain.id}
            onClick={() => {
              setSelectedChainId(chain.id);
              setSelectedNode(null);
            }}
            className={`w-full text-left rounded p-2 border transition-colors ${
              chain.id === selectedChainId
                ? "border-blue-300 bg-blue-50"
                : "border-gray-200 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span
                className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                  IMPACT_BADGE[chain.impact] ?? ""
                }`}
              >
                {chain.impact}
              </span>
              <span className="text-xs text-gray-400">{chain.steps.length} steps</span>
            </div>
            <p className="text-sm font-medium leading-tight">{chain.title}</p>
          </button>
        ))}
      </div>

      {/* Graph + detail panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedChain && (
          <div className="mb-2 shrink-0">
            <p className="text-sm text-gray-600">{selectedChain.description}</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {selectedChain.mitre_ids.map((id) => (
                <span
                  key={id}
                  className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-mono"
                >
                  {id}
                </span>
              ))}
            </div>
          </div>
        )}

        <div ref={containerRef} className="flex-1 border border-gray-100 rounded min-h-0" />

        {selectedNode && (
          <div className="mt-2 shrink-0 p-2 bg-gray-50 rounded text-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="w-2.5 h-2.5 rounded-full inline-block shrink-0"
                style={{ backgroundColor: SEVERITY_COLOR[selectedNode.severity] }}
              />
              <span className="font-medium">{selectedNode.label}</span>
              {selectedNode.mitreId && (
                <span className="text-xs text-gray-500 font-mono">{selectedNode.mitreId}</span>
              )}
              {selectedNode.unresolved && (
                <span className="text-xs text-yellow-600 bg-yellow-50 px-1.5 py-0.5 rounded">
                  finding not linked
                </span>
              )}
            </div>
            <p className="text-gray-600 text-xs">{selectedNode.fullAction}</p>
          </div>
        )}
      </div>
    </div>
  );
}
