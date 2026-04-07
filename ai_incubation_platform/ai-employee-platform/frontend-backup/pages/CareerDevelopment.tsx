/**
 * 职业发展页面
 */
import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Button,
  Space,
  List,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  message,
  Empty,
  Avatar,
  Badge,
  Descriptions,
  Progress,
  Statistic,
  Tabs,
  Tree,
} from 'antd';
import {
  AimOutlined,
  BookOutlined,
  UsergroupAddOutlined,
  TrophyOutlined,
  PlusOutlined,
  StarOutlined,
  RiseOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import { useCareerDevelopment } from '@/hooks/useCareerDevelopment';
import { useAuth } from '@/hooks/useAuth';
import type { EmployeeSkill, CareerRole, DevelopmentPlan } from '@/services/careerDevelopmentApi';
import dayjs from 'dayjs';

const { Title, Paragraph, Text } = Typography;

const CareerDevelopment: React.FC = () => {
  const { user } = useAuth();
  const {
    employeeSkillsQuery,
    addEmployeeSkillMutation,
    careerRolesQuery,
    recommendCareerPathsQuery,
    developmentPlansQuery,
    createDevelopmentPlanMutation,
    mentorMatchesQuery,
    careerDashboardQuery,
  } = useCareerDevelopment();

  const [activeTab, setActiveTab] = useState('skills');
  const [skillModalOpen, setSkillModalOpen] = useState(false);
  const [planModalOpen, setPlanModalOpen] = useState(false);
  const [skillForm] = Form.useForm();
  const [planForm] = Form.useForm();

  const employeeId = user?.id || '';

  // 获取数据
  const { data: employeeSkills, isLoading: loadingSkills } = employeeSkillsQuery(employeeId);
  const { data: careerRoles, isLoading: loadingRoles } = careerRolesQuery();
  const { data: recommendPaths, isLoading: loadingPaths } = recommendCareerPathsQuery(employeeId);
  const { data: developmentPlans, isLoading: loadingPlans } = developmentPlansQuery(employeeId);
  const { data: mentorMatches } = mentorMatchesQuery(employeeId);
  careerDashboardQuery(employeeId);

  // 添加技能
  const handleAddSkill = (values: any) => {
    addEmployeeSkillMutation.mutate(
      {
        employee_id: employeeId,
        skill_id: values.skill_id,
        level: values.level,
        years_of_experience: values.years_of_experience,
      },
      {
        onSuccess: () => {
          message.success('技能添加成功');
          setSkillModalOpen(false);
          skillForm.resetFields();
        },
        onError: () => {
          message.error('添加技能失败');
        },
      }
    );
  };

  // 创建发展计划
  const handleCreatePlan = (values: any) => {
    createDevelopmentPlanMutation.mutate(
      {
        employee_id: employeeId,
        plan_name: values.plan_name,
        target_role_id: values.target_role_id,
        start_date: values.start_date,
        target_completion_date: values.target_completion_date,
      },
      {
        onSuccess: () => {
          message.success('发展计划创建成功');
          setPlanModalOpen(false);
          planForm.resetFields();
        },
        onError: () => {
          message.error('创建发展计划失败');
        },
      }
    );
  };

  // 获取技能等级标签
  const getSkillLevelTag = (level: string) => {
    const levelMap: Record<string, { color: string; text: string }> = {
      beginner: { color: 'default', text: '初学者' },
      intermediate: { color: 'blue', text: '中级' },
      advanced: { color: 'cyan', text: '高级' },
      expert: { color: 'purple', text: '专家' },
      master: { color: 'gold', text: '大师' },
    };
    const config = levelMap[level] || { color: 'default', text: level };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 技能图谱内容
  const SkillsContent = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 技能统计 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="已掌握技能"
              value={employeeSkills?.length || 0}
              prefix={<BookOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="专家级技能"
              value={employeeSkills?.filter((s: any) => s.level === 'expert' || s.level === 'master').length || 0}
              prefix={<StarOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="学习目标"
              value={5}
              suffix="个"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="学习进度"
              value={75}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 我的技能 */}
      <Card
        title={<><BookOutlined /> 我的技能</>}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setSkillModalOpen(true)}
          >
            添加技能
          </Button>
        }
      >
        {loadingSkills ? (
          <Empty description="加载中..." />
        ) : !employeeSkills?.length ? (
          <Empty description="暂无技能记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Row gutter={16}>
            {(employeeSkills || []).map((empSkill: EmployeeSkill) => (
              <Col span={8} key={empSkill.skill.id}>
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Text strong>{empSkill.skill.name}</Text>
                      {getSkillLevelTag(empSkill.level)}
                    </Space>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {empSkill.skill.description}
                    </Text>
                    {empSkill.years_of_experience > 0 && (
                      <Text type="secondary">
                        经验：{empSkill.years_of_experience}年
                      </Text>
                    )}
                    {empSkill.skill.tags && empSkill.skill.tags.length > 0 && (
                      <div>
                        {empSkill.skill.tags.map((tag: string) => (
                          <Tag key={tag} color="blue" style={{ marginBottom: 4 }}>
                            {tag}
                          </Tag>
                        ))}
                      </div>
                    )}
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Card>

      {/* 技能树 */}
      <Card title={<><RiseOutlined /> 技能树</>}>
        <Tree
          blockNode
          defaultExpandAll
          treeData={[
            {
              title: '前端开发',
              key: 'frontend',
              children: [
                {
                  title: '基础技能',
                  key: 'frontend-basic',
                  children: [
                    { title: 'HTML/CSS', key: 'html-css' },
                    { title: 'JavaScript', key: 'javascript' },
                    { title: 'TypeScript', key: 'typescript' },
                  ],
                },
                {
                  title: '框架',
                  key: 'frontend-framework',
                  children: [
                    { title: 'React', key: 'react' },
                    { title: 'Vue', key: 'vue' },
                    { title: 'Angular', key: 'angular' },
                  ],
                },
              ],
            },
            {
              title: '后端开发',
              key: 'backend',
              children: [
                {
                  title: '语言',
                  key: 'backend-lang',
                  children: [
                    { title: 'Python', key: 'python' },
                    { title: 'Java', key: 'java' },
                    { title: 'Go', key: 'go' },
                  ],
                },
              ],
            },
          ]}
        />
      </Card>
    </Space>
  );

  // 职业路径内容
  const CareerPathsContent = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 推荐职业路径 */}
      <Card title={<><AimOutlined /> 推荐职业路径</>}>
        {loadingPaths ? (
          <Empty description="加载中..." />
        ) : !recommendPaths?.length ? (
          <Empty description="暂无推荐路径" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            dataSource={recommendPaths}
            renderItem={(item: any, _index: number) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{item.title}</Text>
                      <Tag color="green">匹配度 {item.match_score}%</Tag>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text type="secondary">{item.description}</Text>
                      <Progress percent={item.progress * 100} />
                      <Text type="secondary">
                        需要提升的技能：{item.required_skills?.join(', ')}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 职业角色列表 */}
      <Card
        title={<><TrophyOutlined /> 职业角色</>}
        extra={
          <Button type="link">查看全部</Button>
        }
      >
        {loadingRoles ? (
          <Empty description="加载中..." />
        ) : !careerRoles?.length ? (
          <Empty description="暂无职业角色" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Row gutter={16}>
            {(careerRoles || []).slice(0, 6).map((role: CareerRole) => (
              <Col span={8} key={role.id}>
                <Card size="small" hoverable>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>{role.name}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {role.description}
                    </Text>
                    <Tag color="blue">等级 {role.level}</Tag>
                    <Tag>{role.path_type}</Tag>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Card>
    </Space>
  );

  // 发展计划内容
  const DevelopmentPlansContent = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Button
        type="primary"
        icon={<PlusOutlined />}
        onClick={() => setPlanModalOpen(true)}
      >
        创建发展计划
      </Button>

      {loadingPlans ? (
        <Empty description="加载中..." />
      ) : !developmentPlans?.length ? (
        <Empty description="暂无发展计划" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Row gutter={16}>
          {(developmentPlans || []).map((plan: DevelopmentPlan) => (
            <Col span={12} key={plan.id}>
              <Card
                title={plan.plan_name}
                extra={
                  <Tag color={plan.status === 'active' ? 'processing' : plan.status === 'completed' ? 'success' : 'default'}>
                    {plan.status}
                  </Tag>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Progress
                    percent={plan.progress * 100}
                    format={() => `${Math.round(plan.progress * 100)}%`}
                  />
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="开始日期">
                      {plan.start_date ? dayjs(plan.start_date).format('YYYY-MM-DD') : '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="目标完成日期">
                      {plan.target_completion_date
                        ? dayjs(plan.target_completion_date).format('YYYY-MM-DD')
                        : '-'}
                    </Descriptions.Item>
                  </Descriptions>
                  <Button type="link" size="small">
                    查看详情
                  </Button>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 导师匹配 */}
      <Card
        title={<><UsergroupAddOutlined /> 推荐导师</>}
        extra={
          <Button type="link">查看更多</Button>
        }
      >
        {!mentorMatches?.length ? (
          <Empty description="暂无推荐导师" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Row gutter={16}>
            {(mentorMatches || []).map((mentor: any, index: number) => (
              <Col span={8} key={index}>
                <Card size="small" hoverable>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Avatar size={48} icon={<UsergroupAddOutlined />} />
                      <Space direction="vertical">
                        <Text strong>{mentor.name}</Text>
                        <Text type="secondary">{mentor.position}</Text>
                      </Space>
                    </Space>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      匹配度：{mentor.match_score}%
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      擅长领域：{mentor.expertise?.join(', ')}
                    </Text>
                    <Button type="primary" size="small" block>
                      联系导师
                    </Button>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Card>
    </Space>
  );

  const tabItems = [
    {
      key: 'skills',
      label: (
        <span>
          <BookOutlined />
          技能图谱
          <Badge count={employeeSkills?.length || 0} style={{ marginLeft: 8 }} />
        </span>
      ),
      children: <SkillsContent />,
    },
    {
      key: 'paths',
      label: (
        <span>
          <AimOutlined />
          职业路径
        </span>
      ),
      children: <CareerPathsContent />,
    },
    {
      key: 'plans',
      label: (
        <span>
          <DashboardOutlined />
          发展计划
        </span>
      ),
      children: <DevelopmentPlansContent />,
    },
  ];

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Title level={2}>职业发展</Title>
          <Paragraph type="secondary">
            规划职业路径，提升技能水平，实现职业目标
          </Paragraph>
        </div>

        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Space>

      {/* 添加技能弹窗 */}
      <Modal
        title="添加技能"
        open={skillModalOpen}
        onOk={() => skillForm.submit()}
        onCancel={() => setSkillModalOpen(false)}
        confirmLoading={addEmployeeSkillMutation.isPending}
      >
        <Form form={skillForm} layout="vertical" onFinish={handleAddSkill}>
          <Form.Item
            name="skill_id"
            label="选择技能"
            rules={[{ required: true, message: '请选择技能' }]}
          >
            <Select>
              <Select.Option value="react">React</Select.Option>
              <Select.Option value="typescript">TypeScript</Select.Option>
              <Select.Option value="nodejs">Node.js</Select.Option>
              <Select.Option value="python">Python</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="level"
            label="技能等级"
            rules={[{ required: true, message: '请选择等级' }]}
          >
            <Select>
              <Select.Option value="beginner">初学者</Select.Option>
              <Select.Option value="intermediate">中级</Select.Option>
              <Select.Option value="advanced">高级</Select.Option>
              <Select.Option value="expert">专家</Select.Option>
              <Select.Option value="master">大师</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="years_of_experience" label="从业年限">
            <Input type="number" placeholder="年" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建发展计划弹窗 */}
      <Modal
        title="创建发展计划"
        open={planModalOpen}
        onOk={() => planForm.submit()}
        onCancel={() => setPlanModalOpen(false)}
        confirmLoading={createDevelopmentPlanMutation.isPending}
      >
        <Form form={planForm} layout="vertical" onFinish={handleCreatePlan}>
          <Form.Item
            name="plan_name"
            label="计划名称"
            rules={[{ required: true, message: '请输入计划名称' }]}
          >
            <Input placeholder="例如：成为技术专家" />
          </Form.Item>
          <Form.Item
            name="target_role_id"
            label="目标职位"
            rules={[{ required: true, message: '请选择目标职位' }]}
          >
            <Select>
              <Select.Option value="role1">高级前端工程师</Select.Option>
              <Select.Option value="role2">技术专家</Select.Option>
              <Select.Option value="role3">技术主管</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="start_date"
            label="开始日期"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="target_completion_date"
            label="目标完成日期"
            rules={[{ required: true, message: '请选择目标完成日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CareerDevelopment;
