/**
 * ECharts 可视化组件
 *
 * 包含:
 * - 投资关系图谱
 * - 股权穿透树图
 * - 趋势图表
 * - 投资链桑基图
 */

// ==================== 投资关系图谱 ====================
/**
 * 创建投资关系网络图
 * @param {Object} container - DOM 容器
 * @param {Array} nodes - 节点数据 [{id, name, type, category, size}]
 * @param {Array} edges - 边数据 [{source, target, type, value, label}]
 */
export function createInvestmentNetworkChart(container, nodes, edges) {
    const chart = echarts.init(container);

    const categories = [];
    const categorySet = new Set();
    nodes.forEach(node => {
        if (!categorySet.has(node.category)) {
            categorySet.add(node.category);
            categories.push({ name: node.category });
        }
    });

    const option = {
        title: {
            text: '投资关系网络',
            top: 'bottom',
            left: 'right'
        },
        tooltip: {
            formatter: function(params) {
                if (params.dataType === 'edge') {
                    return `${params.data.source} → ${params.data.target}<br/>${params.data.label}`;
                }
                return `${params.data.name}<br/>类型：${params.data.category}<br/>连接数：${params.data.value || 'N/A'}`;
            }
        },
        legend: [{
            data: categories.map(c => c.name),
            selected: {},
            bottom: 10,
            left: 'center'
        }],
        animationDuration: 1500,
        animationEasingUpdate: 'quinticInOut',
        series: [{
            name: '投资关系网络',
            type: 'graph',
            layout: 'force',
            data: nodes.map(node => ({
                id: node.id,
                name: node.name,
                symbolSize: node.size || 20,
                category: categories.findIndex(c => c.name === node.category),
                value: node.value || 0,
                draggable: true,
                itemStyle: {
                    color: getCategoryColor(node.type)
                }
            })),
            links: edges.map(edge => ({
                source: edge.source,
                target: edge.target,
                value: edge.label,
                symbol: ['none', 'arrow'],
                lineStyle: {
                    width: Math.min(5, Math.max(1, edge.value / 100000000 || 1)),
                    curveness: 0.3
                }
            })),
            categories: categories,
            roam: true,
            label: {
                position: 'right',
                formatter: '{b}',
                fontSize: 10
            },
            lineStyle: {
                color: 'source',
                curveness: 0.3
            },
            emphasis: {
                focus: 'adjacency',
                lineStyle: {
                    width: 5
                }
            },
            force: {
                repulsion: 500,
                edgeLength: 100,
                gravity: 0.1
            }
        }]
    };

    chart.setOption(option);

    // 响应式调整
    window.addEventListener('resize', () => chart.resize());

    return chart;
}

// ==================== 股权穿透图 ====================
/**
 * 创建股权穿透图（树图）
 * @param {Object} container - DOM 容器
 * @param {Object} treeData - 树形数据 {name, children, ratio, type}
 */
export function createEquityTreeChart(container, treeData) {
    const chart = echarts.init(container);

    // 转换为 ECharts 树图格式
    function convertTree(node) {
        return {
            name: node.name,
            value: node.ratio || 0,
            type: node.type,
            children: node.children ? node.children.map(convertTree) : null
        };
    }

    const data = convertTree(treeData);

    const option = {
        title: {
            text: '股权穿透图',
            left: 'center'
        },
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                return `${params.name}<br/>持股比例：${params.value}%<br/>类型：${params.data.type || '未知'}`;
            }
        },
        series: [{
            type: 'tree',
            data: [data],
            top: '10%',
            left: '10%',
            bottom: '10%',
            right: '20%',
            symbol: 'emptyCircle',
            symbolSize: 12,
            label: {
                position: 'left',
                verticalAlign: 'middle',
                align: 'right',
                fontSize: 11,
                formatter: '{b}: {c}%'
            },
            leaves: {
                label: {
                    position: 'right',
                    verticalAlign: 'middle',
                    align: 'left'
                }
            },
            emphasis: {
                focus: 'descendant'
            },
            expandAndCollapse: true,
            animationDuration: 550,
            animationDurationUpdate: 750,
            lineStyle: {
                color: '#ccc',
                width: 2,
                curveness: 0.5
            }
        }]
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());

    return chart;
}

// ==================== 投资趋势图 ====================
/**
 * 创建投资趋势图（折线图 + 柱状图）
 * @param {Object} container - DOM 容器
 * @param {Object} options - 配置选项
 * @param {Array} options.dates - 日期数组
 * @param {Array} options.counts - 投资数量
 * @param {Array} options.amounts - 投资金额
 * @param {Array} options.forecast - 预测数据 [{date, prediction, lower, upper}]
 */
