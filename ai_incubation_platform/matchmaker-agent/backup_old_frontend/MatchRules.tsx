import { Form, Input, InputNumber, Button, Card, Switch, Select, message } from 'antd'

function MatchRules() {
  const [form] = Form.useForm()

  const handleSubmit = (values: any) => {
    console.log('Match Rules:', values)
    message.success('匹配规则保存成功！')
  }

  return (
    <div>
      <Card title="匹配规则配置">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            minScore: 70,
            maxRecommendations: 10,
            autoMatch: true,
            skillWeight: 40,
            experienceWeight: 30,
            educationWeight: 20,
            locationWeight: 10,
          }}
        >
          <Form.Item
            label="最低匹配分数"
            name="minScore"
            rules={[{ required: true, message: '请输入最低匹配分数' }]}
          >
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            label="最大推荐数量"
            name="maxRecommendations"
            rules={[{ required: true, message: '请输入最大推荐数量' }]}
          >
            <InputNumber min={1} max={50} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            label="自动匹配"
            name="autoMatch"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Card title="权重配置" type="inner" style={{ marginBottom: 16 }}>
            <Form.Item label="技能权重 (%)" name="skillWeight">
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="经验权重 (%)" name="experienceWeight">
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="学历权重 (%)" name="educationWeight">
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="地点权重 (%)" name="locationWeight">
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
          </Card>

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

export default MatchRules
