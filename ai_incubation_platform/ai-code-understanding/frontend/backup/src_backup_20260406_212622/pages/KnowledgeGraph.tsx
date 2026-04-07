// 知识图谱页面
import React, { useState, useEffect, useRef } from 'react';
import { Network, Search, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import { understandingApi } from '@/services/api';
import * as d3 from 'd3';
import { toast } from 'sonner';

interface Node {
  id: string;
  name: string;
  node_type: string;
  file_path?: string;
  in_degree: number;
  out_degree: number;
  is_core: boolean;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface Edge {
  source: string;
  target: string;
  edge_type: string;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
  node_count: number;
  edge_count: number;
}

const KnowledgeGraph: React.FC = () => {
  const [projectName, setProjectName] = useState('ai-code-understanding');
  const [repoPath, setRepoPath] = useState('/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding');
  const [layout, setLayout] = useState<'force' | 'circular' | 'dag'>('force');
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const svgRef = useRef<SVGSVGElement>(null);

  const loadGraph = async () => {
    setLoading(true);
    try {
      const response = await understandingApi.knowledgeGraphViz({
        project_name: projectName,
        repo_path: repoPath,
        layout,
        max_nodes: 100,
      });

      if (response.success && response.data) {
        setGraphData(response.data);
        toast.success(`加载 ${response.data.node_count} 个节点，${response.data.edge_count} 条边`);
      }
    } catch (error: any) {
      // 使用演示数据
      const demoData: GraphData = {
        nodes: [
          { id: 'project', name: 'ai-code-understanding', node_type: 'PROJECT', in_degree: 0, out_degree: 5, is_core: true },
          { id: 'src', name: 'src', node_type: 'PACKAGE', in_degree: 1, out_degree: 4, is_core: true },
          { id: 'api', name: 'api', node_type: 'PACKAGE', in_degree: 1, out_degree: 4, is_core: false },
          { id: 'services', name: 'services', node_type: 'PACKAGE', in_degree: 1, out_degree: 3, is_core: false },
          { id: 'core', name: 'core', node_type: 'PACKAGE', in_degree: 1, out_degree: 6, is_core: true },
          { id: 'understanding_service', name: 'understanding_service', node_type: 'MODULE', in_degree: 2, out_degree: 0, is_core: false },
          { id: 'global_map', name: 'global_map', node_type: 'MODULE', in_degree: 1, out_degree: 0, is_core: false },
          { id: 'knowledge_graph', name: 'knowledge_graph', node_type: 'MODULE', in_degree: 1, out_degree: 0, is_core: false },
          { id: 'indexer', name: 'indexer', node_type: 'MODULE', in_degree: 1, out_degree: 0, is_core: false },
          { id: 'MainClass', name: 'MainClass', node_type: 'CLASS', in_degree: 3, out_degree: 2, is_core: true },
          { id: 'UtilsClass', name: 'UtilsClass', node_type: 'CLASS', in_degree: 5, out_degree: 0, is_core: false },
          { id: 'func1', name: 'process_data', node_type: 'FUNCTION', in_degree: 2, out_degree: 1, is_core: false },
          { id: 'func2', name: 'analyze_code', node_type: 'FUNCTION', in_degree: 1, out_degree: 2, is_core: false },
          { id: 'func3', name: 'build_graph', node_type: 'FUNCTION', in_degree: 1, out_degree: 0, is_core: false },
        ],
        edges: [
          { source: 'project', target: 'src', edge_type: 'CONTAINS' },
          { source: 'src', target: 'api', edge_type: 'CONTAINS' },
          { source: 'src', target: 'services', edge_type: 'CONTAINS' },
          { source: 'src', target: 'core', edge_type: 'CONTAINS' },
          { source: 'api', target: 'understanding_service', edge_type: 'IMPORTS' },
          { source: 'services', target: 'understanding_service', edge_type: 'CONTAINS' },
          { source: 'core', target: 'global_map', edge_type: 'CONTAINS' },
          { source: 'core', target: 'knowledge_graph', edge_type: 'CONTAINS' },
          { source: 'core', target: 'indexer', edge_type: 'CONTAINS' },
          { source: 'understanding_service', target: 'MainClass', edge_type: 'DEFINES' },
          { source: 'MainClass', target: 'UtilsClass', edge_type: 'USES' },
          { source: 'MainClass', target: 'func1', edge_type: 'CALLS' },
          { source: 'MainClass', target: 'func2', edge_type: 'CALLS' },
          { source: 'func2', target: 'func3', edge_type: 'CALLS' },
          { source: 'knowledge_graph', target: 'func3', edge_type: 'DEFINES' },
        ],
        node_count: 14,
        edge_count: 15,
      };
      setGraphData(demoData);
      toast.warning('使用演示数据（服务未响应）');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (graphData && svgRef.current) {
      renderGraph();
    }
  }, [graphData, layout]);

  const renderGraph = () => {
    if (!graphData || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current?.clientWidth || 800;
    const height = svgRef.current?.clientHeight || 600;

    const g = svg.append('g');

    // 颜色映射
    const colorScale: Record<string, string> = {
      'PROJECT': '#FF6B6B',
      'PACKAGE': '#4ECDC4',
      'MODULE': '#45B7D1',
      'CLASS': '#96CEB4',
      'FUNCTION': '#FFEAA7',
    };

    const nodeColor = (type: string) => colorScale[type] || '#999';

    // 创建力导向模拟
    const simulation = d3.forceSimulation<Node>(graphData.nodes || [])
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('link', d3.forceLink<Node, Edge>(graphData.edges || []).id((d: any) => d.id).distance(100))
      .force('collide', d3.forceCollide().radius(30));

    // 绘制边
    const links = g.append('g')
      .selectAll('line')
      .data(graphData.edges || [])
      .join('line')
      .attr('stroke', '#666')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 1.5);

    // 绘制节点
    const nodes = g.append('g')
      .selectAll('g')
      .data(graphData.nodes || [])
      .join('g')
      .call((drag: any) => drag
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended)
      )
      .on('click', (_, d) => setSelectedNode(d));

    // 节点圆圈
    nodes.append('circle')
      .attr('r', (d) => {
        if (d.node_type === 'PROJECT') return 30;
        if (d.node_type === 'PACKAGE') return 20;
        if (d.node_type === 'MODULE') return 15;
        if (d.node_type === 'CLASS') return 12;
        return 8;
      })
      .attr('fill', (d) => nodeColor(d.node_type))
      .attr('stroke', (d) => d.is_core ? '#4caf50' : '#333')
      .attr('stroke-width', (d) => d.is_core ? 3 : 1);

    // 节点标签
    nodes.append('text')
      .attr('dy', (d) => {
        if (d.node_type === 'PROJECT') return 45;
        if (d.node_type === 'PACKAGE') return 35;
        return 20;
      })
      .attr('text-anchor', 'middle')
      .attr('fill', '#e8ecf1')
      .attr('font-size', '10px')
      .text((d) => d.name.length > 15 ? d.name.substring(0, 12) + '...' : d.name);

    // 更新位置
    simulation.on('tick', () => {
      links
        .attr('x1', (d: any) => (d.source as any).x)
        .attr('y1', (d: any) => (d.source as any).y)
        .attr('x2', (d: any) => (d.target as any).x)
        .attr('y2', (d: any) => (d.target as any).y);

      nodes.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event: any, d: Node) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: Node) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: Node) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  };

  const filteredNodes = (graphData?.nodes || []).filter(node =>
    node.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="h-[calc(100vh-12rem)] flex gap-4">
      {/* 左侧：控制面板 */}
      <div className="w-80 bg-surface border border-border rounded-xl p-4 flex flex-col">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Network className="w-5 h-5 text-accent" />
          知识图谱
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">项目名称</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-sm text-muted mb-1">仓库路径</label>
            <input
              type="text"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-sm text-muted mb-1">布局算法</label>
            <select
              value={layout}
              onChange={(e) => setLayout(e.target.value as any)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-accent"
            >
              <option value="force">力导向布局</option>
              <option value="circular">环形布局</option>
              <option value="dag">有向图布局</option>
            </select>
          </div>

          <button
            onClick={loadGraph}
            disabled={loading}
            className="w-full bg-accent hover:bg-accent/90 text-white rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
          >
            {loading ? '加载中...' : '加载知识图谱'}
          </button>
        </div>

        {/* 图例 */}
        <div className="mt-6 pt-6 border-t border-border">
          <h4 className="text-sm font-medium mb-3">图例</h4>
          <div className="space-y-2 text-sm">
            {[
              { type: 'PROJECT', color: '#FF6B6B', label: '项目' },
              { type: 'PACKAGE', color: '#4ECDC4', label: '包' },
              { type: 'MODULE', color: '#45B7D1', label: '模块' },
              { type: 'CLASS', color: '#96CEB4', label: '类' },
              { type: 'FUNCTION', color: '#FFEAA7', label: '函数' },
            ].map((item) => (
              <div key={item.type} className="flex items-center gap-2">
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-muted">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 搜索节点 */}
        {graphData && (
          <div className="mt-6 pt-6 border-t border-border">
            <div className="relative mb-3">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索节点..."
                className="w-full bg-background border border-border rounded-lg pl-8 pr-3 py-2 text-sm focus:border-accent"
              />
            </div>
            <div className="max-h-32 overflow-auto space-y-1">
              {filteredNodes.slice(0, 10).map((node) => (
                <button
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className="w-full text-left px-2 py-1 rounded hover:bg-card text-sm truncate"
                >
                  {node.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 右侧：图谱可视化 */}
      <div className="flex-1 bg-surface border border-border rounded-xl flex flex-col">
        {graphData ? (
          <>
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted">节点：<span className="text-text font-medium">{graphData.node_count}</span></span>
                <span className="text-muted">边：<span className="text-text font-medium">{graphData.edge_count}</span></span>
              </div>
              <div className="flex gap-2">
                <button className="p-2 hover:bg-card rounded-lg transition-colors" title="放大">
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button className="p-2 hover:bg-card rounded-lg transition-colors" title="缩小">
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button className="p-2 hover:bg-card rounded-lg transition-colors" title="适应屏幕">
                  <Maximize className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 relative">
              <svg ref={svgRef} className="w-full h-full" />
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted">
            <Network className="w-16 h-16 mb-4 opacity-50" />
            <p>点击"加载知识图谱"开始</p>
          </div>
        )}

        {/* 节点详情面板 */}
        {selectedNode && (
          <div className="absolute bottom-4 right-4 w-80 bg-card border border-border rounded-xl p-4 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold">{selectedNode.name}</h4>
              <button onClick={() => setSelectedNode(null)} className="text-muted hover:text-text">
                <XIcon className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted">类型</span>
                <span>{selectedNode.node_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">入度</span>
                <span>{selectedNode.in_degree}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">出度</span>
                <span>{selectedNode.out_degree}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">核心节点</span>
                <span>{selectedNode.is_core ? '是' : '否'}</span>
              </div>
              {selectedNode.file_path && (
                <div className="pt-2 border-t border-border">
                  <span className="text-muted text-xs">文件：</span>
                  <span className="text-xs font-mono">{selectedNode.file_path}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// 简单的 X 图标组件
const XIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export default KnowledgeGraph;
