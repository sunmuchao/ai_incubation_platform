// 依赖关系图可视化组件 - Bento Grid 风格
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ZoomIn, ZoomOut, Download, Maximize } from 'lucide-react';

interface Node {
  id: string;
  label: string;
  type: string;
  size?: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface Edge {
  source: string | Node;
  target: string | Node;
  type: string;
  label?: string;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

interface DependencyGraphProps {
  data: GraphData;
  config?: {
  title?: string;
    layout?: 'force_directed' | 'hierarchical' | 'circular';
    node_style?: any;
    edge_style?: any;
  };
  height?: number;
}

const DependencyGraph: React.FC<DependencyGraphProps> = ({
  data,
  height = 500,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // 节点颜色映射 - Monochromatic + 强调色
  const nodeColorMap: Record<string, string> = {
    'module': '#3d9cf5',
    'class': '#4caf50',
    'function': '#ff9800',
    'interface': '#9c27b0',
    'file': '#64748b',
    'package': '#e91e63',
    'default': '#9aa8b8',
  };

  // 节点大小映射
  const nodeSizeMap: Record<string, number> = {
    'module': 20,
    'class': 15,
    'function': 10,
    'interface': 12,
    'file': 8,
    'package': 25,
    'default': 10,
  };

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    const width = containerRef.current?.clientWidth || 800;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // 创建分组
    const g = svg.append('g');

    // 创建缩放行为
    const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', (event) => {
      g.attr('transform', event.transform);
      setZoomLevel(event.transform.k);
    });

    svg.call(zoom as any);

    // 力导向模拟
    const simulation = d3.forceSimulation()
      .nodes(data.nodes)
      .force('link', d3.forceLink(data.edges).id((d: any) => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(30));

    // 绘制连线
    const links = g.append('g')
      .selectAll('line')
      .data(data.edges)
      .join('line')
      .attr('stroke', '#475569')
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.5);

    // 绘制箭头
    const marker = svg.append('defs')
      .append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 28)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto');

    marker.append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#64748b');

    links.attr('marker-end', 'url(#arrowhead)');

