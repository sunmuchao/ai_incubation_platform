/**
 * MiniChart - 迷你图表组件
 * 用于 Bento Card 中的小型可视化
 */
import React, { useMemo } from 'react';
import ReactECharts, { type EChartsOption } from 'echarts-for-react';
import './MiniChart.less';

export interface MiniChartProps {
  /** 图表类型 */
  type?: 'line' | 'area' | 'bar' | 'progress';
  /** 图表数据 */
  data: number[];
  /** 图表颜色 */
  color?: string;
  /** 图表高度 */
  height?: number;
  /** 是否显示渐变 */
  gradient?: boolean;
  /** 是否平滑曲线 */
  smooth?: boolean;
  /** 进度值 (用于 progress 类型) */
  progressValue?: number;
  /** 自定义类名 */
  className?: string;
}

export const MiniChart: React.FC<MiniChartProps> = ({
  type = 'line',
  data,
  color = '#7c3aed',
  height = 60,
  gradient = true,
  smooth = true,
  progressValue,
  className = '',
}) => {
  const chartOption = useMemo((): EChartsOption => {
    const commonOption: EChartsOption = {
      grid: { left: 0, right: 0, top: 0, bottom: 0 },
      xAxis: { show: false, type: 'category' },
      yAxis: { show: false, type: 'value' },
      tooltip: { show: false },
    };

    if (type === 'progress') {
      return {
        ...commonOption,
        series: [
          {
            type: 'gauge',
            progress: { show: true, width: 6 },
            axisLine: { lineStyle: { width: 6, color: [[1, '#f0f2f5']] } },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { show: false },
            pointer: { show: false },
            data: [{ value: progressValue ?? 0, name: '' }],
            detail: { show: false },
          },
        ],
      };
    }

    if (type === 'bar') {
      return {
        ...commonOption,
        series: [
          {
            type: 'bar',
            data,
            itemStyle: {
              color,
              borderRadius: [4, 4, 0, 0],
            },
            barGap: 2,
            barCategoryGap: '20%',
          },
        ],
      };
    }

    // line 或 area
    const seriesConfig: any = {
      type: 'line',
      data,
      smooth,
      showSymbol: false,
      lineStyle: {
        color,
        width: 2,
      },
    };

    if (type === 'area' || gradient) {
      seriesConfig.areaStyle = {
        color: new (require('echarts/lib/util/graphic')).LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: color + '40' },
          { offset: 1, color: color + '05' },
        ]),
      };
    }

    return {
      ...commonOption,
      series: [seriesConfig],
    };
  }, [type, data, color, smooth, gradient, progressValue]);

  return (
    <div
      className={`mini-chart mini-chart--${type} ${className}`}
      style={{ height }}
    >
      <ReactECharts
        option={chartOption}
        style={{ height: '100%' }}
        notMerge={true}
        lazyUpdate={true}
        theme="light"
      />
    </div>
  );
};

export default MiniChart;
