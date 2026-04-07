/**
 * 快速查询面板 - Bento Grid 风格重构
 * 提供常用查询模板和智能建议
 */
import React, { useState } from 'react'
import { Input, Empty } from 'antd'
import {
  ThunderboltOutlined,
  SearchOutlined,
  HistoryOutlined,
  TableOutlined,
  BarChartOutlined,
  LineChartOutlined,
  FilterOutlined,
  RocketOutlined,
  ArrowUpOutlined,
  RightOutlined,
} from '@ant-design/icons'

// 查询模板类型
interface QueryTemplate {
  id: string
  name: string
  description: string
  query: string
  category: 'explore' | 'aggregate' | 'trend' | 'comparison' | 'anomaly'
  icon: React.ReactNode
  difficulty: 'easy' | 'medium' | 'hard'
}

interface QuickQueryPanelProps {
  onSelectQuery?: (query: string) => void
}

// 查询模板库
const QUERY_TEMPLATES: QueryTemplate[] = [
  {
    id: 'explore-table',
    name: '探索表结构',
    description: '查看表的所有数据和结构',
    query: '查看表的所有数据，显示前 100 条记录',
    category: 'explore',
    icon: <TableOutlined />,
    difficulty: 'easy',
  },
  {
    id: 'explore-schema',
    name: '查看 Schema',
    description: '获取表的字段信息',
    query: '显示表的字段结构',
    category: 'explore',
    icon: <SearchOutlined />,
    difficulty: 'easy',
  },
  {
    id: 'aggregate-count',
    name: '统计总数',
    description: '计算记录总数',
    query: '统计表的总记录数',
    category: 'aggregate',
    icon: <ThunderboltOutlined />,
    difficulty: 'easy',
  },
  {
    id: 'aggregate-sum',
    name: '求和统计',
    description: '对数值字段求和',
    query: '计算表中某字段的总和',
    category: 'aggregate',
    icon: <ThunderboltOutlined />,
    difficulty: 'medium',
  },
  {
    id: 'aggregate-group',
    name: '分组统计',
    description: '按维度分组汇总',
    query: '按维度分组，统计每个组的总和',
    category: 'aggregate',
    icon: <BarChartOutlined />,
    difficulty: 'medium',
  },
  {
    id: 'trend-time',
    name: '时间趋势',
    description: '分析时间序列趋势',
    query: '分析某字段按时间的趋势变化',
    category: 'trend',
    icon: <LineChartOutlined />,
    difficulty: 'medium',
  },
  {
    id: 'comparison-rank',
    name: '排行榜',
    description: '找出 top N 记录',
    query: '找出某字段最高的前 10 条记录',
    category: 'comparison',
    icon: <RocketOutlined />,
    difficulty: 'easy',
  },
  {
    id: 'comparison-compare',
    name: '对比分析',
    description: '对比不同时间段或类别',
    query: '对比两个时间段的差异',
    category: 'comparison',
    icon: <BarChartOutlined />,
    difficulty: 'hard',
  },
  {
    id: 'anomaly-detect',
    name: '异常检测',
    description: '发现异常数据点',
    query: '找出表中的异常值',
    category: 'anomaly',
    icon: <FilterOutlined />,
    difficulty: 'hard',
  },
  {
    id: 'anomaly-change',
    name: '变化分析',
    description: '分析显著变化',
    query: '分析环比变化最大的记录',
    category: 'anomaly',
    icon: <ArrowUpOutlined />,
    difficulty: 'hard',
  },
]

// 类别配置
const CATEGORY_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  all: { label: '全部', icon: <ThunderboltOutlined />, color: 'slate' },
  explore: { label: '探索', icon: <SearchOutlined />, color: 'indigo' },
  aggregate: { label: '汇总', icon: <BarChartOutlined />, color: 'emerald' },
  trend: { label: '趋势', icon: <LineChartOutlined />, color: 'amber' },
  comparison: { label: '对比', icon: <BarChartOutlined />, color: 'violet' },
  anomaly: { label: '异常', icon: <FilterOutlined />, color: 'rose' },
}

/**
 * 快速查询面板 - Bento Grid 版本
 */
