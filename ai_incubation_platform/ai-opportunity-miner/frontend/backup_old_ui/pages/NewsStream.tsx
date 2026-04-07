import { Card, List, Tag, Input, Button, Space } from 'antd'
import { SearchOutlined, ReloadOutlined, StarOutlined, ShareAltOutlined } from '@ant-design/icons'
import { useState } from 'react'

function NewsStream() {
  const [searchText, setSearchText] = useState('')

  const newsData = [
    { 
      key: '1', 
      title: '人工智能行业迎来新突破，多项技术取得重大进展',
      source: '科技日报',
      time: '10 分钟前',
      category: '科技',
      hot: true
    },
    { 
      key: '2', 
      title: '某知名车企发布新款新能源汽车，续航里程突破 1000 公里',
      source: '汽车之家',
      time: '30 分钟前',
      category: '汽车',
      hot: true
    },
    { 
      key: '3', 
      title: '生物医药领域新专利获批，将大幅降低治疗成本',
      source: '医药经济报',
      time: '1 小时前',
      category: '医药',
      hot: false
    },
    { 
      key: '4', 
      title: '智能制造论坛在京举行，多家企业签约合作',
      source: '财经新闻',
      time: '2 小时前',
      category: '财经',
      hot: false
    },
    { 
      key: '5', 
      title: '区块链技术在供应链金融中的应用案例分析',
      source: '链闻',
      time: '3 小时前',
      category: '区块链',
      hot: false
    },
  ]

  const categoryColors: Record<string, string> = {
    '科技': 'blue',
    '汽车': 'green',
    '医药': 'purple',
    '财经': 'orange',
    '区块链': 'cyan',
  }

  return (
    <div>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索新闻"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Button icon={<ReloadOutlined />}>刷新</Button>
        </Space>
        <List
          itemLayout="vertical"
          dataSource={newsData}
          renderItem={(item) => (
            <List.Item
              key={item.key}
              actions={[
                <span key="star"><StarOutlined /> 收藏</span>,
                <span key="share"><ShareAltOutlined /> 分享</span>,
              ]}
              extra={
                <div style={{ width: 200, height: 120, background: 'linear-gradient(135deg, #722ed1 0%, #1890ff 100%)', borderRadius: 8 }} />
              }
            >
              <List.Item.Meta
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <a style={{ color: 'rgba(255,255,255,0.85)' }}>{item.title}</a>
                    {item.hot && <Tag color="red">热门</Tag>}
                  </div>
                }
                description={
                  <Space>
                    <span>{item.source}</span>
                    <span>{item.time}</span>
                    <Tag color={categoryColors[item.category]}>{item.category}</Tag>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  )
}

export default NewsStream
