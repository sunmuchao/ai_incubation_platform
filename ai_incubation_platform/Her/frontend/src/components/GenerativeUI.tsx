/**
 * AI Native Generative UI 主渲染器
 *
 * AI Native 设计原则:
 * 1. 界面由 AI 动态生成，而非固定布局
 * 2. 根据任务类型/用户意图动态重组
 * 3. 可视化组件由 AI 选择并生成
 * 4. 支持所有 Agent Skills 的 UI 渲染
 */

import React from 'react'
import { Empty } from 'antd'
import './GenerativeUI.less'

// 从模块化组件导入所有组件
import {
  // 类型
  GenerativeUIConfig,
  GenerativeUIProps,
  GenerativeAction,

  // 匹配组件
  MatchSpotlight,
  MatchCardList,
  MatchCarousel,

  // 礼物组件
  GiftGrid,
  GiftCarousel,

  // 约会组件
  DateSpotList,
  DatePlanCarousel,

  // 安全组件
  SafetyAlert,
  SafetyStatus,
  SafetyEmergency,
  EmergencyPanel,

  // 共享组件
  EmptyState,
  ConsumptionProfile,
  HealthReport,

  // 情感分析组件
  EmotionRadar,
  EmotionEmpty,
  LoveLanguageCard,
  LoveLanguageTranslationCard,
  PredictionEmpty,
  RelationshipWeatherReport,
  SilenceStatus,

  // 关系进展组件
  MilestoneTimeline,
  RelationshipTimeline,
  HealthScoreCard,
  RelationshipChart,
  RelationshipDashboard,

  // 聊天助手组件
  MessageSent,
  ConversationList,
  ChatHistory,
  SuggestionCards,
  UnreadBadge,

  // 话题建议组件
  TopicKit,
  TopicSuggestions,
  RelationshipCurator,

  // 教练组件
  VideoDateCoachDashboard,
  DateSimulationFeedback,
  PerformanceCoachDashboard,
  CoachEmpty,

  // 活动准备组件
  PrepChecklist,
  OutfitRecommendations,
  DateAssistantCard,
  DateReview,
  VenueRecommendations,
  MilestoneCard,

  // 仪表板组件
  RiskControlDashboard,
  RiskAssessmentDashboard,
  ShareGrowthDashboard,
  ActivityDirectorDashboard,
  ConversationMatchmakerDashboard,

  // 趋势组件
  RelationshipTrendChart,
  RelationshipWeather,
  ConflictMeter,
  MediationEmpty
} from './generative-ui'

// 导出类型（保持向后兼容）
export { GenerativeUIConfig, GenerativeUIProps, GenerativeAction }

// 导出所有组件（保持向后兼容）
export {
  MatchSpotlight,
  MatchCardList,
  MatchCarousel,
  GiftGrid,
  GiftCarousel,
  DateSpotList,
  DatePlanCarousel,
  SafetyAlert,
  SafetyStatus,
  SafetyEmergency,
  EmergencyPanel,
  EmptyState,
  ConsumptionProfile,
  HealthReport,
  EmotionRadar,
  EmotionEmpty,
  LoveLanguageCard,
  LoveLanguageTranslationCard,
  PredictionEmpty,
  RelationshipWeatherReport,
  SilenceStatus,
  MilestoneTimeline,
  RelationshipTimeline,
  HealthScoreCard,
  RelationshipChart,
  RelationshipDashboard,
  MessageSent,
  ConversationList,
  ChatHistory,
  SuggestionCards,
  UnreadBadge,
  TopicKit,
  TopicSuggestions,
  RelationshipCurator,
  VideoDateCoachDashboard,
  DateSimulationFeedback,
  PerformanceCoachDashboard,
  CoachEmpty,
  PrepChecklist,
  OutfitRecommendations,
  DateAssistantCard,
  DateReview,
  VenueRecommendations,
  MilestoneCard,
  RiskControlDashboard,
  RiskAssessmentDashboard,
  ShareGrowthDashboard,
  ActivityDirectorDashboard,
  ConversationMatchmakerDashboard,
  RelationshipTrendChart,
  RelationshipWeather,
  ConflictMeter,
  MediationEmpty
}

