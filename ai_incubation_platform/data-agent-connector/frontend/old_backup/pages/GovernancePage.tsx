/**
 * 数据治理页面
 */
import React, { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Progress,
  Row,
  Col,
  Statistic,
  Button,
  Select,
  Space,
  Typography,
  Tree,
  Modal,
  Form,
  message,
  Tabs,
  Badge,
} from 'antd'
import {
  SafetyCertificateOutlined,
  TagsOutlined,
  EyeInvisibleOutlined,
  BlockOutlined,
  PlusOutlined,
  ScanOutlined,
} from '@ant-design/icons'
import { governanceService } from '../services/governanceService'
import { connectorService } from '../services/connectorService'
import type {
  Classification,
  DataLabel,
  SensitiveRecord,
  MaskingPolicy,
  GovernanceScore,
  DataSource,
} from '../types'

const { Title } = Typography
const { TabPane } = Tabs
const { DirectoryTree } = Tree

// 敏感级别颜色映射
const sensitivityColors: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'blue',
}

const sensitivityLabels: Record<string, string> = {
  high: '高敏感',
  medium: '中敏感',
  low: '低敏感',
}

// 脱敏类型映射
const maskingTypeLabels: Record<string, string> = {
  full: '完全掩码',
  partial: '部分掩码',
  hash: '哈希',
  encrypt: '加密',
  redact: '隐藏',
}

