/**
 * 监控中心页面
 */
import React, { useEffect, useState } from 'react'
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Statistic,
  Badge,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
} from 'antd'
const { TextArea } = Input
import {
  PlusOutlined,
  EditOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { monitoringService } from '../services/monitoringService'
import type { AlertRule, Alert, SystemHealth } from '../types'

const { Title } = Typography

const MonitoringPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [alertRules, setAlertRules] = useState<AlertRule[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadMonitoringData()
  }, [])

  const loadMonitoringData = async () => {
    setLoading(true)
    try {
      // 加载系统健康状态
      const health = await monitoringService.getSystemHealth()
      setSystemHealth(health)

      // 加载告警规则
      const rules = await monitoringService.getAlertRules()
      setAlertRules(rules)

      // 加载告警记录
      const alertsData = await monitoringService.getAlerts({ limit: 20 })
      setAlerts(alertsData)
    } catch (error) {
      console.error('Failed to load monitoring data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateRule = async (values: any) => {
    try {
      if (editingRule) {
        await monitoringService.updateAlertRule(editingRule.id, values)
        message.success('告警规则更新成功')
      } else {
        await monitoringService.createAlertRule(values)
        message.success('告警规则创建成功')
      }
      setIsRuleModalOpen(false)
      form.resetFields()
      setEditingRule(null)
      loadMonitoringData()
    } catch (error: any) {
      message.error(`操作失败：${error.message}`)
    }
  }

  const handleEditRule = (rule: AlertRule) => {
    setEditingRule(rule)
    form.setFieldsValue({
      name: rule.name,
      description: rule.description,
      metric_name: rule.metric_name,
      operator: rule.operator,
      threshold: rule.threshold,
      severity: rule.severity,
    })
    setIsRuleModalOpen(true)
  }

  const handleToggleRule = async (rule: AlertRule) => {
    try {
      await monitoringService.updateAlertRule(rule.id, { enabled: !rule.enabled })
      message.success(rule.enabled ? '告警规则已禁用' : '告警规则已启用')
      loadMonitoringData()
    } catch (error: any) {
      message.error(`操作失败：${error.message}`)
    }
  }

  const handleSilenceRule = async (rule: AlertRule) => {
    try {
      await monitoringService.silenceAlertRule(rule.id, 60)
      message.success('告警规则已静默 60 分钟')
      loadMonitoringData()
    } catch (error: any) {
      message.error(`操作失败：${error.message}`)
    }
  }

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await monitoringService.acknowledgeAlert(alertId, 'current_user')
      message.success('告警已确认')
      loadMonitoringData()
    } catch (error: any) {
      message.error(`操作失败：${error.message}`)
    }
  }

  // 告警规则表格列
  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '指标',
      dataIndex: 'metric_name',
      key: 'metric_name',
    },
    {
      title: '条件',
      key: 'condition',
      render: (_: any, record: AlertRule) => (
        <code>
          {record.metric_name} {record.operator} {record.threshold}
        </code>
      ),
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
      title: '状态',
      key: 'status',
      render: (_: any, record: AlertRule) => (
        <Space>
          <Badge status={record.enabled ? 'success' : 'default'} text={record.enabled ? '已启用' : '已禁用'} />
          {record.silenced && <Tag>静默中</Tag>}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: AlertRule) => (
        <Space>
          <Button
            size="small"
            icon={record.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => handleToggleRule(record)}
          >
            {record.enabled ? '禁用' : '启用'}
          </Button>
          <Button size="small" onClick={() => handleSilenceRule(record)}>
            静默
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEditRule(record)}>
            编辑
          </Button>
        </Space>
      ),
    },
  ]

  // 告警记录表格列
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          firing: { text: '触发中', color: 'red' },
          acknowledged: { text: '已确认', color: 'blue' },
          resolved: { text: '已恢复', color: 'green' },
        }
        const s = statusMap[status] || { text: status, color: 'default' }
        return <Tag color={s.color}>{s.text}</Tag>
      },
    },
    {
      title: '当前值 / 阈值',
      key: 'values',
      render: (_: any, record: Alert) => (
        <span>
          {record.metric_value?.toFixed(2)} / {record.threshold?.toFixed(2)}
        </span>
      ),
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Alert) =>
        record.status === 'firing' ? (
          <Button size="small" onClick={() => handleAcknowledgeAlert(record.id)}>
            确认
          </Button>
        ) : null,
    },
  ]

  // 系统健康状态卡片
  const renderHealthStatus = () => {
    if (!systemHealth) return null

    return (
      <Card
        title="系统健康状态"
        bordered={false}
        className="mb-6"
      >
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Badge
              status={systemHealth.status === 'healthy' ? 'success' : systemHealth.status === 'degraded' ? 'warning' : 'error'}
              text={
                <span style={{ fontSize: 18, fontWeight: 600 }}>
                  {systemHealth.status === 'healthy' ? '健康' : systemHealth.status === 'degraded' ? '降级' : '异常'}
                </span>
              }
            />
          </Col>
          <Col flex="auto">
            <Row gutter={[16, 16]}>
              <Col>
                <Statistic
                  title="活跃连接"
                  value={systemHealth.active_connections}
                  suffix={`/ ${systemHealth.max_connections}`}
                />
              </Col>
              <Col>
                <Statistic
                  title="当前 QPS"
                  value={systemHealth.current_qps}
                  precision={2}
                />
              </Col>
              <Col>
                <Statistic
                  title="并发查询"
                  value={systemHealth.current_concurrent}
                />
              </Col>
              <Col>
                <Statistic
                  title="血缘节点"
                  value={systemHealth.total_lineage_nodes}
                />
              </Col>
            </Row>
          </Col>
        </Row>
      </Card>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={2} style={{ margin: 0 }}>
          监控中心
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingRule(null)
            form.resetFields()
            setIsRuleModalOpen(true)
          }}
        >
          新建告警规则
        </Button>
      </div>

      {renderHealthStatus()}

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="告警规则">
            <Table
              columns={ruleColumns}
              dataSource={alertRules}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              size="small"
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="告警记录">
            <Table
              columns={alertColumns}
              dataSource={alerts}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              size="small"
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      {/* 新建/编辑告警规则模态框 */}
      <Modal
        title={editingRule ? '编辑告警规则' : '新建告警规则'}
        open={isRuleModalOpen}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsRuleModalOpen(false)
          form.resetFields()
          setEditingRule(null)
        }}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateRule}
        >
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="例如：CPU 使用率过高" />
          </Form.Item>

          <Form.Item
            name="description"
            label="规则描述"
          >
            <TextArea rows={2} placeholder="描述此告警规则的作用" />
          </Form.Item>

          <Form.Item
            name="metric_name"
            label="监控指标"
            rules={[{ required: true, message: '请选择监控指标' }]}
          >
            <Select placeholder="选择指标">
              <Select.Option value="cpu_usage">CPU 使用率</Select.Option>
              <Select.Option value="memory_usage">内存使用率</Select.Option>
              <Select.Option value="query_latency">查询延迟</Select.Option>
              <Select.Option value="error_rate">错误率</Select.Option>
              <Select.Option value="active_connections">活跃连接数</Select.Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="operator"
                label="操作符"
                rules={[{ required: true, message: '请选择操作符' }]}
              >
                <Select>
                  <Select.Option value=">">&gt;</Select.Option>
                  <Select.Option value="<">&lt;</Select.Option>
                  <Select.Option value=">=">&gt;=</Select.Option>
                  <Select.Option value="<=">&lt;=</Select.Option>
                  <Select.Option value="==">==</Select.Option>
                  <Select.Option value="!=">!=</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="threshold"
                label="阈值"
                rules={[{ required: true, message: '请输入阈值' }]}
              >
                <InputNumber style={{ width: '100%' }} placeholder="100" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="severity"
            label="告警级别"
            initialValue="warning"
          >
            <Select>
              <Select.Option value="critical">紧急 (Critical)</Select.Option>
              <Select.Option value="warning">警告 (Warning)</Select.Option>
              <Select.Option value="info">提示 (Info)</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default MonitoringPage
