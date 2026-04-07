/**
 * P6 - 可视化增强组件
 *
 * 新增图表：
 * 1. 商机评分雷达图
 * 2. 趋势预测图
 * 3. 供应链关系图
 * 4. 政策分布图
 * 5. 推荐引擎效果对比图
 */

// ==================== 商机评分雷达图 ====================

/**
 * 渲染商机多维度评分雷达图
 * @param {string} elementId - HTML 元素 ID
 * @param {Object} scoreData - 评分数据
 */
function renderOpportunityScoreRadar(elementId, scoreData) {
    const chart = echarts.init(document.getElementById(elementId));

    const option = {
        title: {
            text: '商机质量评分',
            left: 'center'
        },
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                return `${params.name}: ${params.value}分`;
            }
        },
        radar: {
            indicator: [
                { name: '置信度', max: 100 },
                { name: '风险', max: 100 },
                { name: '价值', max: 100 },
                { name: '紧迫性', max: 100 },
                { name: '可行性', max: 100 },
                { name: '战略匹配', max: 100 }
            ],
            radius: '65%'
        },
        series: [{
            name: '商机评分',
            type: 'radar',
            data: [
                {
                    value: [
                        scoreData.confidence_score || 0,
                        scoreData.risk_score || 0,
                        scoreData.value_score || 0,
                        scoreData.urgency_score || 0,
                        scoreData.feasibility_score || 0,
                        scoreData.strategic_fit_score || 0
                    ],
                    name: '综合评分',
                    areaStyle: {
                        color: 'rgba(64, 158, 255, 0.5)'
                    },
                    lineStyle: {
                        color: '#409EFF'
                    }
                }
            ]
        }],
        color: ['#409EFF']
    };

    chart.setOption(option);
    return chart;
}

// ==================== 趋势预测图 ====================

/**
 * 渲染趋势预测图（含历史数据和预测数据）
 * @param {string} elementId - HTML 元素 ID
 * @param {Object} trendData - 趋势数据
 */
function renderTrendPredictionChart(elementId, trendData) {
    const chart = echarts.init(document.getElementById(elementId));

    const dates = trendData.dates || [];
    const historicalValues = trendData.historical || [];
    const predictedValues = trendData.predicted || [];

    // 构建预测部分的日期（在历史日期后）
    const predictDates = dates.slice(-1).concat(trendData.predict_dates || []);

    const option = {
        title: {
            text: trendData.keyword ? `${trendData.keyword} 趋势预测` : '趋势预测',
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                let result = params[0].axisValue + '<br/>';
                params.forEach(param => {
                    const marker = param.marker || '●';
                    result += `${marker} ${param.seriesName}: ${param.value}<br/>`;
                });
                return result;
            }
        },
        legend: {
            data: ['历史数据', '预测数据'],
            top: 30
        },
        xAxis: {
            type: 'category',
            data: dates.concat(predictDates.slice(1)),
            axisLabel: {
                rotate: 45
            }
        },
        yAxis: {
            type: 'value',
            name: trendData.unit || '热度指数'
        },
        series: [
            {
                name: '历史数据',
                type: 'line',
                data: historicalValues,
                smooth: true,
                lineStyle: {
                    color: '#67C23A',
                    width: 3
                },
                itemStyle: {
                    color: '#67C23A'
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
                        { offset: 1, color: 'rgba(103, 194, 58, 0.01)' }
                    ])
                }
            },
            {
                name: '预测数据',
                type: 'line',
                data: new Array(historicalValues.length - 1).fill(null).concat(
                    [historicalValues[historicalValues.length - 1]],
                    predictedValues
                ),
                smooth: true,
                lineStyle: {
                    color: '#E6A23C',
                    width: 3,
                    type: 'dashed'
                },
                itemStyle: {
                    color: '#E6A23C'
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(230, 162, 60, 0.3)' },
                        { offset: 1, color: 'rgba(230, 162, 60, 0.01)' }
                    ])
                }
            }
        ]
    };

    // 添加增长阶段标注
    if (trendData.growth_stage) {
        option.annotation = {
            data: [{
                xAxis: dates.length - 1,
                yAxis: Math.max(...historicalValues),
                label: {
                    formatter: trendData.growth_stage
                }
            }]
        };
    }

    chart.setOption(option);
    return chart;
}

