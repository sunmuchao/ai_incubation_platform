/**
 * 图表组件封装
 */
import React from 'react';
import ReactECharts, { type EChartsOption } from 'echarts-for-react';
import { Card, type CardProps } from 'antd';

interface ChartCardProps extends CardProps {
  option: EChartsOption;
  loading?: boolean;
  height?: number | string;
  title?: string;
  extra?: React.ReactNode;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  option,
  loading = false,
  height = 300,
  title,
  extra,
  ...cardProps
}) => {
  return (
    <Card
      title={title}
      loading={loading}
      extra={extra}
      {...cardProps}
    >
      <ReactECharts
        option={option}
        style={{ height }}
        notMerge={true}
        lazyUpdate={true}
        theme="light"
      />
    </Card>
  );
};

/**
 * 柱状图配置生成器
 */
export const createBarChartOption = (
  categories: string[],
  data: number[],
  title?: string,
  color = '#5470c6'
): EChartsOption => ({
  title: title ? { text: title, left: 'center' } : undefined,
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
  },
  xAxis: {
    type: 'category',
    data: categories,
    axisLabel: { interval: 0, rotate: 30 },
  },
  yAxis: {
    type: 'value',
  },
  series: [
    {
      name: title,
      type: 'bar',
      data,
      itemStyle: { color },
      label: {
        show: true,
        position: 'top',
      },
    },
  ],
  grid: {
    left: '3%',
    right: '4%',
    bottom: '15%',
    containLabel: true,
  },
});

/**
 * 折线图配置生成器
 */
export const createLineChartOption = (
  categories: string[],
  data: number[],
  title?: string,
  color = '#5470c6'
): EChartsOption => ({
  title: title ? { text: title, left: 'center' } : undefined,
  tooltip: {
    trigger: 'axis',
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: categories,
  },
  yAxis: {
    type: 'value',
  },
  series: [
    {
      name: title,
      type: 'line',
      data,
      itemStyle: { color },
      areaStyle: {
        color: new (require('echarts/lib/util/graphic')).LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: color + '40' },
          { offset: 1, color: color + '05' },
        ]),
      },
      smooth: true,
    },
  ],
});

/**
 * 饼图配置生成器
 */
export const createPieChartOption = (
  data: { name: string; value: number }[],
  title?: string,
  center?: [string, string]
): EChartsOption => ({
  title: title ? { text: title, left: 'center' } : undefined,
  tooltip: {
    trigger: 'item',
    formatter: '{a} <br/>{b}: {c} ({d}%)',
  },
  legend: {
    orient: 'vertical',
    left: 'left',
  },
  series: [
    {
      name: title,
      type: 'pie',
      radius: '50%',
      center: center || ['50%', '60%'],
      data,
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)',
        },
      },
      label: {
        formatter: '{b}: {d}%',
      },
    },
  ],
});

export default ChartCard;
