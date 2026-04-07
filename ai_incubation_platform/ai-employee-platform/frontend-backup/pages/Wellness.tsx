/**
 * 员工福祉页面
 */
import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Button,
  Space,
  Progress,
  Statistic,
  Timeline,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  message,
  Tag,
  Empty,
  Slider,
} from 'antd';
import {
  HeartOutlined,
  CalendarOutlined,
  FileTextOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useWellness } from '@/hooks/useWellness';
import { useAuth } from '@/hooks/useAuth';
import type { LeaveRequest, CounselingSession, WellnessAssessment } from '@/services/wellnessApi';
import dayjs from 'dayjs';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const Wellness: React.FC = () => {
  const { user } = useAuth();
  const {
    wellnessDashboardQuery,
    stressTrendQuery,
    employeeAssessmentsQuery,
    createAssessmentMutation,
    logStressLevelMutation,
    employeeSessionsQuery,
    bookCounselingSessionMutation,
    employeeLeavesQuery,
    requestLeaveMutation,
    turnoverRiskQuery,
  } = useWellness();

  const [stressModalOpen, setStressModalOpen] = useState(false);
  const [leaveModalOpen, setLeaveModalOpen] = useState(false);
  const [counselingModalOpen, setCounselingModalOpen] = useState(false);
  const [assessmentModalOpen, setAssessmentModalOpen] = useState(false);
  const [stressForm] = Form.useForm();
  const [leaveForm] = Form.useForm();
  const [counselingForm] = Form.useForm();
  const [assessmentForm] = Form.useForm();

  const employeeId = user?.id || '';

  // 获取数据
  wellnessDashboardQuery(employeeId);
  const { data: stressTrend } = stressTrendQuery(employeeId);
  const { data: assessments, isLoading: loadingAssessments } = employeeAssessmentsQuery(employeeId);
  const { data: sessions, isLoading: loadingSessions } = employeeSessionsQuery(employeeId);
  const { data: leaves, isLoading: loadingLeaves } = employeeLeavesQuery(employeeId);
  const { data: turnoverRisk } = turnoverRiskQuery(employeeId);

  // 记录压力水平
  const handleLogStress = (values: { level: number; notes?: string }) => {
    logStressLevelMutation.mutate(
      { employeeId, level: values.level, notes: values.notes },
      {
        onSuccess: () => {
          message.success('压力水平已记录');
          setStressModalOpen(false);
          stressForm.resetFields();
        },
        onError: () => {
          message.error('记录压力水平失败');
        },
      }
    );
  };

  // 申请请假
  const handleRequestLeave = (values: { leave_type: string; start_date: string; end_date: string; reason?: string }) => {
    requestLeaveMutation.mutate(
      {
        employee_id: employeeId,
        leave_type: values.leave_type,
        start_date: values.start_date,
        end_date: values.end_date,
        reason: values.reason,
      },
      {
        onSuccess: () => {
          message.success('请假申请已提交');
          setLeaveModalOpen(false);
          leaveForm.resetFields();
        },
        onError: () => {
          message.error('提交请假申请失败');
        },
      }
    );
  };

  // 预约心理咨询
  const handleBookCounseling = (values: { counselor_id: string; session_date: string; duration_minutes?: number }) => {
    bookCounselingSessionMutation.mutate(
      {
        employee_id: employeeId,
        counselor_id: values.counselor_id,
        session_date: values.session_date,
        duration_minutes: values.duration_minutes || 60,
      },
      {
        onSuccess: () => {
          message.success('咨询预约已提交');
          setCounselingModalOpen(false);
          counselingForm.resetFields();
        },
        onError: () => {
          message.error('预约咨询失败');
        },
      }
    );
  };

  // 创建评估
  const handleCreateAssessment = (values: { assessment_type: string; responses: Record<string, unknown> }) => {
    createAssessmentMutation.mutate(
      {
        employee_id: employeeId,
        assessment_type: values.assessment_type,
        responses: values.responses || {},
      },
      {
        onSuccess: () => {
          message.success('评估已创建');
          setAssessmentModalOpen(false);
          assessmentForm.resetFields();
        },
        onError: () => {
          message.error('创建评估失败');
        },
      }
    );
  };

  // 获取请假状态标签
  const getLeaveStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'orange', text: '待审批' },
      approved: { color: 'green', text: '已批准' },
      rejected: { color: 'red', text: '已拒绝' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 获取咨询状态标签
  const getSessionStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
      scheduled: { color: 'blue', text: '已安排', icon: <ClockCircleOutlined /> },
      completed: { color: 'green', text: '已完成', icon: <CheckCircleOutlined /> },
      cancelled: { color: 'red', text: '已取消', icon: <CloseCircleOutlined /> },
    };
    const config = statusMap[status] || { color: 'default', text: status, icon: null };
    return (
      <Tag icon={config.icon} color={config.color}>
        {config.text}
      </Tag>
    );
  };

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Title level={2}>员工福祉</Title>
          <Paragraph type="secondary">
            关注您的身心健康，提供全方位的员工关怀服务
          </Paragraph>
        </div>

        {/* 快捷操作 */}
        <Card>
          <Row gutter={16}>
            <Col span={6}>
              <Button
                block
                icon={<ThunderboltOutlined />}
                onClick={() => setStressModalOpen(true)}
              >
                记录压力
              </Button>
            </Col>
            <Col span={6}>
              <Button
                block
                icon={<CalendarOutlined />}
                onClick={() => setLeaveModalOpen(true)}
              >
                申请请假
              </Button>
            </Col>
            <Col span={6}>
              <Button
                block
                icon={<HeartOutlined />}
                onClick={() => setCounselingModalOpen(true)}
              >
                预约咨询
              </Button>
            </Col>
            <Col span={6}>
              <Button
                block
                icon={<FileTextOutlined />}
                onClick={() => setAssessmentModalOpen(true)}
              >
                心理评估
              </Button>
            </Col>
          </Row>
        </Card>

        {/* 健康概览 */}
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="当前压力水平"
                value={(stressTrend as any)?.current_level || 0}
                precision={1}
                valueStyle={{
                  color:
                    ((stressTrend as any)?.current_level || 0) > 7
                      ? '#cf1322'
                      : ((stressTrend as any)?.current_level || 0) > 4
                      ? '#faad14'
                      : '#3f8600',
                }}
                suffix="/ 10"
              />
              <Progress
                percent={(((stressTrend as any)?.current_level || 0) / 10) * 100}
                strokeColor={
                  ((stressTrend as any)?.current_level || 0) > 7
                    ? '#cf1322'
                    : ((stressTrend as any)?.current_level || 0) > 4
                    ? '#faad14'
                    : '#3f8600'
                }
                showInfo={false}
                style={{ marginTop: 8 }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="离职风险"
                value={(turnoverRisk as any)?.risk_level || '低'}
                valueStyle={{
                  color: (turnoverRisk as any)?.risk_level === '高' ? '#cf1322' : (turnoverRisk as any)?.risk_level === '中' ? '#faad14' : '#3f8600',
                }}
              />
              {(turnoverRisk as any)?.risk_factors?.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    风险因素：
                  </Text>
                  <div>
                    {(turnoverRisk as any).risk_factors.slice(0, 2).map((factor: string, i: number) => (
                      <Tag key={i} color="red" style={{ marginBottom: 4 }}>
                        {factor}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已完成咨询"
                value={sessions?.filter((s: any) => s.status === 'completed').length || 0}
                suffix="次"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="待审批请假"
                value={leaves?.filter((l: any) => l.status === 'pending').length || 0}
                suffix="个"
              />
            </Card>
          </Col>
        </Row>

        {/* 压力趋势图表 */}
        {(stressTrend as any)?.trend_data && (
          <Card title="压力水平趋势">
            <div style={{ height: 200, display: 'flex', alignItems: 'flex-end', gap: 8 }}>
              {((stressTrend as any).trend_data || []).map((item: any, index: number) => (
                <div
                  key={index}
                  style={{
                    flex: 1,
                    height: `${(item.level / 10) * 100}%`,
                    backgroundColor:
                      item.level > 7 ? '#cf1322' : item.level > 4 ? '#faad14' : '#3f8600',
                    borderRadius: 4,
                    opacity: 0.8,
                  }}
                  title={`${item.date}: ${item.level}`}
                />
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
              {((stressTrend as any).trend_data || []).slice(0, 7).map((item: any, index: number) => (
                <Text key={index} type="secondary" style={{ fontSize: 12 }}>
                  {dayjs(item.date).format('MM-DD')}
                </Text>
              ))}
            </div>
          </Card>
        )}

        <Row gutter={16}>
          {/* 请假记录 */}
          <Col span={12}>
            <Card
              title="请假记录"
              extra={
                <Button type="link" onClick={() => setLeaveModalOpen(true)}>
                  <PlusOutlined /> 新申请
                </Button>
              }
            >
              {loadingLeaves ? (
                <Space><></></Space>
              ) : !leaves?.length ? (
                <Empty description="暂无请假记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <Timeline
                  items={(leaves || []).map((leave: LeaveRequest) => ({
                    key: leave.id,
                    color: leave.status === 'approved' ? 'green' : leave.status === 'rejected' ? 'red' : 'blue',
                    children: (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <Text strong>{leave.leave_type}</Text>
                          {getLeaveStatusTag(leave.status)}
                        </Space>
                        <Text type="secondary">
                          {dayjs(leave.start_date).format('YYYY-MM-DD')} - {dayjs(leave.end_date).format('YYYY-MM-DD')}
                        </Text>
                        {leave.reason && <Text type="secondary">{leave.reason}</Text>}
                      </Space>
                    ),
                  }))}
                />
              )}
            </Card>
          </Col>

          {/* 咨询预约 */}
          <Col span={12}>
            <Card
              title="咨询预约"
              extra={
                <Button type="link" onClick={() => setCounselingModalOpen(true)}>
                  <PlusOutlined /> 新预约
                </Button>
              }
            >
              {loadingSessions ? (
                <Space><></></Space>
              ) : !sessions?.length ? (
                <Empty description="暂无咨询预约" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <Timeline
                  items={(sessions || []).map((session: CounselingSession) => ({
                    key: session.id,
                    color: session.status === 'completed' ? 'green' : session.status === 'cancelled' ? 'red' : 'blue',
                    children: (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <Text strong>心理咨询师</Text>
                          {getSessionStatusTag(session.status)}
                        </Space>
                        <Text type="secondary">
                          <CalendarOutlined /> {dayjs(session.session_date).format('YYYY-MM-DD HH:mm')}
                        </Text>
                        <Text type="secondary">时长：{session.duration_minutes}分钟</Text>
                      </Space>
                    ),
                  }))}
                />
              )}
            </Card>
          </Col>
        </Row>

        {/* 最近评估 */}
        <Card title="心理评估记录">
          {loadingAssessments ? (
            <Space><></></Space>
          ) : !assessments?.length ? (
            <Empty description="暂无评估记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Row gutter={16}>
              {(assessments || []).map((assessment: WellnessAssessment) => (
                <Col span={8} key={assessment.id}>
                  <Card size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text strong>{assessment.assessment_type}</Text>
                      <Progress
                        percent={assessment.score * 10}
                        status={assessment.score >= 7 ? 'success' : assessment.score >= 4 ? 'normal' : 'exception'}
                        format={() => `${assessment.score}/10`}
                      />
                      <Text type="secondary">
                        {dayjs(assessment.created_at).format('YYYY-MM-DD')}
                      </Text>
                      {assessment.recommendations?.length > 0 && (
                        <div>
                          <Text type="secondary">建议：</Text>
                          <ul>
                            {assessment.recommendations.slice(0, 2).map((rec, i) => (
                              <li key={i}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Card>
      </Space>

      {/* 记录压力弹窗 */}
      <Modal
        title="记录压力水平"
        open={stressModalOpen}
        onOk={() => stressForm.submit()}
        onCancel={() => setStressModalOpen(false)}
        confirmLoading={logStressLevelMutation.isPending}
      >
        <Form form={stressForm} layout="vertical" onFinish={handleLogStress}>
          <Form.Item
            name="level"
            label="压力水平 (1-10)"
            rules={[{ required: true, message: '请选择压力水平' }]}
          >
            <Slider min={1} max={10} marks={{ 1: '1', 5: '5', 10: '10' }} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <TextArea rows={3} placeholder="记录当前压力来源或感受..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 申请请假弹窗 */}
      <Modal
        title="申请请假"
        open={leaveModalOpen}
        onOk={() => leaveForm.submit()}
        onCancel={() => setLeaveModalOpen(false)}
        confirmLoading={requestLeaveMutation.isPending}
      >
        <Form form={leaveForm} layout="vertical" onFinish={handleRequestLeave}>
          <Form.Item
            name="leave_type"
            label="请假类型"
            rules={[{ required: true, message: '请选择请假类型' }]}
          >
            <Select>
              <Select.Option value="annual">年假</Select.Option>
              <Select.Option value="sick">病假</Select.Option>
              <Select.Option value="personal">事假</Select.Option>
              <Select.Option value="maternity">产假</Select.Option>
              <Select.Option value="paternity">陪产假</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name={['start_date', 'start_date']}
            label="开始日期"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name={['end_date', 'end_date']}
            label="结束日期"
            rules={[{ required: true, message: '请选择结束日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="reason" label="请假原因">
            <TextArea rows={3} placeholder="请填写请假原因..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 预约咨询弹窗 */}
      <Modal
        title="预约心理咨询"
        open={counselingModalOpen}
        onOk={() => counselingForm.submit()}
        onCancel={() => setCounselingModalOpen(false)}
        confirmLoading={bookCounselingSessionMutation.isPending}
      >
        <Form form={counselingForm} layout="vertical" onFinish={handleBookCounseling}>
          <Form.Item
            name="counselor_id"
            label="选择咨询师"
            rules={[{ required: true, message: '请选择咨询师' }]}
          >
            <Select>
              <Select.Option value="counselor_1">张老师 - 资深心理咨询师</Select.Option>
              <Select.Option value="counselor_2">李老师 - 职业规划师</Select.Option>
              <Select.Option value="counselor_3">王老师 - 压力管理专家</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="session_date"
            label="预约时间"
            rules={[{ required: true, message: '请选择预约时间' }]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="duration_minutes" label="咨询时长">
            <Select defaultValue={60}>
              <Select.Option value={30}>30 分钟</Select.Option>
              <Select.Option value={60}>60 分钟</Select.Option>
              <Select.Option value={90}>90 分钟</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 心理评估弹窗 */}
      <Modal
        title="心理评估"
        open={assessmentModalOpen}
        onOk={() => assessmentForm.submit()}
        onCancel={() => setAssessmentModalOpen(false)}
        confirmLoading={createAssessmentMutation.isPending}
      >
        <Form form={assessmentForm} layout="vertical" onFinish={handleCreateAssessment}>
          <Form.Item
            name="assessment_type"
            label="评估类型"
            rules={[{ required: true, message: '请选择评估类型' }]}
          >
            <Select>
              <Select.Option value="mental_health">心理健康</Select.Option>
              <Select.Option value="stress">压力水平</Select.Option>
              <Select.Option value="satisfaction">满意度</Select.Option>
              <Select.Option value="work_life_balance">工作生活平衡</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Wellness;