// ==================== 供应链关系图 ====================

/**
 * 渲染供应链关系图谱
 * @param {string} elementId - HTML 元素 ID
 * @param {Object} graphData - 图谱数据
 */
function renderSupplyChainGraph(elementId, graphData) {
    const chart = echarts.init(document.getElementById(elementId));

    // 构建节点
    const nodes = [
        {
            id: graphData.center.company_id || 'center',
            name: graphData.center.company_name,
            symbolSize: 50,
            category: 0,
            role: graphData.center.role,
            value: {
                industry: graphData.center.industry,
                region: graphData.center.region
            }
        }
    ];

    const categories = [
        { name: '目标公司' },
        { name: '供应商' },
        { name: '分销商' },
        { name: '客户' },
        { name: '物流' }
    ];

    // 添加上下游节点
    graphData.nodes.forEach((node, index) => {
        let category = 1; // 默认供应商
        if (node.role === 'distributor') category = 2;
        else if (node.role === 'customer') category = 3;
        else if (node.role === 'logistics') category = 4;

        nodes.push({
            id: node.company_id || `node_${index}`,
            name: node.company_name,
            symbolSize: 35,
            category: category,
            value: {
                industry: node.industry,
                region: node.region,
                products: node.products?.join(', ')
            }
        });
    });

    // 构建关系边
    const edges = graphData.relationships.map(rel => ({
        source: rel.target_company || rel.source_company,
        target: rel.source_company || rel.target_company,
        label: {
            show: true,
            formatter: rel.relationship_type
        },
        lineStyle: {
            curveness: 0.2,
            width: rel.strength ? rel.strength * 3 : 1
        }
    }));

    const option = {
        title: {
            text: '供应链关系图谱',
            left: 'center'
        },
        tooltip: {
            formatter: function(params) {
                if (params.dataType === 'node') {
                    let content = `<strong>${params.name}</strong><br/>`;
                    content += `角色：${params.data.role || '未知'}<br/>`;
                    content += `行业：${params.data.value?.industry || '未知'}<br/>`;
                    content += `地区：${params.data.value?.region || '未知'}`;
                    if (params.data.value?.products) {
                        content += `<br/>产品：${params.data.value.products}`;
                    }
                    return content;
                }
                return params.name;
            }
        },
        legend: [{
            data: categories.map(c => c.name),
            top: 30
        }],
        series: [{
            type: 'graph',
            layout: 'force',
            data: nodes,
            links: edges,
            categories: categories,
            roam: true,
            label: {
                show: true,
                position: 'right'
            },
            force: {
                repulsion: 300,
                edgeLength: [100, 200],
                gravity: 0.1
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
            }
        }]
    };

    chart.setOption(option);
    return chart;
}

// ==================== 政策分布图 ====================

/**
 * 渲染政策分布图（按类型和级别）
 * @param {string} elementId - HTML 元素 ID
 * @param {Array} policies - 政策列表
 */