    // 绘制节点
    const nodes = g.append('g')
      .selectAll('g')
      .data(data.nodes)
      .join('g')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended) as any);

    // 节点光圈（选中效果）
    nodes.append('circle')
      .attr('r', (d: any) => (nodeSizeMap[d.type] || nodeSizeMap.default) + 4)
      .attr('fill', 'transparent')
      .attr('stroke', '#3d9cf5')
      .attr('stroke-width', 0)
      .attr('stroke-opacity', 0)
      .attr('class', 'selection-ring');

    // 节点圆圈
    nodes.append('circle')
      .attr('r', (d: any) => nodeSizeMap[d.type] || nodeSizeMap.default)
      .attr('fill', (d: any) => nodeColorMap[d.type] || nodeColorMap.default)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.3)
      .attr('opacity', 0.9)
      .attr('cursor', 'pointer')
      .attr('class', 'node-circle')
      .on('click', (_event, d: any) => {
        setSelectedNode(d);
        // 高亮选中节点
        d3.selectAll('.selection-ring').attr('stroke-opacity', 0).attr('stroke-width', 0);
        d3.selectAll('.node-circle').attr('filter', null);
        const ring = d3.select(_event.currentTarget.parentNode).select('.selection-ring');
        ring.attr('stroke-opacity', 1).attr('stroke-width', 2);
        d3.select(_event.currentTarget).attr('filter', 'drop-shadow(0 0 8px rgba(61, 156, 245, 0.6))');
      })
      .on('mouseenter', function() {
        d3.select(this).attr('opacity', 1).attr('filter', 'drop-shadow(0 0 6px rgba(255,255,255,0.3))');
      })
      .on('mouseleave', function() {
        d3.select(this).attr('opacity', 0.9).attr('filter', null);
      });

    // 节点标签
    nodes.append('text')
      .attr('dx', (d: any) => (nodeSizeMap[d.type] || nodeSizeMap.default) + 10)
      .attr('dy', 4)
      .text((d: any) => d.label.length > 20 ? d.label.slice(0, 20) + '...' : d.label)
      .attr('fill', '#e8ecf1')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .attr('pointer-events', 'none')
      .attr('opacity', 0.9);

    // 更新节点位置
    simulation.on('tick', () => {
      links
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      nodes.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    // 拖拽行为
    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: any) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // 自动适应屏幕
    setTimeout(() => {
      svg.transition().duration(750).call(
        zoom as any,
        d3.zoomIdentity.translate(0, 0).scale(1)
      );
    }, 100);

    return () => {
      simulation.stop();
    };
  }, [data]);

  const handleZoomIn = () => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.transition().duration(300).call(
      (d3.zoom() as any).scaleBy,
      1.3
    );
  };

  const handleZoomOut = () => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.transition().duration(300).call(
      (d3.zoom() as any).scaleBy,
      0.7
    );
  };

  const handleFitToScreen = () => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.transition().duration(750).call(
      (d3.zoom() as any).transform,
      d3.zoomIdentity.translate(0, 0).scale(1)
    );
    setZoomLevel(1);
  };

  const handleDownload = () => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dependency-graph.svg';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div ref={containerRef} className="relative border border-border-light rounded-xl overflow-hidden bento-card">
      {/* 工具栏 */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
        <button
          onClick={handleZoomIn}
          className="p-2 bg-surface-lighter border border-border-light rounded-lg hover:bg-surface hover:border-accent/30 transition-all duration-200 text-text-secondary hover:text-accent"
          title="放大"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-surface-lighter border border-border-light rounded-lg hover:bg-surface hover:border-accent/30 transition-all duration-200 text-text-secondary hover:text-accent"
          title="缩小"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleFitToScreen}
          className="p-2 bg-surface-lighter border border-border-light rounded-lg hover:bg-surface hover:border-accent/30 transition-all duration-200 text-text-secondary hover:text-accent"
          title="适应屏幕"
        >
          <Maximize className="w-4 h-4" />
        </button>
        <button
          onClick={handleDownload}
          className="p-2 bg-surface-lighter border border-border-light rounded-lg hover:bg-surface hover:border-accent/30 transition-all duration-200 text-text-secondary hover:text-accent"
          title="下载 SVG"
        >
          <Download className="w-4 h-4" />
        </button>
      </div>

      {/* 图例 */}
      <div className="absolute top-3 left-3 z-10 bg-surface-lighter/90 backdrop-blur-bento border border-border-light rounded-lg p-3 shadow-bento">
        <div className="text-xs font-semibold text-text-primary mb-2">节点类型</div>
        <div className="space-y-1.5">
          {Object.entries(nodeColorMap).filter(([k]) => k !== 'default').map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full shadow-sm"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-text-secondary capitalize">{type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* SVG 画布 */}
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        className="bg-base-950"
      />

      {/* 节点详情弹窗 */}
      {selectedNode && (
        <div className="absolute bottom-4 left-4 right-4 bento-card p-4 z-10 animate-slide-up">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: nodeColorMap[selectedNode.type] || nodeColorMap.default }}
              >
                <span className="text-white text-xs font-bold">{selectedNode.label.charAt(0).toUpperCase()}</span>
              </div>
              <div>
                <h3 className="font-semibold text-base text-text-primary">{selectedNode.label}</h3>
                <p className="text-xs text-text-muted">
                  类型：<span className="text-text-secondary">{selectedNode.type}</span>
                </p>
                <p className="text-xs text-text-muted mt-0.5 font-mono">{selectedNode.id}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-lighter rounded-lg transition-all duration-200"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* 缩放级别指示 */}
      <div className="absolute bottom-3 right-3 text-xs text-text-muted bg-surface-lighter/80 backdrop-blur-bento px-2.5 py-1.5 rounded-md border border-border-light font-mono">
        {(zoomLevel * 100).toFixed(0)}%
      </div>
    </div>
  );
};

export default DependencyGraph;
