/**
 * 人才市场页面 - Bento Grid 重构版
 */
import React, { useState, useMemo } from 'react';
import { Input, Select, Slider, Checkbox, Typography, Space, Button, Empty, Tag, Avatar } from 'antd';
import {
  SearchOutlined,
  ThunderboltOutlined,
  StarOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  UserOutlined,
  FireOutlined,
} from '@ant-design/icons';
import { BentoGrid, BentoCard, StatMetric, TrendIndicator } from '@/components/bento';
import { useMarketplace } from '@/hooks';
import { type MarketplaceFilters } from '@/services/marketplaceApi';
import type { AIEmployee } from '@/types/employee';
import './Marketplace.less';

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

  // 模拟数据
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
      skills: { Python: 'expert', Pandas: 'expert', SQL: 'advanced', 可视化: 'advanced' },
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
      skills: { 沟通: 'expert', 多语言: 'expert', 问题解决: 'advanced' },
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
      skills: { Copywriting: 'expert', SEO: 'advanced', 社交媒体: 'advanced' },
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

  // 状态标签颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available':
        return 'success';
      case 'busy':
        return 'processing';
      case 'unavailable':
        return 'default';
      default:
        return 'default';
    }
  };

  // 获取技能标签
  const getSkillTags = (skills: Record<string, string>) => {
    return Object.entries(skills).slice(0, 3).map(([skill, level]) => ({
      name: skill,
      level,
    }));
  };

  return (
    <BentoGrid
      title="人才市场"
      description="发现和雇佣专业的 AI 员工"
      maxColumns={4}
      gap="md"
      extra={
        <Space>
          <Button type="primary">发布需求</Button>
        </Space>
      }
    >
      {/* 统计卡片区 - 4 个 1x1 卡片 */}
      <BentoCard size="1x1">
        <StatMetric
          label="AI 员工总数"
          value={256}
          suffix="人"
          trend={12}
          trendType="up"
          icon={<ThunderboltOutlined style={{ color: '#2979ff' }} />}
        />
      </BentoCard>

      <BentoCard size="1x1">
        <StatMetric
          label="今日新增"
          value={12}
          suffix="人"
          trend={8}
          trendType="up"
          icon={<FireOutlined style={{ color: '#ff5252' }} />}
        />
      </BentoCard>

      <BentoCard size="1x1">
        <StatMetric
          label="平均评分"
          value={4.6}
          suffix="分"
          icon={<StarOutlined style={{ color: '#ffb300' }} />}
        />
      </BentoCard>

      <BentoCard size="1x1">
        <StatMetric
          label="平均时薪"
          value={65}
          prefix="¥"
          suffix="/小时"
          trend={5}
          trendType="down"
          icon={<DollarOutlined style={{ color: '#00c853' }} />}
        />
      </BentoCard>

      {/* 筛选面板 - 1x2 卡片 */}
      <BentoCard
        size="1x2"
        title="筛选条件"
        icon={<SearchOutlined />}
      >
        <div className="marketplace-filters">
          <div className="filter-group">
            <label className="filter-label">关键词搜索</label>
            <Input
              placeholder="输入技能或描述"
              prefix={<SearchOutlined />}
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
              size="large"
            />
          </div>

          <div className="filter-group">
            <label className="filter-label">分类</label>
            <Select
              placeholder="选择分类"
              style={{ width: '100%' }}
              value={selectedCategory}
              onChange={setSelectedCategory}
              allowClear
              size="large"
            >
              {categories.map((cat) => (
                <Option key={cat.value} value={cat.value}>
                  {cat.label}
                </Option>
              ))}
            </Select>
          </div>

          <div className="filter-group">
            <label className="filter-label">时薪范围 (¥)</label>
            <Slider
              range
              min={0}
              max={1000}
              value={priceRange}
              onChange={(value) => setPriceRange(value as [number, number])}
            />
            <div className="filter-range-text">
              <span>¥{priceRange[0]}</span>
              <span>¥{priceRange[1]}+</span>
            </div>
          </div>

          <div className="filter-group">
            <label className="filter-label">最低评分</label>
            <Slider
              min={0}
              max={5}
              step={0.5}
              value={minRating}
              onChange={(value) => setMinRating(value as number)}
            />
            <div className="filter-rating-text">
              <span>{minRating === 0 ? '不限' : `${minRating}分+`}</span>
            </div>
          </div>

          <div className="filter-checkbox-group">
            <Checkbox checked={availableOnly} onChange={(e) => setAvailableOnly(e.target.checked)}>
              只看可雇佣
            </Checkbox>
          </div>

          <div className="filter-actions">
            <Button type="primary" onClick={handleSearch} block size="large">
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
              size="large"
            >
              重置
            </Button>
          </div>
        </div>
      </BentoCard>

      {/* 员工列表 - 3x2 大卡片 */}
      <BentoCard
        size="3x2"
        title="AI 员工列表"
        icon={<UserOutlined />}
        extra={
          <Select defaultValue="rating" style={{ width: 120 }} size="small">
            <Option value="rating">评分优先</Option>
            <Option value="hourly_rate">价格从低到高</Option>
            <Option value="hours">工作时长</Option>
            <Option value="newest">最新发布</Option>
          </Select>
        }
      >
        {mockEmployees.length > 0 ? (
          <div className="employee-grid">
            {mockEmployees.map((employee) => (
              <div key={employee.id} className="employee-card-bento">
                <div className="employee-card-header">
                  <div className="employee-card-avatar">
                    <Avatar
                      size={48}
                      style={{ backgroundColor: '#7c3aed' }}
                      icon={<UserOutlined />}
                    />
                    <Tag
                      color={getStatusColor(employee.status)}
                      className="employee-status-tag"
                    >
                      {employee.status === 'available' ? '可雇佣' :
                       employee.status === 'busy' ? '工作中' : '不可用'}
                    </Tag>
                  </div>
                  <div className="employee-card-rating">
                    <StarOutlined className="rating-star" />
                    {employee.rating.toFixed(1)}
                  </div>
                </div>

                <div className="employee-card-body">
                  <h4 className="employee-card-name">{employee.name}</h4>
                  <p className="employee-card-desc">{employee.description}</p>

                  <div className="employee-card-skills">
                    {getSkillTags(employee.skills).map((skill, i) => (
                      <Tag key={i} color="default" className="skill-tag">
                        {skill.name}
                      </Tag>
                    ))}
                  </div>
                </div>

                <div className="employee-card-footer">
                  <div className="employee-metric">
                    <ClockCircleOutlined className="metric-icon" />
                    <span>{employee.total_hours_worked}小时</span>
                  </div>
                  <div className="employee-metric">
                    <DollarOutlined className="metric-icon" />
                    <span>¥{employee.hourly_rate}/h</span>
                  </div>
                </div>

                <div className="employee-card-actions">
                  <Button type="primary" block>
                    立即雇佣
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty description="暂无符合条件的 AI 员工" />
        )}
      </BentoCard>
    </BentoGrid>
  );
};

export default Marketplace;