function renderPolicyDistribution(elementId, policies) {
    const chart = echarts.init(document.getElementById(elementId));

    // 统计数据
    const typeCount = {};
    const levelCount = {};
    const regionCount = {};

    policies.forEach(p => {
        // 按类型统计
        const type = p.policy_type || 'unknown';
        typeCount[type] = (typeCount[type] || 0) + 1;

        // 按级别统计
        const level = p.level || 'unknown';
        levelCount[level] = (levelCount[level] || 0) + 1;

        // 按地区统计
        const region = p.region || 'unknown';
        regionCount[region] = (regionCount[region] || 0) + 1;
    });

    const option = {
        title: {
            text: '政策分布分析',
            left: 'center'
        },
        tooltip: {
            trigger: 'item'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        series: [
            {
                name: '政策类型',
                type: 'pie',
                radius: ['40%', '60%'],
                center: ['25%', '50%'],
                data: Object.entries(typeCount).map(([name, value]) => ({
                    name: name,
                    value: value
                })),
                label: {
                    formatter: '{b}: {c} ({d}%)'
                }
            },
            {
                name: '政策级别',
                type: 'bar',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: Object.entries(levelCount).map(([name, value]) => ({
                    name: name,
                    value: value
                })),
                itemStyle: {
                    color: '#409EFF'
                }
            }
        ],
        xAxis: [{
            type: 'category',
            data: Object.keys(levelCount),
            axisLabel: {
                interval: 0,
                rotate: 30
            }
        }],
        yAxis: [{
            type: 'value'
        }]
    };

    chart.setOption(option);
    return chart;
}

// ==================== 推荐效果对比图 ====================

/**
 * 渲染推荐策略效果对比图
 * @param {string} elementId - HTML 元素 ID
 * @param {Object} statsData - 统计数据
 */
function renderRecommendationStats(elementId, statsData) {
    const chart = echarts.init(document.getElementById(elementId));

    const byType = statsData.by_type || {};

    const option = {
        title: {
            text: '推荐策略分布',
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        legend: {
            top: 30
        },
        xAxis: {
            type: 'category',
            data: Object.keys(byType).map(k => {
                const names = {
                    'content_based': '内容推荐',
                    'collaborative': '协同过滤',
                    'trend_driven': '趋势驱动',
                    'knowledge_graph': '知识图谱'
                };
                return names[k] || k;
            }),
            axisLabel: {
                interval: 0,
                rotate: 0
            }
        },
        yAxis: {
            type: 'value',
            name: '推荐数量'
        },
        series: [{
            data: Object.values(byType),
            type: 'bar',
            barWidth: '50%',
            itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: '#83bff6' },
                    { offset: 0.5, color: '#188df0' },
                    { offset: 1, color: '#188df0' }
                ])
            },
            label: {
                show: true,
                position: 'top'
            }
        }]
    };

    chart.setOption(option);
    return chart;
}

// ==================== 综合仪表板 ====================

/**
 * 渲染 P6 综合仪表板
 * @param {string} elementId - HTML 元素 ID
 * @param {Object} dashboardData - 仪表板数据
 */
function renderP6Dashboard(elementId, dashboardData) {
    const chart = echarts.init(document.getElementById(elementId));

    const option = {
        title: {
            text: 'P6 商机挖掘仪表板',
            left: 'center'
        },
        grid: {
            left: '5%',
            right: '5%',
            top: '15%',
            bottom: '10%'
        },
        xAxis: {
            type: 'category',
            data: dashboardData.categories || [],
            axisLabel: {
                interval: 0,
                rotate: 30
            }
        },
        yAxis: {
            type: 'value'
        },
        series: [
            {
                name: '平均置信度',
                type: 'bar',
                data: dashboardData.confidence_scores || [],
                itemStyle: {
                    color: '#67C23A'
                }
            },
            {
                name: '平均价值',
                type: 'line',
                yAxisIndex: 0,
                data: dashboardData.value_scores || [],
                itemStyle: {
                    color: '#E6A23C'
                }
            }
        ],
        tooltip: {
            trigger: 'axis'
        }
    };

    chart.setOption(option);
    return chart;
}

// ==================== 导出模块 ====================

export {
    renderOpportunityScoreRadar,
    renderTrendPredictionChart,
    renderSupplyChainGraph,
    renderPolicyDistribution,
    renderRecommendationStats,
    renderP6Dashboard
};
