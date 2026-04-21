/**
 * 将模型输出的「一整段」中文回复拆成更易读的段落（换行）。
 * 不改变语义，只做常见版式修复；与 white-space: pre-wrap 配合使用。
 */
export function formatChatReplyReadability(text: string): string {
  if (!text) return text
  let t = text.trim()
  if (!t) return t

  // 冒号后总起下一句（「：    这三位」类）
  t = t.replace(/([：:])\s+(这|以下|这三|下面|接下来|先看看|如果你|你也可以)/g, '$1\n\n$2')

  // 句末标点后新话题起句（避免把「1。2」当句号：要求标点后为常见中文起句）
  t = t.replace(/([。！？])\s*(太|让|我先|好的|对了|另外|你对|要不|所以|接下来|下面|如果你|其实|对了，)/g, '$1\n\n$2')

  // 黏在同一行里的 Markdown 列表（- **姓名**）
  t = t.replace(/([^\n])\s*(-\s+\*\*)/g, '$1\n\n$2')

  // 合并过多空行
  t = t.replace(/\n{3,}/g, '\n\n')

  return t.trim()
}
