/**
 * 连接器管理页面
 */
import React, { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Descriptions,
  Drawer,
  Typography,
  Empty,
} from 'antd'
import {
  PlusOutlined,
  DisconnectOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { connectorService } from '../services/connectorService'
import type { DataSource, ConnectorType, ConnectorSchema } from '../types'

const { Title } = Typography
const { TextArea } = Input

const ConnectorsPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [connectors, setConnectors] = useState<DataSource[]>([])
  const [connectorTypes, setConnectorTypes] = useState<ConnectorType[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form] = Form.useForm()
  const [selectedConnector, setSelectedConnector] = useState<DataSource | null>(null)
  const [schemaDrawerOpen, setSchemaDrawerOpen] = useState(false)
  const [schema, setSchema] = useState<ConnectorSchema | null>(null)
  const [schemaLoading, setSchemaLoading] = useState(false)

  useEffect(() => {
    loadConnectors()
    loadConnectorTypes()
  }, [])

  const loadConnectors = async () => {
    setLoading(true)
    try {
      const data = await connectorService.getActiveConnectors()
      setConnectors(data)
    } catch (error) {
      console.error('Failed to load connectors:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadConnectorTypes = async () => {
    try {
      const types = await connectorService.getConnectorTypes()
      setConnectorTypes(types)
    } catch (error) {
      console.error('Failed to load connector types:', error)
    }
  }

  const handleCreateConnector = async (values: any) => {
    try {
      await connectorService.createConnector(values.connector_type, {
        name: values.name,
        datasource_name: values.datasource_name,
        connection_string: values.connection_string,
      })
      message.success('连接器创建成功')
      setIsModalOpen(false)
      form.resetFields()
      loadConnectors()
    } catch (error: any) {
      message.error(`创建失败：${error.message}`)
    }
  }

  const handleDisconnect = async (name: string) => {
    try {
      await connectorService.disconnectConnector(name)
      message.success('连接器已断开')
      loadConnectors()
    } catch (error: any) {
      message.error(`断开失败：${error.message}`)
    }
  }

  const handleViewSchema = async (connector: DataSource) => {
    setSchemaLoading(true)
    setSchemaDrawerOpen(true)
    setSelectedConnector(connector)
    try {
      const schemaData = await connectorService.getConnectorSchema(connector.name)
      setSchema(schemaData)
    } catch (error: any) {
      message.error(`获取 Schema 失败：${error.message}`)
    } finally {
      setSchemaLoading(false)
    }
  }

  const columns = [
    {
      title: '连接器名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <Space>
          <DatabaseOutlined />
          <strong>{text}</strong>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'connector_type',
      key: 'connector_type',
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '数据源名称',
      dataIndex: 'datasource_name',
      key: 'datasource_name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag icon={status === 'connected' ? <CheckCircleOutlined /> : <CloseCircleOutlined />} color={status === 'connected' ? 'green' : status === 'error' ? 'red' : 'default'}>
          {status === 'connected' ? '已连接' : status === 'error' ? '异常' : '未连接'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: DataSource) => (
        <Space>
          <Button
            size="small"
            icon={<DatabaseOutlined />}
            onClick={() => handleViewSchema(record)}
          >
            查看 Schema
          </Button>
          <Popconfirm
            title="确定要断开此连接器吗？"
            onConfirm={() => handleDisconnect(record.name)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DisconnectOutlined />}>
              断开
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={2} style={{ margin: 0 }}>
          连接器管理
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsModalOpen(true)}
        >
          新建连接器
        </Button>
      </div>

      <Card>
        {connectors.length === 0 && !loading ? (
          <Empty
            description="暂无连接器"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Table
            columns={columns}
            dataSource={connectors}
            rowKey="name"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        )}
      </Card>

      {/* 新建连接器模态框 */}
      <Modal
        title="新建连接器"
        open={isModalOpen}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsModalOpen(false)
          form.resetFields()
        }}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateConnector}
        >
          <Form.Item
            name="connector_type"
            label="连接器类型"
            rules={[{ required: true, message: '请选择连接器类型' }]}
          >
            <Select placeholder="请选择连接器类型">
              {connectorTypes.map((type) => (
                <Select.Option key={type.name} value={type.name}>
                  {type.display_name} - {type.description}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="name"
            label="连接器名称"
            rules={[{ required: true, message: '请输入连接器名称' }]}
          >
            <Input placeholder="例如：mysql-prod" />
          </Form.Item>

          <Form.Item
            name="datasource_name"
            label="数据源名称"
            rules={[{ required: true, message: '请输入数据源名称' }]}
          >
            <Input placeholder="例如：production_db" />
          </Form.Item>

          <Form.Item
            name="connection_string"
            label="连接字符串"
            rules={[{ required: true, message: '请输入连接字符串' }]}
          >
            <TextArea
              rows={4}
              placeholder="例如：mysql://user:password@localhost:3306/dbname"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Schema 查看抽屉 */}
      <Drawer
        title={`Schema - ${selectedConnector?.name}`}
        placement="right"
        width={720}
        open={schemaDrawerOpen}
        onClose={() => {
          setSchemaDrawerOpen(false)
          setSchema(null)
        }}
      >
        {schemaLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-400">加载中...</div>
          </div>
        ) : schema ? (
          <div>
            <Descriptions title="基本信息" bordered column={1} size="small">
              <Descriptions.Item label="数据源">
                {selectedConnector?.datasource_name}
              </Descriptions.Item>
              <Descriptions.Item label="表数量">
                {schema.tables?.length || 0}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5} style={{ marginTop: 24 }}>
              表结构
            </Title>
            {schema.tables?.map((table, index) => (
              <Card
                key={index}
                title={table.name}
                size="small"
                className="mb-4"
              >
                <Table
                  dataSource={table.columns?.map((col, idx) => ({
                    ...col,
                    key: idx,
                  })) || []}
                  columns={[
                    {
                      title: '列名',
                      dataIndex: 'name',
                      key: 'name',
                      render: (text: string, record: any) => (
                        <Space>
                          {record.is_primary && <Tag color="gold">PK</Tag>}
                          {record.is_foreign && <Tag color="purple">FK</Tag>}
                          {text}
                        </Space>
                      ),
                    },
                    {
                      title: '类型',
                      dataIndex: 'type',
                      key: 'type',
                    },
                    {
                      title: '可空',
                      dataIndex: 'nullable',
                      key: 'nullable',
                      render: (nullable: boolean) =>
                        nullable ? (
                          <Tag color="default">是</Tag>
                        ) : (
                          <Tag color="green">否</Tag>
                        ),
                    },
                    {
                      title: '注释',
                      dataIndex: 'comment',
                      key: 'comment',
                    },
                  ]}
                  pagination={false}
                  size="small"
                />
              </Card>
            ))}
          </div>
        ) : (
          <Empty description="无 Schema 数据" />
        )}
      </Drawer>
    </div>
  )
}

export default ConnectorsPage
