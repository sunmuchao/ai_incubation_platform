// Face Verification Types - 人脸认证类型定义

export type FaceVerificationStatus =
  | 'not_started'
  | 'in_progress'
  | 'submitted'
  | 'verified'
  | 'failed'
  | 'expired'

export type FaceVerificationMethod =
  | 'id_card_compare'
  | 'self_photo'
  | 'video_liveness'
  | 'ai_gesture'

export type VerificationBadgeType =
  | 'blue_star'
  | 'gold_star'
  | 'platinum_star'
  | 'diamond_star'

export interface FaceVerificationRequest {
  method: FaceVerificationMethod
  photo_base64: string
  video_base64?: string
  gesture_sequence?: string[]
}

export interface FaceVerificationResponse {
  success: boolean
  message: string
  verification_id?: string
  status: FaceVerificationStatus
  similarity_score?: number
  liveness_score?: number
  badge_type?: VerificationBadgeType
}

export interface UserVerificationStatus {
  user_id: string
  face_verified: boolean
  face_verification_id?: string
  face_verification_date?: string
  id_verified: boolean
  education_verified: boolean
  occupation_verified: boolean
  current_badge?: VerificationBadgeType
  badge_display_name?: string
  badge_display_icon?: string
  badge_display_color?: string
  trust_score: number
}

export interface VerificationBadge {
  id: string
  user_id: string
  badge_type: VerificationBadgeType
  status: 'active' | 'expired'
  verification_id: string
  display_name: string
  display_icon: string
  display_color: string
  issued_at: string
  expires_at?: string
}

export interface FaceVerificationRecord {
  id: string
  user_id: string
  method: FaceVerificationMethod
  status: FaceVerificationStatus
  similarity_score?: number
  liveness_score?: number
  is_passed: boolean
  photo_hash?: string
  failure_reason?: string
  retry_count: number
  submitted_at?: string
  completed_at?: string
}

// 徽章配置
export const VERIFICATION_BADGE_CONFIG: Record<VerificationBadgeType, {
  name: string
  icon: string
  color: string
  description: string
  requirements: string[]
}> = {
  blue_star: {
    name: '蓝星认证',
    icon: '⭐',
    color: '#1890ff',
    description: '已完成人脸认证',
    requirements: ['face_verification'],
  },
  gold_star: {
    name: '金星认证',
    icon: '🌟',
    color: '#faad14',
    description: '身份证+人脸双重认证',
    requirements: ['id_verification', 'face_verification'],
  },
  platinum_star: {
    name: '铂金星认证',
    icon: '✨',
    color: '#95de64',
    description: '实名+人脸+学历认证',
    requirements: ['id_verification', 'face_verification', 'education_verification'],
  },
  diamond_star: {
    name: '钻石星认证',
    icon: '💎',
    color: '#D4A59A',
    description: '全方位身份认证',
    requirements: ['id_verification', 'face_verification', 'education_verification', 'occupation_verification'],
  },
}