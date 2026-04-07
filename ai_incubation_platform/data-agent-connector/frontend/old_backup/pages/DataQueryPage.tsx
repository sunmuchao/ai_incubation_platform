/**
 * 数据查询页面 - 包含 SQL 编辑器和 NL2SQL
 */
import React, { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Input,
  Table,
  Tabs,
  Space,
  Typography,
  message,
  Spin,
  Alert,
  Tag,
  Collapse,
} from 'antd'
import {
  PlayCircleOutlined,
  ThunderboltOutlined,
  SaveOutlined,
  HistoryOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { queryService } from '../services/queryService'
import { connectorService } from '../services/connectorService'
import type { DataSource, SchemaTable } from '../types'

const { Title, Text } = Typography
const { TextArea } = Input
const { TabPane } = Tabs
const { Panel } = Collapse

// 默认 SQL 模板
const DEFAULT_SQL_TEMPLATES: Record<string, string> = {
  select: 'SELECT * FROM table_name LIMIT 100;',
  count: 'SELECT COUNT(*) FROM table_name;',
  group: `SELECT column_name, COUNT(*) as cnt
FROM table_name
GROUP BY column_name
ORDER BY cnt DESC;`,
  join: `SELECT a.*, b.*
FROM table_a a
INNER JOIN table_b b ON a.id = b.a_id;`,
}

const DataQueryPage: React.FC = () => {
  // 状态管理
  const [connectors, setConnectors] = useState<DataSource[]>([])
  const [selectedConnector, setSelectedConnector] = useState<string>('')
  const [schemas, setSchemas] = useState<Record<string, SchemaTable[]>>({})

  // SQL 编辑器状态
  const [sqlQuery, setSqlQuery] = useState<string>(DEFAULT_SQL_TEMPLATES.select)
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryResult, setQueryResult] = useState<any[]>([])
  const [queryStats, setQueryStats] = useState({ executionTime: 0, rowsReturned: 0 })

  // NL2SQL 状态
  const [naturalLanguage, setNaturalLanguage] = useState<string>('')
  const [nl2sqlLoading, setNl2sqlLoading] = useState(false)
  const [nl2sqlResult, setNl2sqlResult] = useState<any>(null)

  // 查询历史
  const [queryHistory, setQueryHistory] = useState<any[]>([])

  useEffect(() => {
    loadConnectors()
  }, [])

  const loadConnectors = async () => {
    try {
      const data = await connectorService.getActiveConnectors()
      setConnectors(data)
      if (data.length > 0) {
        setSelectedConnector(data[0].name)
        loadSchema(data[0].name)
      }
    } catch (error) {
      console.error('Failed to load connectors:', error)
    }
  }

  const loadSchema = async (connectorName: string) => {
    try {
      const schema = await connectorService.getConnectorSchema(connectorName)
      setSchemas((prev) => ({ ...prev, [connectorName]: schema?.tables || [] }))
    } catch (error) {
      console.error('Failed to load schema:', error)
    }
  }

  const handleConnectorChange = (value: string) => {
    setSelectedConnector(value)
    loadSchema(value)
  }

  // 执行 SQL 查询
  const executeQuery = async () => {
    if (!selectedConnector) {
      message.error('请选择数据源')
      return
    }
    if (!sqlQuery.trim()) {
      message.error('请输入 SQL 查询')
      return
    }

    setQueryLoading(true)
    try {
      const result = await queryService.executeQuery(selectedConnector, sqlQuery)
      setQueryResult(result.data || [])
      setQueryStats({
        executionTime: result.execution_time_ms || 0,
        rowsReturned: result.rows_returned || 0,
      })
      message.success('查询执行成功')

      // 添加到历史
      setQueryHistory((prev) => [
        { sql: sqlQuery, time: new Date().toISOString(), connector: selectedConnector },
        ...prev.slice(0, 19),
      ])
    } catch (error: any) {
      message.error(`查询失败：${error.message}`)
      setQueryResult([])
    } finally {
      setQueryLoading(false)
    }
  }

  // 执行 NL2SQL 查询
  const executeNLQuery = async () => {
    if (!selectedConnector) {
      message.error('请选择数据源')
      return
    }
    if (!naturalLanguage.trim()) {
      message.error('请输入自然语言查询')
      return
    }

    setNl2sqlLoading(true)
    try {
      const result = await queryService.aiQuery(
        selectedConnector,
        naturalLanguage,
        { use_enhanced: true, enable_self_correction: true }
      )
      setNl2sqlResult(result)
      if (result.success && result.data) {
        setQueryResult(result.data)
        setQueryStats({
          executionTime: result.execution_time_ms || 0,
          rowsReturned: result.data.length,
        })
        message.success('AI 查询成功')
      } else if (!result.success) {
        message.warning(`AI 查询未生成有效 SQL：${result.validation?.message || '未知错误'}`)
      }
    } catch (error: any) {
      message.error(`查询失败：${error.message}`)
    } finally {
      setNl2sqlLoading(false)
    }
  }

  // 插入模板
  const insertTemplate = (template: string) => {
    setSqlQuery(DEFAULT_SQL_TEMPLATES[template])
  }

  // 渲染结果表格
  const renderResultTable = () => {
    if (queryResult.length === 0) {
      return <div className="text-gray-400 text-center py-8">暂无查询结果</div>
    }

    const columns = Object.keys(queryResult[0]).map((key) => ({
      title: key,
      dataIndex: key,
      key,
      ellipsis: true,
      render: (val: any) => {
        if (val === null) return <span className="text-gray-400">NULL</span>
        if (typeof val === 'object') return JSON.stringify(val)
        return String(val)
      },
    }))

    return (
      <Table
        columns={columns}
        dataSource={queryResult}
        rowKey={(_, index) => `row-${index}`}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        scroll={{ x: 'max-content' }}
        size="small"
      />
    )
  }

  // Schema 树形展示
  const renderSchemaTree = () => {
    const tables = schemas[selectedConnector] || []
    if (tables.length === 0) {
      return <div className="text-gray-400 text-sm">暂无表结构</div>
    }

    return (
      <Collapse accordion size="small">
        {tables.map((table, index) => (
          <Panel header={<strong>{table.name}</strong>} key={index}>
            <ul className="text-sm space-y-1">
              {table.columns?.map((col, idx) => (
                <li key={idx} className="flex justify-between">
                  <span>
                    {col.name}
                    {col.is_primary && <Tag className="ml-1">PK</Tag>}
                  </span>
                  <span className="text-gray-500">{col.type}</span>
                </li>
              ))}
            </ul>
          </Panel>
        ))}
      </Collapse>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={2} style={{ margin: 0 }}>
          数据查询
        </Title>
        <Space>
          <Select
            value={selectedConnector}
            onChange={handleConnectorChange}
            style={{ width: 250 }}
            options={connectors.map((c) => ({ label: c.name, value: c.name }))}
          />
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        {/* 左侧：查询编辑器 */}
        <Col xs={24} lg={18}>
          <Card>
            <Tabs defaultActiveKey="sql">
              <TabPane
                tab={
                  <span>
                    <ThunderboltOutlined />
                    SQL 编辑器
                  </span>
                }
                key="sql"
              >
                <div className="mb-4">
                  <Space wrap>
                    <Text>快速插入：</Text>
                    <Button size="small" onClick={() => insertTemplate('select')}>
                      SELECT
                    </Button>
                    <Button size="small" onClick={() => insertTemplate('count')}>
                      COUNT
                    </Button>
                    <Button size="small" onClick={() => insertTemplate('group')}>
                      GROUP BY
                    </Button>
                    <Button size="small" onClick={() => insertTemplate('join')}>
                      JOIN
                    </Button>
                  </Space>
                </div>
                <div className="border border-gray-300 rounded-md overflow-hidden mb-4">
                  <Editor
                    height="300px"
                    defaultLanguage="sql"
                    theme="vs-light"
                    value={sqlQuery}
                    onChange={(value) => setSqlQuery(value || '')}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      automaticLayout: true,
                      scrollBeyondLastLine: false,
                    }}
                  />
                </div>
                <div className="flex justify-between items-center">
                  <Space>
                    <Button
                      type="primary"
                      size="large"
                      icon={<PlayCircleOutlined />}
                      onClick={executeQuery}
                      loading={queryLoading}
                    >
                      执行查询
                    </Button>
                    <Button icon={<SaveOutlined />} onClick={() => message.success('SQL 已保存')}>
                      保存 SQL
                    </Button>
                  </Space>
                  {queryStats.executionTime > 0 && (
                    <Text type="secondary">
                      耗时：{queryStats.executionTime}ms | 行数：{queryStats.rowsReturned}
                    </Text>
                  )}
                </div>
              </TabPane>

              <TabPane
                tab={
                  <span>
                    <RobotOutlined />
                    AI 自然语言查询
                  </span>
                }
                key="ai"
              >
                <div className="mb-4">
                  <TextArea
                    value={naturalLanguage}
                    onChange={(e) => setNaturalLanguage(e.target.value)}
                    placeholder="请输入自然语言查询，例如：&#10;&#10;查询上个月销售额最高的 10 个产品&#10;统计每个部门的员工数量和平均薪资"
                    rows={4}
                  />
                </div>
                <div className="mb-4">
                  <Alert
                    message="AI 查询提示"
                    description="AI 将自动分析您的查询意图并生成 SQL。支持 Few-Shot 学习、关系增强和自校正功能。"
                    type="info"
                    showIcon
                  />
                </div>
                <Button
                  type="primary"
                  size="large"
                  icon={<RobotOutlined />}
                  onClick={executeNLQuery}
                  loading={nl2sqlLoading}
                >
                  AI 查询
                </Button>

                {nl2sqlResult && (
                  <Card title="AI 查询结果" size="small" className="mt-4">
                    <div className="space-y-2">
                      <div>
                        <Text strong>置信度：</Text>
                        <Tag color={nl2sqlResult.confidence > 0.8 ? 'green' : 'orange'}>
                          {(nl2sqlResult.confidence * 100).toFixed(1)}%
                        </Tag>
                      </div>
                      <div>
                        <Text strong>生成 SQL：</Text>
                        <pre className="bg-gray-100 p-2 rounded text-sm overflow-auto">
                          {nl2sqlResult.sql}
                        </pre>
                      </div>
                      {nl2sqlResult.explanation && (
                        <div>
                          <Text strong>结果解释：</Text>
                          <p className="text-gray-600">{nl2sqlResult.explanation}</p>
                        </div>
                      )}
                      {nl2sqlResult.suggestions?.length > 0 && (
                        <div>
                          <Text strong>优化建议：</Text>
                          <ul className="text-gray-600">
                            {nl2sqlResult.suggestions.map((s: string, i: number) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </Card>
                )}
              </TabPane>
            </Tabs>
          </Card>

          {/* 查询结果 */}
          <Card title="查询结果" className="mt-4">
            {queryLoading ? (
              <div className="flex justify-center py-12">
                <Spin size="large" tip="执行查询中..." />
              </div>
            ) : (
              renderResultTable()
            )}
          </Card>
        </Col>

        {/* 右侧：Schema 和历史 */}
        <Col xs={24} lg={6}>
          <Card title="表结构" className="mb-4" size="small">
            <div className="max-h-64 overflow-auto">{renderSchemaTree()}</div>
          </Card>

          <Card
            title={
              <span>
                <HistoryOutlined /> 查询历史
              </span>
            }
            size="small"
          >
            <div className="space-y-2 max-h-96 overflow-auto">
              {queryHistory.length === 0 ? (
                <div className="text-gray-400 text-sm text-center py-4">暂无查询历史</div>
              ) : (
                queryHistory.map((item, index) => (
                  <Card
                    key={index}
                    size="small"
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => setSqlQuery(item.sql)}
                  >
                    <div className="text-xs text-gray-500 mb-1">
                      {new Date(item.time).toLocaleString()}
                    </div>
                    <div className="text-sm font-mono truncate">{item.sql}</div>
                  </Card>
                ))
              )}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DataQueryPage
