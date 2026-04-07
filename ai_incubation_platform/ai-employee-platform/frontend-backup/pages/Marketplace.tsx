/**
 * 人才市场页面
 */
import React, { useState, useMemo } from 'react';
import { Row, Col, Card, Input, Select, Slider, Checkbox, Typography, Space, Button, Empty } from 'antd';
import { SearchOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { EmployeeCard, StatCard } from '@/components';
import { useMarketplace } from '@/hooks';
import { type MarketplaceFilters } from '@/services/marketplaceApi';
import type { AIEmployee } from '@/types/employee';

const { Title, Text } = Typography;
const { Option } = Select;

const Marketplace: React.FC = () => {
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>();
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 1000]);
  const [minRating, setMinRating] = useState(0);
  const [availableOnly, setAvailableOnly] = useState(true);

  const { search } = useMarketplace();

  // 分类选项
  const categories = useMemo(
    () => [
      { label: '全部', value: '' },
      { label: '技术开发', value: 'development' },
      { label: '数据分析', value: 'analytics' },
      { label: '客户服务', value: 'support' },
      { label: '内容创作', value: 'content' },
      { label: '营销推广', value: 'marketing' },
      { label: '设计创意', value: 'design' },
    ],
    []
  );

  // 技能选项
  const skillOptions = useMemo(
    () => [
      { label: 'Python', value: 'python' },
      { label: 'JavaScript', value: 'javascript' },
      { label: '数据分析', value: 'data-analysis' },
      { label: '机器学习', value: 'ml' },
      { label: '自然语言处理', value: 'nlp' },
      { label: '图像处理', value: 'cv' },
    ],
    []
  );

  // 处理搜索
  const handleSearch = async () => {
    await search({
      category: selectedCategory,
      max_hourly_rate: priceRange[1],
      min_rating: minRating,
      available_only: availableOnly,
      keyword: searchKeyword,
    } as MarketplaceFilters);
  };

  // 模拟数据（实际应从 API 获取）
  const mockEmployees: AIEmployee[] = [
    {
      id: '1',
      name: '数据分析助手',
      description: '专业的数据分析 AI，擅长处理 CSV/Excel 数据，生成可视化报告',
      avatar_url: '',
      owner_id: 'owner1',
      tenant_id: 'tenant1',
      status: 'available',
      category: 'analytics',
      skills: { Python: 'expert', Pandas: 'expert', SQL: 'advanced', '可视化': 'advanced' },
      hourly_rate: 50,
      rating: 4.8,
      review_count: 156,
      total_hours_worked: 1280,
      completion_rate: 98,
      response_time_hours: 2,
      timezone: 'UTC+8',
      languages: ['中文', 'English'],
      tags: ['数据分析', 'Python', '可视化'],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-06-01T00:00:00Z',
    },
    {
      id: '2',
      name: '客服机器人',
      description: '7x24 小时在线客服，支持多语言，擅长处理客户咨询和投诉',
      avatar_url: '',
      owner_id: 'owner2',
      tenant_id: 'tenant2',
      status: 'available',
      category: 'support',
      skills: { '沟通': 'expert', '多语言': 'expert', '问题解决': 'advanced' },
      hourly_rate: 30,
      rating: 4.9,
      review_count: 523,
      total_hours_worked: 3200,
      completion_rate: 99,
      response_time_hours: 1,
      timezone: 'UTC+8',
      languages: ['中文', 'English', '日本語'],
      tags: ['客服', '多语言', '即时响应'],
      created_at: '2024-02-01T00:00:00Z',
      updated_at: '2024-06-01T00:00:00Z',
    },
    {
      id: '3',
      name: '代码审查助手',
      description: '专业代码审查，发现潜在 bug 和安全漏洞，提供优化建议',
      avatar_url: '',
      owner_id: 'owner3',
      tenant_id: 'tenant3',
      status: 'busy',
      category: 'development',
      skills: { CodeReview: 'expert', Security: 'expert', Python: 'advanced', JavaScript: 'advanced' },
      hourly_rate: 80,
      rating: 4.7,
      review_count: 89,
      total_hours_worked: 560,
      completion_rate: 95,
      response_time_hours: 4,
      timezone: 'UTC+8',
      languages: ['中文', 'English'],
      tags: ['代码审查', '安全', '优化'],
      created_at: '2024-03-01T00:00:00Z',
      updated_at: '2024-06-01T00:00:00Z',
    },
    {
      id: '4',
      name: '文档生成器',
      description: '自动生成技术文档、API 文档、用户手册等',
      avatar_url: '',
      owner_id: 'owner4',
      tenant_id: 'tenant4',
      status: 'available',
      category: 'content',
      skills: { Writing: 'expert', TechDoc: 'expert', Markdown: 'advanced' },
      hourly_rate: 40,
      rating: 4.6,
      review_count: 67,
      total_hours_worked: 420,
      completion_rate: 96,
      response_time_hours: 3,
      timezone: 'UTC+8',
      languages: ['中文', 'English'],
      tags: ['文档', '写作', '技术'],
      created_at: '2024-03-15T00:00:00Z',
      updated_at: '2024-06-01T00:00:00Z',
    },
    {
      id: '5',
      name: '图像识别专家',
      description: '专业的图像识别和分析，支持物体检测、人脸识别、场景理解',
      avatar_url: '',
      owner_id: 'owner5',
      tenant_id: 'tenant5',
      status: 'available',
      category: 'development',
      skills: { CV: 'expert', PyTorch: 'expert', TensorFlow: 'advanced' },
      hourly_rate: 100,
      rating: 4.9,
      review_count: 45,
      total_hours_worked: 280,
      completion_rate: 98,
      response_time_hours: 6,
      timezone: 'UTC+8',
      languages: ['中文', 'English'],
      tags: ['图像识别', '深度学习', 'CV'],
      created_at: '2024-04-01T00:00:00Z',
      updated_at: '2024-06-01T00:00:00Z',
    },
    {
      id: '6',
      name: '营销文案助手',
      description: '创作吸引人的营销文案，支持多种风格和平台',
      avatar_url: '',
      owner_id: 'owner6',
      tenant_id: 'tenant6',
      status: 'unavailable',
      category: 'marketing',
      skills: { Copywriting: 'expert', SEO: 'advanced', '社交媒体': 'advanced' },
      hourly_rate: 60,
      rating: 4.7,
      review_count: 112,
      total_hours_worked: 680,
      completion_rate: 94,
      response_time_hours: 2,
      timezone: 'UTC+8',
      languages: ['中文', 'English'],
      tags: ['营销', '文案', 'SEO'],
      created_at: '2024-04-15T00:00:00Z',
      updated_at: '2024-06-01T00:00:00Z',
    },
  ];

  return (
    <div className="marketplace-page">
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>人才市场</Title>
        <Text type="secondary">发现和雇佣专业的 AI 员工</Text>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8} lg={6}>
          <StatCard
            title="AI 员工总数"
            value={256}
            suffix="人"
            prefix={<ThunderboltOutlined style={{ color: '#1890ff' }} />}
          />
        </Col>
        <Col xs={24} sm={8} lg={6}>
          <StatCard
            title="今日新增"
            value={12}
            suffix="人"
            trend={8}
            trendType="up"
          />
        </Col>
        <Col xs={24} sm={8} lg={6}>
          <StatCard
            title="平均评分"
            value={4.6}
            suffix="分"
            prefix="⭐"
          />
        </Col>
        <Col xs={24} sm={8} lg={6}>
          <StatCard
            title="平均时薪"
            value={65}
            prefix="¥"
            suffix="/小时"
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 左侧筛选栏 */}
        <Col xs={24} lg={6}>
          <Card title="筛选条件" bordered={false}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* 搜索框 */}
              <div>
                <Text strong>关键词搜索</Text>
                <Input
                  placeholder="输入技能或描述"
                  prefix={<SearchOutlined />}
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                  onPressEnter={handleSearch}
                  allowClear
                  style={{ marginTop: 8 }}
                />
              </div>

              {/* 分类筛选 */}
              <div>
                <Text strong>分类</Text>
                <Select
                  mode="multiple"
                  placeholder="选择分类"
                  style={{ width: '100%', marginTop: 8 }}
                  value={selectedCategory ? [selectedCategory] : []}
                  onChange={(values) => setSelectedCategory(values[0])}
                >
                  {categories.map((cat) => (
                    <Option key={cat.value} value={cat.value}>
                      {cat.label}
                    </Option>
                  ))}
                </Select>
              </div>

              {/* 技能筛选 */}
              <div>
                <Text strong>技能</Text>
                <Select
                  mode="multiple"
                  placeholder="选择技能"
                  style={{ width: '100%', marginTop: 8 }}
                  maxTagCount="responsive"
                >
                  {skillOptions.map((skill) => (
                    <Option key={skill.value} value={skill.value}>
                      {skill.label}
                    </Option>
                  ))}
                </Select>
              </div>

              {/* 价格范围 */}
              <div>
                <Text strong>时薪范围 (¥)</Text>
                <Slider
                  range
                  min={0}
                  max={1000}
                  value={priceRange}
                  onChange={(value) => setPriceRange(value as [number, number])}
                  style={{ marginTop: 8 }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                  <Text type="secondary">¥{priceRange[0]}</Text>
                  <Text type="secondary">¥{priceRange[1]}+</Text>
                </div>
              </div>

              {/* 最低评分 */}
              <div>
                <Text strong>最低评分</Text>
                <Slider
                  min={0}
                  max={5}
                  step={0.5}
                  value={minRating}
                  onChange={(value) => setMinRating(value as number)}
                  marks={{
                    0: '0',
                    2.5: '2.5',
                    4: '4+',
                    5: '5',
                  }}
                  style={{ marginTop: 8 }}
                />
              </div>

              {/* 只看可雇佣 */}
              <Checkbox checked={availableOnly} onChange={(e) => setAvailableOnly(e.target.checked)}>
                只看可雇佣
              </Checkbox>

              {/* 按钮 */}
              <Space style={{ width: '100%' }}>
                <Button type="primary" onClick={handleSearch} block>
                  应用筛选
                </Button>
                <Button
                  onClick={() => {
                    setSearchKeyword('');
                    setSelectedCategory(undefined);
                    setPriceRange([0, 1000]);
                    setMinRating(0);
                    setAvailableOnly(true);
                  }}
                  block
                >
                  重置
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>

        {/* 右侧员工列表 */}
        <Col xs={24} lg={18}>
          <Card
            bordered={false}
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>AI 员工列表</span>
                <Text type="secondary">共 {mockEmployees.length} 位</Text>
              </div>
            }
            extra={
              <Select defaultValue="rating" style={{ width: 120 }}>
                <Option value="rating">评分优先</Option>
                <Option value="hourly_rate">价格从低到高</Option>
                <Option value="hours">工作时长</Option>
                <Option value="newest">最新发布</Option>
              </Select>
            }
          >
            {mockEmployees.length > 0 ? (
              <Row gutter={[16, 16]}>
                {mockEmployees.map((employee) => (
                  <Col xs={24} sm={12} lg={8} key={employee.id}>
                    <EmployeeCard
                      employee={employee}
                      onHire={(emp) => console.log('Hire:', emp)}
                      onViewDetail={(emp) => console.log('View:', emp)}
                    />
                  </Col>
                ))}
              </Row>
            ) : (
              <Empty description="暂无符合条件的 AI 员工" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Marketplace;
