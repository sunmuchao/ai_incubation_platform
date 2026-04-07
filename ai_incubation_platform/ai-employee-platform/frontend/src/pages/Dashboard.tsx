/**
 * 工作台页面 - Bento Grid 重构版
 * 采用模块化网格布局，Monochromatic 配色
 */
import React, { useState, useEffect } from 'react';
import { Tag, Space, Typography } from 'antd';
import {
  TeamOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  RiseOutlined,
  FireOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { BentoGrid, BentoCard, StatMetric, MiniChart, TrendIndicator } from '@/components/bento';
import './Dashboard.less';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  const [_loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    totalEmployees: 24,
    availableEmployees: 18,
    totalHours: 1280,
    totalRevenue: 45600,
    avgRating: 4.6,
  });

  // 获取统计数据
  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true);
      try {
        setStats({
          totalEmployees: 24,
          availableEmployees: 18,
          totalHours: 1280,
          totalRevenue: 45600,
          avgRating: 4.6,
        });
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  // 员工状态分布数据
  const employeeStatusData = [
    { name: '可雇佣', value: stats.availableEmployees, color: '#00c853' },
    { name: '工作中', value: 4, color: '#2979ff' },
    { name: '不可用', value: 2, color: '#9aa3b0' },
  ];

  // 收入趋势数据
  const revenueTrendData = [12000, 15000, 18000, 22000, 28000, stats.totalRevenue];

  // 热门员工数据
  const topEmployeesData = [
    { rank: 1, name: '数据分析助手', skills: ['Python', 'SQL'], rating: 4.9, revenue: 15600, trend: 15 },
    { rank: 2, name: '客服机器人', skills: ['沟通', '多语言'], rating: 4.8, revenue: 12800, trend: 12 },
    { rank: 3, name: '代码审查助手', skills: ['CodeReview', 'Security'], rating: 4.8, revenue: 11200, trend: 8 },
    { rank: 4, name: '文档生成器', skills: ['Writing', 'TechDoc'], rating: 4.7, revenue: 9600, trend: 5 },
    { rank: 5, name: '图像识别专家', skills: ['CV', 'PyTorch'], rating: 4.6, revenue: 8400, trend: 3 },
  ];

  // 任务完成情况
  const taskData = [
    { type: '数据分析', completed: 156, inProgress: 8, rate: 95 },
    { type: '内容创作', completed: 89, inProgress: 12, rate: 88 },
    { type: '代码开发', completed: 67, inProgress: 15, rate: 82 },
    { type: '客户服务', completed: 234, inProgress: 6, rate: 97 },
  ];

  return (
    <BentoGrid
      title="工作台"
      description="欢迎回来，这里是您的 AI 员工管理平台"
      maxColumns={4}
      gap="md"
    >
      {/* 统计卡片行 - 4 个 1x1 卡片 */}
      <BentoCard size="1x1" icon={<TeamOutlined />}>
        <StatMetric
          label="AI 员工总数"
          value={stats.totalEmployees}
          suffix="人"
          trend={12}
          trendType="up"
          icon={<TeamOutlined style={{ color: '#2979ff' }} />}
        />
      </BentoCard>

      <BentoCard size="1x1" icon={<CheckCircleOutlined />}>
        <StatMetric
          label="可雇佣员工"
          value={stats.availableEmployees}
          suffix="人"
          trend={8}
          trendType="up"
          icon={<CheckCircleOutlined style={{ color: '#00c853' }} />}
        />
      </BentoCard>

      <BentoCard size="1x1" icon={<ClockCircleOutlined />}>
        <StatMetric
          label="总工作时长"
          value={stats.totalHours}
          suffix="小时"
          trend={25}
          trendType="up"
          icon={<ClockCircleOutlined style={{ color: '#ffb300' }} />}
        />
      </BentoCard>

      <BentoCard size="1x1" icon={<DollarOutlined />}>
        <StatMetric
          label="总收入"
          value={stats.totalRevenue.toLocaleString()}
          prefix="¥"
          trend={18}
          trendType="up"
          icon={<DollarOutlined style={{ color: '#00c853' }} />}
        />
      </BentoCard>

      {/* 员工状态分布 - 2x2 卡片 */}
      <BentoCard
        size="2x2"
        title="员工状态分布"
        icon={<TeamOutlined />}
        extra={
          <Tag color="blue" style={{ borderRadius: 6 }}>
            实时
          </Tag>
        }
      >
        <div className="employee-status-chart">
          {employeeStatusData.map((item, index) => (
            <div key={index} className="status-item">
              <div className="status-info">
                <span
                  className="status-dot"
                  style={{ backgroundColor: item.color }}
                />
                <span className="status-label">{item.name}</span>
              </div>
              <div className="status-value">
                <span className="status-count">{item.value}</span>
                <span className="status-unit">人</span>
              </div>
            </div>
          ))}
          {/* 环形图可视化占位 */}
          <div className="status-chart-placeholder">
            <MiniChart
              type="progress"
              data={[60]}
              progressValue={(stats.availableEmployees / stats.totalEmployees) * 100}
              color="#00c853"
              height={120}
            />
          </div>
        </div>
      </BentoCard>

      {/* 收入趋势 - 2x2 卡片 */}
      <BentoCard
        size="2x2"
        title="月收入趋势"
        icon={<RiseOutlined />}
        extra={
          <TrendIndicator value={18.5} size="sm" />
        }
      >
        <div className="revenue-chart">
          <div className="revenue-highlights">
            <div className="highlight-item">
              <span className="highlight-label">最高</span>
              <span className="highlight-value">¥{Math.max(...revenueTrendData).toLocaleString()}</span>
            </div>
            <div className="highlight-item">
              <span className="highlight-label">平均</span>
              <span className="highlight-value">¥{Math.round(revenueTrendData.reduce((a, b) => a + b, 0) / revenueTrendData.length).toLocaleString()}</span>
            </div>
          </div>
          <MiniChart
            type="area"
            data={revenueTrendData}
            color="#7c3aed"
            height={180}
            gradient
            smooth
          />
        </div>
      </BentoCard>

      {/* 热门员工 Top 5 - 3x2 卡片 */}
      <BentoCard
        size="3x2"
        title="热门员工 Top 5"
        icon={<TrophyOutlined />}
        accent
      >
        <div className="top-employees">
          {topEmployeesData.map((employee, index) => (
            <div key={index} className="top-employee-item">
              <div className="employee-rank">
                <span className={`rank-badge rank-${employee.rank}`}>
                  {employee.rank}
                </span>
              </div>
              <div className="employee-info">
                <div className="employee-name">{employee.name}</div>
                <div className="employee-skills">
                  <Space size={4}>
                    {employee.skills.map((skill, i) => (
                      <Tag key={i} color="default" style={{ borderRadius: 4, fontSize: 11 }}>
                        {skill}
                      </Tag>
                    ))}
                  </Space>
                </div>
              </div>
              <div className="employee-metrics">
                <div className="employee-rating">
                  <FireOutlined className="rating-icon" />
                  {employee.rating}
                </div>
                <div className="employee-revenue">
                  ¥{employee.revenue.toLocaleString()}
                </div>
                <div className="employee-trend">
                  <TrendIndicator value={employee.trend} size="sm" hideIcon />
                </div>
              </div>
            </div>
          ))}
        </div>
      </BentoCard>

      {/* 任务完成情况 - 1x2 卡片 */}
      <BentoCard
        size="1x2"
        title="任务完成率"
        icon={<CheckCircleOutlined />}
      >
        <div className="task-completion">
          {taskData.map((task, index) => (
            <div key={index} className="task-item">
              <div className="task-info">
                <span className="task-type">{task.type}</span>
                <span className="task-count">
                  {task.completed}/{task.completed + task.inProgress}
                </span>
              </div>
              <div className="task-progress">
                <div className="progress-bar">
                  <div
                    className={`progress-fill progress-fill--${task.rate >= 90 ? 'high' : task.rate >= 70 ? 'medium' : 'low'}`}
                    style={{ width: `${task.rate}%` }}
                  />
                </div>
                <span className="progress-rate">{task.rate}%</span>
              </div>
            </div>
          ))}
        </div>
      </BentoCard>
    </BentoGrid>
  );
};

export default Dashboard;