export const QuickQueryPanel: React.FC<QuickQueryPanelProps> = ({
  onSelectQuery,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [searchText, setSearchText] = useState('')

  // 过滤模板
  const filteredTemplates = QUERY_TEMPLATES.filter(template => {
    const matchCategory = selectedCategory === 'all' || template.category === selectedCategory
    const matchSearch = !searchText ||
      template.name.toLowerCase().includes(searchText.toLowerCase()) ||
      template.description.toLowerCase().includes(searchText.toLowerCase())
    return matchCategory && matchSearch
  })

  // 获取难度颜色
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'bg-emerald-50 text-emerald-700 border-emerald-100'
      case 'medium': return 'bg-amber-50 text-amber-700 border-amber-100'
      case 'hard': return 'bg-rose-50 text-rose-700 border-rose-100'
      default: return 'bg-slate-50 text-slate-600 border-slate-100'
    }
  }

  // 获取难度文本
  const getDifficultyText = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '简单'
      case 'medium': return '中等'
      case 'hard': return '困难'
      default: return difficulty
    }
  }

  // 获取类别颜色
  const getCategoryColor = (color: string, isSelected: boolean) => {
    if (isSelected) {
      switch (color) {
        case 'indigo': return 'bg-indigo-500 text-white border-indigo-600'
        case 'emerald': return 'bg-emerald-500 text-white border-emerald-600'
        case 'amber': return 'bg-amber-500 text-white border-amber-600'
        case 'violet': return 'bg-violet-500 text-white border-violet-600'
        case 'rose': return 'bg-rose-500 text-white border-rose-600'
        default: return 'bg-slate-700 text-white border-slate-800'
      }
    }
    switch (color) {
      case 'indigo': return 'bg-indigo-50 text-indigo-600 border-indigo-100 hover:border-indigo-300'
      case 'emerald': return 'bg-emerald-50 text-emerald-600 border-emerald-100 hover:border-emerald-300'
      case 'amber': return 'bg-amber-50 text-amber-600 border-amber-100 hover:border-amber-300'
      case 'violet': return 'bg-violet-50 text-violet-600 border-violet-100 hover:border-violet-300'
      case 'rose': return 'bg-rose-50 text-rose-600 border-rose-100 hover:border-rose-300'
      default: return 'bg-slate-50 text-slate-600 border-slate-100 hover:border-slate-300'
    }
  }

  // 处理模板选择
  const handleTemplateSelect = (template: QueryTemplate) => {
    onSelectQuery?.(template.query)
  }

  return (
    <div className="space-y-3">
      {/* 搜索框 */}
      <div className="relative">
        <SearchOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="搜索查询模板..."
          className="input-linear pl-10"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
        />
      </div>

      {/* 类别筛选 - 胶囊式按钮 */}
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(CATEGORY_CONFIG).map(([_, config]) => (
          <button
            key={config.label}
            onClick={() => setSelectedCategory(config.label === '全部' ? 'all' : config.label.toLowerCase())}
            className={`
              inline-flex items-center px-3 py-1.5 rounded-full
              text-xs font-medium transition-all duration-200
              border cursor-pointer
              ${getCategoryColor(config.color, selectedCategory === (config.label === '全部' ? 'all' : config.label.toLowerCase()))}
            `}
          >
            <span className="mr-1.5">{config.icon}</span>
            {config.label}
          </button>
        ))}
      </div>

      {/* 查询模板列表 */}
      {filteredTemplates.length === 0 ? (
        <Empty
          description="没有找到匹配的模板"
          imageStyle={{ height: 60 }}
        />
      ) : (
        <div className="grid grid-cols-1 gap-2">
          {filteredTemplates.map((template) => (
            <div
              key={template.id}
              onClick={() => handleTemplateSelect(template)}
              className="
                group p-3 rounded-linear border border-slate-200
                bg-white hover:bg-slate-50
                hover:border-indigo-200 hover:shadow-linear
                cursor-pointer transition-all duration-200
              "
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1 min-w-0">
                  {/* 图标 */}
                  <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-50 to-indigo-100 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                    <span className="text-indigo-600 text-lg">
                      {template.icon}
                    </span>
                  </div>

                  {/* 内容 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h4 className="font-medium text-slate-800 text-sm group-hover:text-indigo-600 transition-colors">
                        {template.name}
                      </h4>
                      <span className={`text-xs px-1.5 py-0.5 rounded border ${getDifficultyColor(template.difficulty)}`}>
                        {getDifficultyText(template.difficulty)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5 truncate">
                      {template.description}
                    </p>
                    <p className="text-xs text-slate-400 mt-1.5 line-clamp-1 font-mono bg-slate-50 px-2 py-1 rounded">
                      {template.query}
                    </p>
                  </div>
                </div>

                {/* 箭头 */}
                <RightOutlined className="text-slate-300 group-hover:text-indigo-400 transition-colors mt-1" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 查询历史占位 */}
      <div className="pt-3 border-t border-slate-100">
        <div className="flex items-center space-x-2 text-slate-500 text-xs">
          <HistoryOutlined />
          <span>查询历史将在对话后自动保存</span>
        </div>
      </div>
    </div>
  )
}

export default QuickQueryPanel
