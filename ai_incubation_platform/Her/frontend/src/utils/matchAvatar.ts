/**
 * 匹配卡片头像：优先用户上传 URL；无有效 URL 时（测试环境）使用网上按性别区分的肖像图，
 * 加载失败时回退到仓库内本地 SVG。
 */

/** 测试用肖像：randomuser.me 男女头像库（0–99 稳定编号） */
const DEMO_PORTRAIT_SLOTS = 100

/** 仅使用仓库中已存在的文件名（onError 兜底） */
const FALLBACK_AVATAR_KEYS = ['female_001', 'male_001', 'female_002', 'male_002'] as const
const MALE_FALLBACK_KEYS = ['male_001', 'male_002'] as const
const FEMALE_FALLBACK_KEYS = ['female_001', 'female_002'] as const

const getAvatarIndex = (name: string): number => {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash) + name.charCodeAt(i)
    hash = hash & hash
  }
  return Math.abs(hash) % 50 + 1
}

/** 0–99，与 randomuser portraits 编号对齐 */
function getPortraitSlot(name: string): number {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash) + name.charCodeAt(i)
    hash = hash & hash
  }
  return Math.abs(hash) % DEMO_PORTRAIT_SLOTS
}

/** 将后端/Agent 返回的性别归一为 male / female，便于选默认头像 */
export function normalizeGender(gender?: string | null): 'male' | 'female' | undefined {
  const raw = (gender ?? '').toString().trim()
  if (!raw) return undefined
  const g = raw.toLowerCase()
  if (['m', 'male', 'man', '1', 'boy', 'guy'].includes(g)) return 'male'
  if (['f', 'female', 'woman', '2', 'girl'].includes(g)) return 'female'
  if (raw === '男' || raw.includes('男')) return 'male'
  if (raw === '女' || raw.includes('女')) return 'female'
  return undefined
}

/** Agent/脏数据常见占位：非空字符串但仍不可用作图片地址 */
export function isUsableAvatarUrl(raw: string | null | undefined): boolean {
  const s = (raw ?? '').toString().trim()
  if (!s) return false
  const lower = s.toLowerCase()
  if (['null', 'undefined', 'none', 'n/a', 'na', '-', '[]'].includes(lower)) return false
  if (lower.includes('via.placeholder.com')) return false
  if (lower.includes('placehold.co')) return false
  return true
}

/** 本地 SVG，仅作网络头像加载失败时的兜底 */
function pickGenderedLocalSvg(name: string, gender?: string | null): string {
  const g = normalizeGender(gender)
  const index = getAvatarIndex(name || 'user')
  if (g === 'male') {
    const key = MALE_FALLBACK_KEYS[index % MALE_FALLBACK_KEYS.length]
    return `/static/avatars/${key}.svg`
  }
  if (g === 'female') {
    const key = FEMALE_FALLBACK_KEYS[index % FEMALE_FALLBACK_KEYS.length]
    return `/static/avatars/${key}.svg`
  }
  const key = FALLBACK_AVATAR_KEYS[index % FALLBACK_AVATAR_KEYS.length]
  return `/static/avatars/${key}.svg`
}

/** 测试用：网上男女肖像（同名字稳定同一 slot） */
function pickGenderedDemoPortrait(name: string, gender?: string | null): string {
  const slot = getPortraitSlot(name || 'user')
  const g = normalizeGender(gender)
  if (g === 'male') {
    return `https://randomuser.me/api/portraits/men/${slot}.jpg`
  }
  if (g === 'female') {
    return `https://randomuser.me/api/portraits/women/${slot}.jpg`
  }
  return slot % 2 === 0
    ? `https://randomuser.me/api/portraits/men/${slot}.jpg`
    : `https://randomuser.me/api/portraits/women/${slot}.jpg`
}

/** 归一化后端/Agent 返回的头像地址，便于浏览器加载 */
export function normalizeAvatarUrl(raw: string): string {
  const s = raw.trim()
  if (!s) return ''
  if (s.startsWith('//')) return `https:${s}`
  if (
    s.startsWith('http://') ||
    s.startsWith('https://') ||
    s.startsWith('data:') ||
    s.startsWith('blob:')
  ) {
    return s
  }
  if (s.startsWith('/')) return s
  return `/${s.replace(/^\/+/, '')}`
}

export function getMatchAvatarSrc(
  name: string,
  gender?: string,
  avatar?: string | null,
  avatarUrl?: string | null
): string {
  const directRaw = (avatar || avatarUrl || '').trim()
  if (directRaw && isUsableAvatarUrl(directRaw)) {
    return normalizeAvatarUrl(directRaw)
  }
  return pickGenderedDemoPortrait(name || 'user', gender)
}

/**
 * 网络图 onError 时回退到本地 SVG，避免卡片只剩图标
 */
export function getFallbackAvatarUrlForCandidate(match: Record<string, any> | null | undefined): string {
  if (!match || typeof match !== 'object') {
    return pickGenderedLocalSvg('user', undefined)
  }
  const u = match.user && typeof match.user === 'object' ? match.user : {}
  const name = String(match.name || u.name || 'user')
  const gender = (match.gender || u.gender) as string | undefined
  return pickGenderedLocalSvg(name, gender)
}

/**
 * 从 MatchCardList 单行数据解析头像（兼容扁平字段与嵌套 user）
 */
export function getAvatarUrlForCandidate(match: Record<string, any> | null | undefined): string {
  if (!match || typeof match !== 'object') {
    return getMatchAvatarSrc('user', undefined, undefined, undefined)
  }
  const u = match.user && typeof match.user === 'object' ? match.user : {}
  const name = String(match.name || u.name || 'user')
  const gender = (match.gender || u.gender) as string | undefined
  const direct = (
    match.avatar_url ||
    match.avatar ||
    u.avatar_url ||
    u.avatar ||
    ''
  ).toString()
  return getMatchAvatarSrc(name, gender, undefined, direct || undefined)
}