const GovernancePage: React.FC = () => {
  // 状态管理
  const [loading, setLoading] = useState(false)
  const [connectors, setConnectors] = useState<DataSource[]>([])
  const [selectedDatasource, setSelectedDatasource] = useState<string>('')

  // 治理分数
  const [governanceScore, setGovernanceScore] = useState<GovernanceScore | null>(null)

  // 分类树
  const [classificationTree, setClassificationTree] = useState<Classification[]>([])
  const [isClassModalOpen, setIsClassModalOpen] = useState(false)

  // 标签
  const [labels, setLabels] = useState<DataLabel[]>([])

  // 敏感数据
  const [sensitiveRecords, setSensitiveRecords] = useState<SensitiveRecord[]>([])
  const [scanLoading, setScanLoading] = useState(false)

  // 脱敏策略
  const [maskingPolicies, setMaskingPolicies] = useState<MaskingPolicy[]>([])
  const [isPolicyModalOpen, setIsPolicyModalOpen] = useState(false)

  useEffect(() => {
    loadConnectors()
    loadGovernanceData()
  }, [])

  const loadConnectors = async () => {
    try {
      const data = await connectorService.getActiveConnectors()
      setConnectors(data)
      if (data.length > 0) {
        setSelectedDatasource(data[0].datasource_name)
      }
    } catch (error) {
      console.error('Failed to load connectors:', error)
    }
  }

  const loadGovernanceData = async () => {
    setLoading(true)
    try {
      // 加载治理分数
      const score = await governanceService.getGovernanceScore()
      setGovernanceScore(score)

      // 加载分类树
      const tree = await governanceService.getClassificationTree()
      setClassificationTree(tree)

      // 加载标签
      const labelsData = await governanceService.getLabels()
      setLabels(labelsData)

      // 加载敏感记录
      const records = await governanceService.getSensitiveRecords({ limit: 100 })
      setSensitiveRecords(records)

      // 加载脱敏策略
      const policies = await governanceService.getMaskingPolicies()
      setMaskingPolicies(policies)
    } catch (error) {
      console.error('Failed to load governance data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateClassification = async (values: any) => {
    try {
      await governanceService.createClassification(values)
      message.success('分类创建成功')
      setIsClassModalOpen(false)
      loadGovernanceData()
    } catch (error: any) {
      message.error(`创建失败：${error.message}`)
    }
  }

  const handleCreateMaskingPolicy = async (values: any) => {
    try {
      await governanceService.createMaskingPolicy(values)
      message.success('脱敏策略创建成功')
      setIsPolicyModalOpen(false)
      loadGovernanceData()
    } catch (error: any) {
      message.error(`创建失败：${error.message}`)
    }
  }

  // 分类树渲染
  const renderClassificationTree = () => {
    return (
      <DirectoryTree
        treeData={classificationTree.map((node) => ({
          title: (
            <span className="flex items-center gap-2">
              <TagsOutlined />
              {node.name}
              {node.tags?.map((tag, i) => (
                <Tag key={i}>{tag}</Tag>
              ))}
            </span>
          ),
          key: node.id,
          children: node.children?.map((child) => ({
            title: (
              <span className="flex items-center gap-2">
                <TagsOutlined />
                {child.name}
              </span>
            ),
            key: child.id,
          })),
        }))}
      />
    )
  }

  // 敏感数据表格列
  const sensitiveColumns = [
    {
      title: '数据源',
      dataIndex: 'datasource',
      key: 'datasource',
    },
    {
      title: '表名',
      dataIndex: 'table_name',
      key: 'table_name',
    },
    {
      title: '列名',
      dataIndex: 'column_name',
      key: 'column_name',
    },
    {
      title: '敏感级别',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      render: (level: string) => (
        <Tag color={sensitivityColors[level]}>{sensitivityLabels[level]}</Tag>
      ),
    },
    {
      title: '模式类型',
      dataIndex: 'pattern_type',
      key: 'pattern_type',
    },
    {
      title: '已脱敏',
      dataIndex: 'is_masked',
      key: 'is_masked',
      render: (masked: boolean) => (
        <Badge status={masked ? 'success' : 'error'} text={masked ? '已脱敏' : '未脱敏'} />
      ),
    },
    {
      title: '已审核',
      dataIndex: 'is_reviewed',
      key: 'is_reviewed',
      render: (reviewed: boolean) => (
        <Badge status={reviewed ? 'success' : 'default'} text={reviewed ? '已审核' : '待审核'} />
      ),
    },
  ]

  // 脱敏策略表格列
  const policyColumns = [
    {
      title: '策略名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '脱敏类型',
      dataIndex: 'masking_type',
      key: 'masking_type',
      render: (type: string) => maskingTypeLabels[type] || type,
    },
    {
      title: '适用敏感级别',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      render: (level: string) => (level ? sensitivityLabels[level] : '全部'),
    },
    {
      title: '数据类型',
      dataIndex: 'data_type',
      key: 'data_type',
    },
    {
      title: '列匹配模式',
      dataIndex: 'column_pattern',
      key: 'column_pattern',
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
    },
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={2} style={{ margin: 0 }}>
          数据治理
        </Title>
        <Space>
          <Select
            value={selectedDatasource}
            onChange={setSelectedDatasource}
            style={{ width: 200 }}
            options={connectors.map((c) => ({ label: c.datasource_name, value: c.datasource_name }))}
          />
          <Button
            type="primary"
            icon={<ScanOutlined />}
            loading={scanLoading}
            onClick={() => setScanLoading(true)}
          >
            扫描敏感数据
          </Button>
        </Space>
      </div>

      {/* 治理分数卡片 */}
      {governanceScore && (
        <Row gutter={[16, 16]} className="mb-6">
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="整体治理分数"
                value={governanceScore.overall_score}
                precision={1}
                suffix="%"
                prefix={<SafetyCertificateOutlined />}
                valueStyle={{
                  color:
                    governanceScore.overall_score >= 80
                      ? '#3f8600'
                      : governanceScore.overall_score >= 60
                      ? '#faad14'
                      : '#cf1322',
                }}
              />
              <Progress
                percent={governanceScore.overall_score}
                showInfo={false}
                strokeColor={
                  governanceScore.overall_score >= 80
                    ? '#52c41a'
                    : governanceScore.overall_score >= 60
                    ? '#faad14'
                    : '#ff4d4f'
                }
                style={{ marginTop: 8 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="分类覆盖率"
                value={governanceScore.classification_coverage}
                precision={1}
                suffix="%"
              />
              <Progress
                percent={governanceScore.classification_coverage}
                showInfo={false}
                size="small"
                style={{ marginTop: 8 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="敏感数据覆盖率"
                value={governanceScore.sensitivity_coverage}
                precision={1}
                suffix="%"
              />
              <Progress
                percent={governanceScore.sensitivity_coverage}
                showInfo={false}
                size="small"
                style={{ marginTop: 8 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="脱敏覆盖率"
                value={governanceScore.masking_coverage}
                precision={1}
                suffix="%"
              />
              <Progress
                percent={governanceScore.masking_coverage}
                showInfo={false}
                size="small"
                style={{ marginTop: 8 }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Tabs defaultActiveKey="classification">
        {/* 数据分类 */}
        <TabPane
          tab={
            <span>
              <TagsOutlined />
              数据分类
            </span>
          }
          key="classification"
        >
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card
                title="分类树"
                extra={
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    size="small"
                    onClick={() => setIsClassModalOpen(true)}
                  >
                    新建分类
                  </Button>
                }
              >
                {renderClassificationTree()}
              </Card>
            </Col>
            <Col span={12}>
              <Card title="数据标签">
                <Table
                  dataSource={labels}
                  columns={[
                    { title: '数据源', dataIndex: 'datasource', key: 'datasource' },
                    { title: '表名', dataIndex: 'table_name', key: 'table_name' },
                    { title: '列名', dataIndex: 'column_name', key: 'column_name' },
                    {
                      title: '标签类型',
                      dataIndex: 'label_type',
                      key: 'label_type',
                      render: (type: string) => <Tag>{type}</Tag>,
                    },
                    { title: '标签键', dataIndex: 'label_key', key: 'label_key' },
                    { title: '标签值', dataIndex: 'label_value', key: 'label_value' },
                  ]}
                  rowKey="id"
                  pagination={{ pageSize: 10 }}
                  size="small"
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 敏感数据 */}
        <TabPane
          tab={
            <span>
              <EyeInvisibleOutlined />
              敏感数据
            </span>
          }
          key="sensitive"
        >
          <Card>
            <Table
              columns={sensitiveColumns}
              dataSource={sensitiveRecords}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              loading={loading}
            />
          </Card>
        </TabPane>

        {/* 脱敏策略 */}
        <TabPane
          tab={
            <span>
              <BlockOutlined />
              脱敏策略
            </span>
          }
          key="masking"
        >
          <Card
            title="脱敏策略列表"
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setIsPolicyModalOpen(true)}
              >
                新建策略
              </Button>
            }
          >
            <Table
              columns={policyColumns}
              dataSource={maskingPolicies}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              size="small"
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 新建分类模态框 */}
      <Modal
        title="新建数据分类"
        open={isClassModalOpen}
        onOk={() => (document.querySelector('[data-modal-ok]') as HTMLElement)?.click()}
        onCancel={() => setIsClassModalOpen(false)}
        footer={null}
      >
        <Form onFinish={handleCreateClassification}>
          {/* 简化实现 */}
        </Form>
      </Modal>

      {/* 新建脱敏策略模态框 */}
      <Modal
        title="新建脱敏策略"
        open={isPolicyModalOpen}
        onCancel={() => setIsPolicyModalOpen(false)}
        footer={null}
      >
        <Form onFinish={handleCreateMaskingPolicy}>
          {/* 简化实现 */}
        </Form>
      </Modal>
    </div>
  )
}

export default GovernancePage