export function createInvestmentTrendChart(container, options) {
    const chart = echarts.init(container);

    const { dates, counts, amounts, forecast = [] } = options;

    // 分离预测数据
    const forecastDates = forecast.map(f => f.date);
    const forecastValues = forecast.map(f => f.prediction);
    const forecastLower = forecast.map(f => f.lower_bound);
    const forecastUpper = forecast.map(f => f.upper_bound);

    // 合并历史和预测日期
    const allDates = [...dates, ...forecastDates.filter(d => !dates.includes(d))];

    // 创建历史数据系列（对齐所有日期）
    const alignedCounts = allDates.map(d => {
        const idx = dates.indexOf(d);
        return idx >= 0 ? counts[idx] : null;
    });

    const alignedAmounts = allDates.map(d => {
        const idx = dates.indexOf(d);
        return idx >= 0 ? amounts[idx] : null;
    });

    const option = {
        title: {
            text: '投资趋势与预测',
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        legend: {
            data: ['投资数量', '投资金额', '预测', '置信区间'],
            bottom: 10
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: allDates,
            axisLabel: {
                rotate: 45
            }
        },
        yAxis: [
            {
                type: 'value',
                name: '投资数量',
                position: 'left'
            },
            {
                type: 'value',
                name: '投资金额 (百万)',
                position: 'right',
                axisLabel: {
                    formatter: function(value) {
                        return (value / 1000000).toFixed(0) + 'M';
                    }
                }
            }
        ],
        series: [
            {
                name: '投资数量',
                type: 'bar',
                data: alignedCounts,
                itemStyle: {
                    color: '#5470c6'
                }
            },
            {
                name: '投资金额',
                type: 'line',
                yAxisIndex: 1,
                data: alignedAmounts,
                itemStyle: {
                    color: '#91cc75'
                },
                smooth: true
            },
            {
                name: '预测',
                type: 'line',
                data: forecastValues.length > 0 ?
                    [...new Array(dates.length).fill(null), ...forecastValues] :
                    forecastValues,
                itemStyle: {
                    color: '#fac858'
                },
                lineStyle: {
                    type: 'dashed'
                },
                symbol: 'circle',
                symbolSize: 8
            },
            {
                name: '置信区间',
                type: 'line',
                data: forecastUpper.length > 0 ?
                    [...new Array(dates.length).fill(null), ...forecastUpper] :
                    forecastUpper,
                itemStyle: {
                    color: '#fac858'
                },
                lineStyle: {
                    type: 'dotted',
                    width: 1
                },
                symbol: 'none'
            }
        ]
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());

    return chart;
}

// ==================== 投资链桑基图 ====================
/**
 * 创建投资链桑基图
 * @param {Object} container - DOM 容器
 * @param {Array} investments - 投资数据 [{investor, investee, amount}]
 */
export function createInvestmentSankeyChart(container, investments) {
    const chart = echarts.init(container);

    // 构建节点和边
    const nodeMap = new Map();
    const links = [];

    investments.forEach(inv => {
        if (!nodeMap.has(inv.investor)) {
            nodeMap.set(inv.investor, { name: inv.investor, type: 'investor' });
        }
        if (!nodeMap.has(inv.investee)) {
            nodeMap.set(inv.investee, { name: inv.investee, type: 'investee' });
        }

        links.push({
            source: inv.investor,
            target: inv.investee,
            value: inv.amount || 1
        });
    });

    const nodes = Array.from(nodeMap.values()).map(node => ({
        name: node.name,
        itemStyle: {
            color: node.type === 'investor' ? '#91cc75' : '#5470c6'
        }
    }));

    const option = {
        title: {
            text: '投资流向桑基图',
            left: 'center'
        },
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                if (params.data.source) {
                    return `${params.data.source} → ${params.data.target}<br/>金额：${formatAmount(params.data.value)}`;
                }
                return `${params.name}<br/>类型：${nodeMap.get(params.name)?.type || '未知'}`;
            }
        },
        series: [{
            type: 'sankey',
            layout: 'none',
            emphasis: {
                focus: 'adjacency'
            },
            data: nodes,
            links: links,
            lineStyle: {
                color: 'gradient',
                curveness: 0.5,
                opacity: 0.7
            },
            label: {
                position: 'right',
                formatter: '{b}'
            }
        }]
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());

    return chart;
}

// ==================== 行业对比雷达图 ====================
/**
 * 创建行业对比雷达图
 * @param {Object} container - DOM 容器
 * @param {Array} industries - 行业数据 [{name, scores: {growth, activity, diversity, scale}}]
 */
export function createIndustryRadarChart(container, industries) {
    const chart = echarts.init(container);

    const indicator = [
        { name: '增长潜力', max: 100 },
        { name: '投资活跃度', max: 100 },
        { name: '投资者多样性', max: 100 },
        { name: '投资规模', max: 100 },
        { name: '市场情绪', max: 100 }
    ];

    const series = industries.map(industry => ({
        name: industry.name,
        type: 'radar',
        data: [{
            value: [
                industry.scores.growth || 50,
                industry.scores.activity || 50,
                industry.scores.diversity || 50,
                industry.scores.scale || 50,
                industry.scores.sentiment || 50
            ],
            name: industry.name
        }]
    }));

    const option = {
        title: {
            text: '行业对比分析',
            left: 'center'
        },
        legend: {
            data: industries.map(i => i.name),
            bottom: 10
        },
        radar: {
            indicator: indicator,
            radius: '65%'
        },
        series: series
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());

    return chart;
}

// ==================== 工具函数 ====================
function getCategoryColor(type) {
    const colors = {
        investor: '#91cc75',
        investee: '#5470c6',
        individual: '#fac858',
        corporate: '#ee6666',
        government: '#73c0de'
    };
    return colors[type] || '#3ba272';
}

function formatAmount(amount) {
    if (amount >= 100000000) {
        return (amount / 100000000).toFixed(2) + '亿';
    } else if (amount >= 10000) {
        return (amount / 10000).toFixed(2) + '万';
    }
    return amount.toString();
}

// 导出 Chart.js 辅助函数
export function createChartJSTrendChart(canvasId, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: data.datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: data.title || '趋势图'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000000) {
                                return (value / 1000000).toFixed(1) + 'M';
                            }
                            return value;
                        }
                    }
                }
            }
        }
    });
}
