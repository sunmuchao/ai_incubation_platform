/**
 * 仪表盘首页
 */
import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Progress, Table, Tag, Typography } from 'antd'
import {
  DatabaseOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined,
  ArrowUpOutlined,
} from '@ant-design/icons'
import { connectorService } from '../services/connectorService'
import { monitoringService } from '../services/monitoringService'
import { governanceService } from '../services/governanceService'
import type { DataSource, Alert } from '../types'

const { Title } = Typography

// 仪表盘统计数据
interface DashboardStats {
  total_datasources: number
  active_connectors: number
  total_queries_24h: number
  avg_query_latency_ms: number
  governance_score: number
  active_alerts: number
}

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<DashboardStats>({
    total_datasources: 0,
    active_connectors: 0,
    total_queries_24h: 0,
    avg_query_latency_ms: 0,
    governance_score: 0,
    active_alerts: 0,
  })
  const [connectors, setConnectors] = useState<DataSource[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [governanceData, setGovernanceData] = useState<any>(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setLoading(true)
    try {
      // 加载连接器数据
      const connectorsData = await connectorService.getActiveConnectors()
      setConnectors(connectorsData)
      setStats((prev) => ({
        ...prev,
        total_datasources: connectorsData.length,
        active_connectors: connectorsData.filter((c) => c.status === 'connected').length,
      }))

      // 加载监控数据
      const dashboardData = await monitoringService.getDashboard()
      if (dashboardData) {
        setStats((prev) => ({
          ...prev,
          total_queries_24h: dashboardData.total_queries_24h || 0,
          avg_query_latency_ms: dashboardData.avg_query_latency_ms || 0,
        }))
      }

      // 加载告警数据
      const activeAlerts = await monitoringService.getAlerts({ status: 'firing', limit: 5 })
      setAlerts(activeAlerts)
      setStats((prev) => ({ ...prev, active_alerts: activeAlerts.length }))

      // 加载治理分数
      const score = await governanceService.getGovernanceScore()
      setStats((prev) => ({ ...prev, governance_score: score.overall_score || 0 }))
      setGovernanceData(score)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  // 连接器状态表格列
  const connectorColumns = [
    {
      title: '连接器名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'connector_type',
      key: 'connector_type',
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '数据源',
      dataIndex: 'datasource_name',
      key: 'datasource_name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          connected: 'green',
          disconnected: 'default',
          error: 'red',
        }
        const statusMap: Record<string, string> = {
          connected: '已连接',
          disconnected: '未连接',
          error: '异常',
        }
        return <Tag color={colorMap[status] || 'default'}>{statusMap[status] || status}</Tag>
      },
    },
  ]

  // 告警表格列
  const alertColumns = [
    {
      title: '告警名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const colorMap: Record<string, string> = {
          critical: 'red',
          warning: 'orange',
          info: 'blue',
        }
        return <Tag color={colorMap[severity] || 'default'}>{severity}</Tag>
      },
    },
    {
      title: '当前值',
      dataIndex: 'metric_value',
      key: 'metric_value',
      render: (value: number) => value?.toFixed(2),
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      render: (value: number) => value?.toFixed(2),
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (time: string) => new Date(time).toLocaleString(),
    },
  ]

  return (
    <div>
      <Title level={2} style={{ marginBottom: 24 }}>
        数据网关 Dashboard
      </Title>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="数据源"
              value={stats.total_datasources}
              prefix={<DatabaseOutlined />}
              suffix={
                <span className="text-green-500 text-sm">
                  {stats.active_connectors} 活跃 <ArrowUpOutlined />
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="24h 查询量"
              value={stats.total_queries_24h}
              prefix={<ApiOutlined />}
              suffix={<span className="text-green-500 text-sm">+12% <ArrowUpOutlined /></span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均延迟"
              value={stats.avg_query_latency_ms}
              precision={0}
              suffix="ms"
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: stats.avg_query_latency_ms < 100 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="治理分数"
              value={stats.governance_score}
              precision={1}
              suffix="%"
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: stats.governance_score >= 80 ? '#3f8600' : '#faad14' }}
            />
            <Progress
              percent={stats.governance_score}
              showInfo={false}
              strokeColor={
                stats.governance_score >= 80 ? '#52c41a' : stats.governance_score >= 60 ? '#faad14' : '#ff4d4f'
              }
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 治理详情 */}
      {governanceData && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="数据治理详情">
              <Row gutter={[16, 16]}>
                <Col span={6}>
                  <Statistic
                    title="分类覆盖率"
                    value={governanceData.classification_coverage || 0}
                    precision={1}
                    suffix="%"
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="敏感数据覆盖率"
                    value={governanceData.sensitivity_coverage || 0}
                    precision={1}
                    suffix="%"
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="脱敏覆盖率"
                    value={governanceData.masking_coverage || 0}
                    precision={1}
                    suffix="%"
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="血缘覆盖率"
                    value={governanceData.lineage_coverage || 0}
                    precision={1}
                    suffix="%"
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      )}

      {/* 连接器和告警 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title="连接器状态"
            extra={<a onClick={() => window.location.href = '/connectors'}>查看更多</a>}
          >
            <Table
              columns={connectorColumns}
              dataSource={connectors.slice(0, 5)}
              rowKey="name"
              pagination={false}
              size="small"
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={`活动告警 (${alerts.length})`}
            extra={<a onClick={() => window.location.href = '/monitoring/alerts'}>查看更多</a>}
          >
            <Table
              columns={alertColumns}
              dataSource={alerts}
              rowKey="id"
              pagination={false}
              size="small"
              loading={loading}
              locale={{ emptyText: '暂无活动告警' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
