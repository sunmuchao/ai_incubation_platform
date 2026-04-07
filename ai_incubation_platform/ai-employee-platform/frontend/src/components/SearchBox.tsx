/**
 * 搜索框组件
 */
import React, { useState, useCallback } from 'react';
import { Input, Select, Space, Button } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';

const { Option } = Select;

interface SearchBoxProps {
  onSearch: (keyword: string, filters?: Record<string, unknown>) => void;
  placeholder?: string;
  showFilters?: boolean;
  filters?: Array<{
    key: string;
    label: string;
    options: { value: string | number; label: string }[];
  }>;
  defaultValue?: string;
  style?: React.CSSProperties;
}

export const SearchBox: React.FC<SearchBoxProps> = ({
  onSearch,
  placeholder = '请输入搜索内容',
  showFilters = false,
  filters = [],
  defaultValue = '',
  style,
}) => {
  const [keyword, setKeyword] = useState(defaultValue);
  const [filterValues, setFilterValues] = useState<Record<string, unknown>>({});

  const handleSearch = useCallback(() => {
    onSearch(keyword, filterValues);
  }, [keyword, filterValues, onSearch]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleReset = () => {
    setKeyword('');
    setFilterValues({});
    onSearch('', {});
  };

  const handleFilterChange = (key: string, value: unknown) => {
    setFilterValues((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <Space.Compact style={{ width: '100%', ...style }}>
      <Input
        placeholder={placeholder}
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        onKeyPress={handleKeyPress}
        prefix={<SearchOutlined />}
        allowClear
        style={{ minWidth: 200 }}
      />

      {showFilters &&
        filters.map((filter) => (
          <Select
            key={filter.key}
            placeholder={filter.label}
            value={filterValues[filter.key]}
            onChange={(value) => handleFilterChange(filter.key, value)}
            allowClear
            style={{ width: 120 }}
          >
            {filter.options.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        ))}

      <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
        搜索
      </Button>
      <Button icon={<ReloadOutlined />} onClick={handleReset}>
        重置
      </Button>
    </Space.Compact>
  );
};

export default SearchBox;
