/**
 * Lineage Graph 组件 - 数据血缘关系可视化
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Card, Spin, Alert, Space, Typography, Tag, Button, Select, Slider } from 'antd'
import {
  DatabaseOutlined,
  TableOutlined,
  FieldStringOutlined,
  ApiOutlined,
  FullscreenOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from '@ant-design/icons'
import { lineageService } from '../services/lineageService'

const { Title, Text } = Typography
const { Option } = Select

// 节点类型图标
const NODE_ICONS: Record<string, React.ReactNode> = {
  table: <TableOutlined />,
  column: <FieldStringOutlined />,
  view: <DatabaseOutlined />,
  query: <ApiOutlined />,
  datasource: <DatabaseOutlined />,
}

// 节点类型颜色
const NODE_COLORS: Record<string, string> = {
  table: '#1890ff',
  column: '#52c41a',
  view: '#722ed1',
  query: '#fa8c16',
  datasource: '#eb2f96',
}

// 边类型颜色
const EDGE_COLORS: Record<string, string> = {
  transform: '#1890ff',
  join: '#52c41a',
  filter: '#fa8c16',
  aggregate: '#722ed1',
  default: '#8c8c8c',
}

interface LineageNode {
  id: string
  name: string
  type: string
  datasource: string
  schema_name?: string
  table_name?: string
  column_name?: string
  metadata?: Record<string, any>
  x?: number
  y?: number
}

interface LineageEdge {
  id: string
  source_id: string
  target_id: string
  operation: string
  metadata?: Record<string, any>
}

interface LineageGraphProps {
  nodeId?: string
  initialDirection?: 'upstream' | 'downstream' | 'both'
  initialDepth?: number
}

/**
 * 简化的血缘图组件（使用 SVG 渲染）
 */