/**
 * Generative UI 渲染器
 *
 * 根据 AI 生成的 UI 配置动态渲染组件
 */
export const GenerativeUIRenderer: React.FC<GenerativeUIProps> = ({ uiConfig, onAction }) => {
  const { component_type, props } = uiConfig

  const renderComponent = () => {
    switch (component_type) {
      // 匹配相关
      case 'match_spotlight':
        return <MatchSpotlight match={props?.match} onAction={onAction} />
      case 'match_card_list':
        return <MatchCardList matches={props?.matches || []} onAction={onAction} />
      case 'match_carousel':
        return <MatchCarousel matches={props?.matches || []} onAction={onAction} />

      // 礼物相关
      case 'gift_grid':
        return <GiftGrid gifts={props?.gifts || []} columns={props?.columns} onAction={onAction} />
      case 'gift_carousel':
        return <GiftCarousel gifts={props?.gifts || []} onAction={onAction} />

      // 消费画像
      case 'consumption_profile':
        return <ConsumptionProfile profile={props?.profile || {}} />

      // 约会相关
      case 'date_spot_map':
      case 'date_spot_list':
        return <DateSpotList spots={props?.spots || []} />
      case 'date_plan_carousel':
        return <DatePlanCarousel plans={props?.plans || props?.spots || []} onAction={onAction} />

      // 健康报告
      case 'health_report':
        return <HealthReport report={props?.report || {}} />

      // 情感分析
      case 'emotion_radar':
        return (
          <EmotionRadar
            emotions={props?.emotions || []}
            dominant_emotion={props?.dominant_emotion}
            intensity={props?.intensity}
          />
        )
      case 'emotion_empty':
        return <EmotionEmpty message={props?.message} />

      // 爱之语
      case 'love_language_card':
        return <LoveLanguageCard profile={props?.profile || {}} />
      case 'love_language_translation_card':
        return (
          <LoveLanguageTranslationCard
            original_expression={props?.original_expression}
            translated_expression={props?.translated_expression}
            love_language_type={props?.love_language_type}
            explanation={props?.explanation}
          />
        )

      // 关系预测
      case 'prediction_empty':
        return <PredictionEmpty message={props?.message} />
      case 'relationship_weather_report':
      case 'relationship_weather':
        return (
          <RelationshipWeatherReport
            weather={props?.weather}
            forecast={props?.forecast || {}}
          />
        )

      // 沉默检测
      case 'silence_status':
        return <SilenceStatus duration={props?.duration} level={props?.level} />

      // 话题建议
      case 'topic_kit':
        return <TopicKit topics={props?.topics || []} onAction={onAction} />
      case 'topic_suggestions':
        return <TopicSuggestions suggestions={props?.suggestions || []} onAction={onAction} />

      // 关系策展
      case 'relationship_curator':
        return <RelationshipCurator relationship={props?.relationship || {}} />
      case 'milestone_timeline':
        return <MilestoneTimeline milestones={props?.milestones || []} />

      // 约会助手
      case 'date_assistant_card':
        return <DateAssistantCard suggestion={props?.suggestion || {}} onAction={onAction} />
      case 'date_review':
        return <DateReview review={props?.review || {}} />

      // 视频约会教练
      case 'video_date_coach_dashboard':
        return (
          <VideoDateCoachDashboard
            coaching={props?.coaching}
            outfit={props?.outfit}
            icebreakers={props?.icebreakers}
            onAction={onAction}
          />
        )
      case 'date_simulation_feedback':
        return <DateSimulationFeedback feedback={props?.feedback || {}} />

      // 绩效教练
      case 'performance_coach_dashboard':
        return (
          <PerformanceCoachDashboard
            metrics={props?.metrics}
            milestones={props?.milestones}
            suggestions={props?.suggestions}
          />
        )
      case 'coach_empty':
        return <CoachEmpty message={props?.message} />

      // 活动准备
      case 'prep_checklist':
        return <PrepChecklist items={props?.items || []} onAction={onAction} />
      case 'outfit_recommendations':
        return <OutfitRecommendations outfits={props?.outfits || []} />

      // 安全组件
      case 'safety_alert':
        return <SafetyAlert level={props?.level} message={props?.message} />
      case 'safety_status':
        return <SafetyStatus status={props?.status} details={props?.details} />
      case 'safety_emergency':
        return <SafetyEmergency message={props?.message} onAction={onAction} />
      case 'emergency_panel':
        return (
          <EmergencyPanel
            emergency_type={props?.emergency_type}
            status={props?.status}
            contacts_notified={props?.contacts_notified}
            location_shared={props?.location_shared}
            onAction={onAction}
          />
        )

      // 风控组件
      case 'risk_control_dashboard':
        return <RiskControlDashboard metrics={props?.metrics || {}} risks={props?.risks || []} />
      case 'risk_assessment_dashboard':
        return <RiskAssessmentDashboard assessment={props?.assessment || {}} />

      // 分享增长
      case 'share_growth_dashboard':
        return (
          <ShareGrowthDashboard
            metrics={props?.metrics || {}}
            invites={props?.invites}
          />
        )

      // 活动导演
      case 'activity_director_dashboard':
        return (
          <ActivityDirectorDashboard
            activities={props?.activities}
            recommendations={props?.recommendations}
            onAction={onAction}
          />
        )

      // 场地推荐
      case 'venue_recommendations':
        return <VenueRecommendations venues={props?.venues || []} />

      // 关系趋势
      case 'relationship_trend_chart':
        return <RelationshipTrendChart data={props?.data || []} />
      case 'relationship_weather_simple':
        return <RelationshipWeather weather={props?.weather} score={props?.score} />

      // 冲突计量器
      case 'conflict_meter':
        return <ConflictMeter level={props?.level || 0} />

      // 调解
      case 'mediation_empty':
        return <MediationEmpty message={props?.message} />

      // 对话匹配
      case 'conversation_matchmaker_dashboard':
        return (
          <ConversationMatchmakerDashboard
            matches={props?.matches}
            intents={props?.intents}
            onAction={onAction}
          />
        )

      // 关系进展追踪
      case 'milestone_card':
        return <MilestoneCard type={props?.type} status={props?.status} onAction={onAction} />
      case 'relationship_timeline':
        return (
          <RelationshipTimeline
            current_stage={props?.current_stage}
            milestones={props?.milestones}
            show_progress_indicator={props?.show_progress_indicator}
            onAction={onAction}
          />
        )
      case 'health_score_card':
        return (
          <HealthScoreCard
            score={props?.score}
            max_score={props?.max_score}
            level={props?.level}
            color={props?.color}
            dimensions={props?.dimensions}
            suggestions={props?.suggestions}
            onAction={onAction}
          />
        )
      case 'relationship_chart':
        return (
          <RelationshipChart
            chart_type={props?.chart_type}
            labels={props?.labels}
            activity_data={props?.activity_data}
            stage_changes={props?.stage_changes}
            onAction={onAction}
          />
        )
      case 'relationship_dashboard':
        return (
          <RelationshipDashboard
            summary={props?.summary}
            timeline={props?.timeline}
            health_score={props?.health_score}
            onAction={onAction}
          />
        )

      // 聊天助手
      case 'message_sent':
        return <MessageSent message_id={props?.message_id} status={props?.status} onAction={onAction} />
      case 'conversation_list':
        return (
          <ConversationList
            conversations={props?.conversations}
            show_unread={props?.show_unread}
            onAction={onAction}
          />
        )
      case 'chat_history':
        return (
          <ChatHistory
            messages={props?.messages}
            show_sender={props?.show_sender}
            onAction={onAction}
          />
        )
      case 'suggestion_cards':
        return (
          <SuggestionCards
            suggestions={props?.suggestions}
            show_reason={props?.show_reason}
            onAction={onAction}
          />
        )
      case 'unread_badge':
        return <UnreadBadge count={props?.count} onAction={onAction} />

      // 空状态
      case 'empty_state':
        return <EmptyState message={props?.message || '暂无内容'} />

      default:
        return <EmptyState message={`未知组件类型：${component_type}`} />
    }
  }

  return <div className="generative-ui-container">{renderComponent()}</div>
}

export default GenerativeUIRenderer