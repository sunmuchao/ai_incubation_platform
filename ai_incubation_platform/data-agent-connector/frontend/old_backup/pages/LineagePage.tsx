/**
 * 血缘图谱页面 - 使用 React Flow 可视化
 */
import React, { useEffect, useState, useCallback } from 'react'
import {
  Card,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Tag,
  Drawer,
  Descriptions,
  Tabs,
  Spin,
  Empty,
  Alert,
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  NodeIndexOutlined,
  ApiOutlined,
} from '@ant-design/icons'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { lineageService } from '../services/lineageService'
import { connectorService } from '../services/connectorService'
import type { LineageNode, LineageGraph, DataSource } from '../types'

const { Title, Text } = Typography
const { TabPane } = Tabs

// 自定义节点样式
const nodeColors: Record<string, string> = {
  table: '#1890ff',
  column: '#52c41a',
  view: '#722ed1',
  query: '#fa8c16',
}

const nodeLabels: Record<string, string> = {
  table: '表',
  column: '列',
  view: '视图',
  query: '查询',
}

// 将血缘节点转换为 React Flow 节点
const convertToFlowNodes = (nodes: LineageNode[]): Node[] => {
  return nodes.map((node, index) => ({
    id: node.id,
    type: 'default',
    position: {
      x: (index % 5) * 250,
      y: Math.floor(index / 5) * 150,
    },
    data: {
      label: (
        <div
          className="px-3 py-2 rounded-lg border-2 shadow-sm"
          style={{
            borderColor: nodeColors[node.type] || '#1890ff',
            background: '#fff',
            minWidth: 180,
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <div
              className="w-3 h-3 rounded-full"
              style={{ background: nodeColors[node.type] || '#1890ff' }}
            />
            <strong className="text-sm">{node.name}</strong>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Tag color={nodeColors[node.type] || 'blue'} style={{ margin: 0 }}>
              {nodeLabels[node.type] || node.type}
            </Tag>
            <span>{node.datasource}</span>
          </div>
        </div>
      ),
      node,
    },
    style: { padding: 0, background: 'transparent', border: 'none' },
  }))
}

// 将血缘边转换为 React Flow 边
const convertToFlowEdges = (edges: any[]): Edge[] => {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source_id,
    target: edge.target_id,
    label: edge.operation || 'transforms',
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    labelStyle: { fill: '#64748b', fontWeight: 500, fontSize: 10 },
    arrowHeadType: 'arrowclosed',
  }))
}