export const LineageGraph: React.FC<LineageGraphProps> = ({
  nodeId,
  initialDirection = 'both',
  initialDepth = 3,
}) => {
  const [loading, setLoading] = useState(false)
  const [nodes, setNodes] = useState<LineageNode[]>([])
  const [edges, setEdges] = useState<LineageEdge[]>([])
  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>(initialDirection)
  const [depth, setDepth] = useState(initialDepth)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  // 加载血缘数据
  const loadLineage = useCallback(async () => {
    if (!nodeId) return

    setLoading(true)
    setError(null)

    try {
      const graph = await lineageService.getLineageGraph(nodeId, { direction, depth })
      setNodes(graph.nodes || [])
      setEdges(graph.edges || [])

      // 计算节点位置（简单的力导向布局模拟）
      calculateNodePositions(graph.nodes || [])
    } catch (err: any) {
      setError(err.message || '加载血缘关系失败')
    } finally {
      setLoading(false)
    }
  }, [nodeId, direction, depth])

  // 计算节点位置
  const calculateNodePositions = (graphNodes: LineageNode[]) => {
    if (graphNodes.length === 0) return

    const centerX = 400
    const centerY = 300
    const radiusX = 250
    const radiusY = 150

    const positionedNodes = graphNodes.map((node, index) => {
      const angle = (2 * Math.PI * index) / graphNodes.length
      return {
        ...node,
        x: centerX + radiusX * Math.cos(angle),
        y: centerY + radiusY * Math.sin(angle),
      }
    })

    setNodes(positionedNodes)
  }

  // 初始化加载
  useEffect(() => {
    if (nodeId) {
      loadLineage()
    }
  }, [nodeId, direction, depth])

  // 处理画布拖拽
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true)
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y })
  }

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return
    setOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    })
  }

  const handleCanvasMouseUp = () => {
    setIsDragging(false)
  }

  // 渲染节点
  const renderNode = (node: LineageNode) => {
    const isSelected = selectedNode?.id === node.id
    const color = NODE_COLORS[node.type] || NODE_COLORS.default
    const icon = NODE_ICONS[node.type] || <DatabaseOutlined />
    const nodeX = node.x || 0
    const nodeY = node.y || 0

    return (
      <g
        key={node.id}
        transform={`translate(${nodeX}, ${nodeY})`}
        onClick={(e) => {
          e.stopPropagation()
          setSelectedNode(node)
        }}
        className="cursor-pointer"
      >
        {/* 节点背景 */}
        <rect
          x="-60"
          y="-30"
          width="120"
          height="60"
          rx="8"
          fill={isSelected ? `${color}20` : 'white'}
          stroke={color}
          strokeWidth={isSelected ? 3 : 2}
          className="transition-all duration-200"
        />

        {/* 节点图标 */}
        <foreignObject x="-20" y="-20" width="40" height="40">
          <div style={{ color, fontSize: 24, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            {icon}
          </div>
        </foreignObject>

        {/* 节点名称 */}
        <text
          x="30"
          y="-5"
          fill="#333"
          fontSize="12"
          fontWeight="bold"
          textLength="80"
          overflow="hidden"
        >
          {node.name.length > 15 ? node.name.substring(0, 15) + '...' : node.name}
        </text>

        {/* 节点类型 */}
        <text
          x="30"
          y="15"
          fill="#666"
          fontSize="10"
        >
          {node.type}
        </text>
      </g>
    )
  }

  // 渲染边
  const renderEdge = (edge: LineageEdge) => {
    const sourceNode = nodes.find(n => n.id === edge.source_id)
    const targetNode = nodes.find(n => n.id === edge.target_id)

    if (!sourceNode || !targetNode) return null

    const color = EDGE_COLORS[edge.operation] || EDGE_COLORS.default
    const sourceX = sourceNode.x || 0
    const sourceY = sourceNode.y || 0
    const targetX = targetNode.x || 0
    const targetY = targetNode.y || 0

    return (
      <g key={edge.id}>
        <line
          x1={sourceX}
          y1={sourceY}
          x2={targetX}
          y2={targetY}
          stroke={color}
          strokeWidth="2"
          markerEnd="url(#arrowhead)"
          opacity="0.6"
        />
        {/* 边标签 */}
        <text
          x={(sourceX + targetX) / 2}
          y={(sourceY + targetY) / 2 - 5}
          fill={color}
          fontSize="10"
          textAnchor="middle"
        >
          {edge.operation}
        </text>
      </g>
    )
  }

  // 渲染节点详情
  const renderNodeDetail = () => {
    if (!selectedNode) return null

    return (
      <div className="absolute top-4 right-4 w-72 z-10">
        <Card
          title="节点详情"
          size="small"
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>ID:</Text> {selectedNode.id}
            </div>
            <div>
              <Text strong>名称:</Text> {selectedNode.name}
            </div>
            <div>
              <Text strong>类型:</Text> <Tag color={NODE_COLORS[selectedNode.type]}>{selectedNode.type}</Tag>
            </div>
            <div>
              <Text strong>数据源:</Text> {selectedNode.datasource}
            </div>
            {selectedNode.table_name && (
              <div>
                <Text strong>表名:</Text> {selectedNode.table_name}
              </div>
            )}
            {selectedNode.column_name && (
              <div>
                <Text strong>列名:</Text> {selectedNode.column_name}
              </div>
            )}
            {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
              <div>
                <Text strong>元数据:</Text>
                <pre className="text-xs bg-gray-100 p-2 rounded mt-1 max-h-32 overflow-auto">
                  {JSON.stringify(selectedNode.metadata, null, 2)}
                </pre>
              </div>
            )}
          </Space>
        </Card>
      </div>
    )
  }

  // 统计信息
  const statistics = useMemo(() => ({
    totalNodes: nodes.length,
    totalEdges: edges.length,
    nodeTypes: nodes.reduce((acc, node) => {
      acc[node.type] = (acc[node.type] || 0) + 1
      return acc
    }, {} as Record<string, number>),
  }), [nodes, edges])

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between p-4 bg-white border-b">
        <div className="flex items-center space-x-4">
          <Title level={4} style={{ margin: 0 }}>血缘关系图</Title>
          <Space>
            <Select
              value={direction}
              onChange={(value) => setDirection(value)}
              style={{ width: 120 }}
            >
              <Option value="upstream">上游</Option>
              <Option value="downstream">下游</Option>
              <Option value="both">双向</Option>
            </Select>
            <span className="text-sm text-gray-500">深度:</span>
            <Slider
              value={depth}
              onChange={(value) => setDepth(value)}
              min={1}
              max={10}
              style={{ width: 100 }}
            />
          </Space>
        </div>
        <div className="flex items-center space-x-2">
          <Button icon={<ZoomOutOutlined />} onClick={() => setZoom(Math.max(0.5, zoom - 0.1))} />
          <span className="text-sm">{(zoom * 100).toFixed(0)}%</span>
          <Button icon={<ZoomInOutlined />} onClick={() => setZoom(Math.min(2, zoom + 0.1))} />
          <Button icon={<FullscreenOutlined />} onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }) }} />
        </div>
      </div>

      {/* 统计信息 */}
      <div className="flex items-center space-x-4 p-2 bg-gray-50 border-b">
        <Tag color="blue">节点：{statistics.totalNodes}</Tag>
        <Tag color="green">关系：{statistics.totalEdges}</Tag>
        {Object.entries(statistics.nodeTypes).map(([type, count]) => (
          <Tag key={type} color={NODE_COLORS[type]}>{type}: {count}</Tag>
        ))}
      </div>

      {/* 画布区域 */}
      <div className="flex-1 relative overflow-hidden bg-gray-100">
        {loading ? (
          <div className="flex justify-center items-center h-full">
            <Spin size="large" tip="加载血缘关系..." />
          </div>
        ) : error ? (
          <div className="flex justify-center items-center h-full">
            <Alert message={error} type="error" showIcon />
          </div>
        ) : nodes.length === 0 ? (
          <div className="flex justify-center items-center h-full">
            <Alert message="暂无血缘关系数据" type="info" showIcon />
          </div>
        ) : (
          <div
            className="w-full h-full cursor-grab active:cursor-grabbing"
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
            onMouseLeave={handleCanvasMouseUp}
          >
            <svg
              className="w-full h-full"
              viewBox={`0 0 800 600`}
              style={{ transform: `scale(${zoom}) translate(${offset.x}px, ${offset.y}px)` }}
            >
              {/* 定义箭头 */}
              <defs>
                <marker
                  id="arrowhead"
                  markerWidth="10"
                  markerHeight="7"
                  refX="9"
                  refY="3.5"
                  orient="auto"
                >
                  <polygon points="0 0, 10 3.5, 0 7" fill="#8c8c8c" />
                </marker>
              </defs>

              {/* 网格背景 */}
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e0e0e0" strokeWidth="0.5" />
              </pattern>
              <rect width="100%" height="100%" fill="url(#grid)" />

              {/* 渲染边 */}
              {edges.map(renderEdge)}

              {/* 渲染节点 */}
              {nodes.map(renderNode)}
            </svg>
          </div>
        )}

        {/* 节点详情面板 */}
        {renderNodeDetail()}
      </div>

      {/* 图例 */}
      <div className="p-2 bg-white border-t">
        <Space size="large">
          <Text type="secondary" style={{ fontSize: 12 }}>图例:</Text>
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center space-x-1">
              <div
                style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: color }}
              />
              <Text style={{ fontSize: 12 }}>{type}</Text>
            </div>
          ))}
        </Space>
      </div>
    </div>
  )
}

export default LineageGraph
