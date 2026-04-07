import { Form, Input, InputNumber, Button, Card, Switch, Divider, message, Select } from 'antd'

function Settings() {
  const [form] = Form.useForm()

  const handleSubmit = (values: any) => {
    console.log('Settings:', values)
    message.success('设置保存成功！')
  }

  return (
    <div>
      <Card title="数据流配置">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            refreshInterval: 30,
            maxEventsDisplay: 100,
            enableNotifications: true,
            highPriorityOnly: false,
            defaultTimeRange: 24,
          }}
        >
          <Form.Item
            label="数据刷新间隔（秒）"
            name="refreshInterval"
            rules={[{ required: true, message: '请输入刷新间隔' }]}
          >
            <InputNumber min={5} max={300} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            label="最大显示事件数"
            name="maxEventsDisplay"
            rules={[{ required: true, message: '请输入最大显示事件数' }]}
          >
            <InputNumber min={10} max={1000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            label="默认时间范围（小时）"
            name="defaultTimeRange"
            rules={[{ required: true, message: '请输入时间范围' }]}
          >
            <InputNumber min={1} max={168} style={{ width: '100%' }} />
          </Form.Item>

          <Divider />

          <Form.Item
            label="启用实时通知"
            name="enableNotifications"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            label="仅显示高优先级事件"
            name="highPriorityOnly"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit">
              保存配置
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default Settings