const LineagePage: React.FC = () => {
  const [connectors, setConnectors] = useState<DataSource[]>([])
  const [selectedDatasource, setSelectedDatasource] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [graphData, setGraphData] = useState<LineageGraph | null>(null)
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null)
  const [nodeDrawerOpen, setNodeDrawerOpen] = useState(false)
  const [impactAnalysis, setImpactAnalysis] = useState<any>(null)
  const [upstreamAnalysis, setUpstreamAnalysis] = useState<any>(null)

  // React Flow 状态
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  useEffect(() => {
    loadConnectors()
  }, [])

  const loadConnectors = async () => {
    try {
      const data = await connectorService.getActiveConnectors()
      setConnectors(data)
      if (data.length > 0) {
        setSelectedDatasource(data[0].datasource_name)
        loadFullGraph(data[0].datasource_name)
      }
    } catch (error) {
      console.error('Failed to load connectors:', error)
    }
  }

  const loadFullGraph = async (datasource?: string) => {
    setLoading(true)
    try {
      const graph = await lineageService.getFullLineageGraph(datasource)
      setGraphData(graph)
      setNodes(convertToFlowNodes(graph.nodes || []))
      setEdges(convertToFlowEdges(graph.edges || []))
    } catch (error) {
      console.error('Failed to load lineage graph:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDatasourceChange = (value: string) => {
    setSelectedDatasource(value)
    loadFullGraph(value)
  }

  const handleSearch = () => {
    if (!searchTerm) return
    // 在节点中搜索
    const matchingNode = graphData?.nodes.find(
      (n) =>
        n.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        n.datasource.toLowerCase().includes(searchTerm.toLowerCase())
    )
    if (matchingNode) {
      handleNodeClick({} as React.MouseEvent, { data: { node: matchingNode } })
    }
  }

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: any) => {
    const lineageNode = node.data.node as LineageNode
    setSelectedNode(lineageNode)
    setNodeDrawerOpen(true)
    loadNodeAnalysis(lineageNode.id)
  }, [])

  const loadNodeAnalysis = async (nodeId: string) => {
    try {
      const [impact, upstream] = await Promise.all([
        lineageService.analyzeImpact(nodeId),
        lineageService.analyzeLineage(nodeId),
      ])
      setImpactAnalysis(impact)
      setUpstreamAnalysis(upstream)
    } catch (error) {
      console.error('Failed to load node analysis:', error)
    }
  }

  const handleRefresh = () => {
    loadFullGraph(selectedDatasource)
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={2} style={{ margin: 0 }}>
          血缘图谱
        </Title>
        <Space>
          <Input
            placeholder="搜索节点..."
            prefix={<SearchOutlined />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 250 }}
          />
          <Select
            value={selectedDatasource}
            onChange={handleDatasourceChange}
            style={{ width: 200 }}
            options={connectors.map((c) => ({ label: c.datasource_name, value: c.datasource_name }))}
          />
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
        </Space>
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center items-center h-96">
            <Spin size="large" tip="加载血缘图中..." />
          </div>
        ) : graphData && graphData.nodes?.length > 0 ? (
          <div style={{ height: '70vh' }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={handleNodeClick}
              fitView
              attributionPosition="bottom-left"
            >
              <Background color="#aaa" gap={16} />
              <Controls />
              <MiniMap
                nodeColor={(node) => {
                  const n = graphData.nodes.find((n) => n.id === node.id)
                  return nodeColors[n?.type || 'table']
                }}
                zoomable
                pannable
              />
            </ReactFlow>
          </div>
        ) : (
          <Empty
            description="暂无血缘数据"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </Card>

      {/* 图例 */}
      <Card title="图例" size="small" className="mt-4">
        <Space>
          {Object.entries(nodeColors).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div className="w-4 h-4 rounded" style={{ background: color }} />
              <Text>{nodeLabels[type] || type}</Text>
            </div>
          ))}
        </Space>
      </Card>

      {/* 节点详情抽屉 */}
      <Drawer
        title={selectedNode?.name || '节点详情'}
        placement="right"
        width={500}
        open={nodeDrawerOpen}
        onClose={() => setNodeDrawerOpen(false)}
      >
        {selectedNode && (
          <>
            <Descriptions title="基本信息" bordered column={1} size="small">
              <Descriptions.Item label="节点 ID">{selectedNode.id}</Descriptions.Item>
              <Descriptions.Item label="节点类型">
                <Tag color={nodeColors[selectedNode.type]}>{nodeLabels[selectedNode.type]}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="数据源">{selectedNode.datasource}</Descriptions.Item>
              {selectedNode.schema_name && (
                <Descriptions.Item label="Schema">{selectedNode.schema_name}</Descriptions.Item>
              )}
              {selectedNode.table_name && (
                <Descriptions.Item label="表名">{selectedNode.table_name}</Descriptions.Item>
              )}
            </Descriptions>

            <Tabs defaultActiveKey="impact" className="mt-4">
              <TabPane
                tab={
                  <span>
                    <ApiOutlined />
                    下游影响 ({impactAnalysis?.impact_count || 0})
                  </span>
                }
                key="impact"
              >
                {impactAnalysis?.impacted_nodes?.length > 0 ? (
                  <ul className="space-y-2">
                    {impactAnalysis.impacted_nodes.map((node: any, index: number) => (
                      <li key={index} className="flex items-center gap-2 text-sm">
                        <Tag color={nodeColors[node.type]}>{nodeLabels[node.type]}</Tag>
                        <Text>{node.name}</Text>
                        <Text type="secondary" className="text-xs">
                          深度：{node.depth}
                        </Text>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Alert message="无下游影响" type="info" showIcon />
                )}
              </TabPane>
              <TabPane
                tab={
                  <span>
                    <NodeIndexOutlined />
                    上游来源 ({upstreamAnalysis?.source_count || 0})
                  </span>
                }
                key="upstream"
              >
                {upstreamAnalysis?.source_nodes?.length > 0 ? (
                  <ul className="space-y-2">
                    {upstreamAnalysis.source_nodes.map((node: any, index: number) => (
                      <li key={index} className="flex items-center gap-2 text-sm">
                        <Tag color={nodeColors[node.type]}>{nodeLabels[node.type]}</Tag>
                        <Text>{node.name}</Text>
                        <Text type="secondary" className="text-xs">
                          深度：{node.depth}
                        </Text>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Alert message="无上游来源" type="info" showIcon />
                )}
              </TabPane>
            </Tabs>
          </>
        )}
      </Drawer>
    </div>
  )
}

export default LineagePage
