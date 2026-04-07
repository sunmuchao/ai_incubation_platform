# -*- coding: utf-8 -*-
"""孵化器十个子项目的课程数据（由 generate_codebase_courses.py 渲染）。"""
from __future__ import annotations

from generate_codebase_courses import (
    CODE_BUY,
    CODE_COMM,
    CODE_CU,
    CODE_DAC,
    CODE_EMP,
    CODE_HIRE,
    CODE_MATCH,
    CODE_MINER,
    CODE_RT,
    CODE_TRAFFIC,
    quiz_block,
    translation_block,
)


def T(d: str, text: str) -> str:
    return f'<span class="term" data-definition="{__import__("html").escape(d, quote=True)}">{__import__("html").escape(text)}</span>'


def std_quiz(qid: str, questions: list[dict]) -> str:
    return quiz_block(qid, questions)


def flow_buttons(fn_prefix: str) -> str:
    return f"""<div class="flow-controls">
  <button type="button" class="btn" onclick="{fn_prefix}_next()">下一步</button>
  <button type="button" class="btn secondary" onclick="{fn_prefix}_reset()">重来</button>
</div>"""


def flow_script(dom_prefix: str, fn_prefix: str, steps: list[dict]) -> str:
    import json

    s = json.dumps(steps, ensure_ascii=False)
    dp = json.dumps(dom_prefix)
    fp = json.dumps(fn_prefix)
    return f"<script>initFlow({dp}, {s}, {fp});</script>"


def chat_script(chat_id: str, fn_prefix: str | None = None) -> str:
    import json

    cid = json.dumps(chat_id)
    fp = json.dumps(fn_prefix or chat_id.replace("-", "_"))
    return f"<script>playChat({cid}, {fp});</script>"


# ---------- 各项目 ----------


def dac() -> dict:
    slug = "data-agent-connector"
    return {
        "folder": slug,
        "slug": slug,
        "title": "Data-Agent Connector · 数据网关",
        "pill": "基础设施 · 统一数据出口",
        "accent": "#2A7B9B",
        "intro": f"把本仓库想成一座城市的「水务集团」：{T('API（应用程序接口）是程序之间用结构化请求对话的约定，例如 REST/JSON。', 'API')} 不是各自挖井，而是统一净化、计量、留痕后再供水。这里解决 {T('NL2SQL（Natural Language to SQL）指把自然语言问题转成可执行的数据库查询语句。', 'NL2SQL')} 的风险、{T('审计日志记录谁在何时做了什么操作，用于合规与排障。', '审计')} 与连接器重复建设问题。",
        "modules": [
            {
                "id": f"{slug}-m1",
                "title": "从一次「问数」看清主路径",
                "subtitle": "先跟随用户动作，再看系统接力",
                "html": f"""
<p class="lead animate-in">想象分析师在聊天框里写：「上周华东区退货率前 5 的类目？」——这不是魔法，而是一连串受控步骤。</p>
<div class="flow-steps animate-in">
  <div class="flow-step"><div class="flow-step-num">1</div><p>自然语言请求进入网关</p></div>
  <div class="flow-arrow">→</div>
  <div class="flow-step"><div class="flow-step-num">2</div><p>权限 / 限流 / 审计落盘</p></div>
  <div class="flow-arrow">→</div>
  <div class="flow-step"><div class="flow-step-num">3</div><p>生成并校验 SQL</p></div>
  <div class="flow-arrow">→</div>
  <div class="flow-step"><div class="flow-step-num">4</div><p>连接器访问数据源并返回</p></div>
</div>
<div class="flow-animation animate-in">
  <div class="flow-actors">
    <div class="flow-actor" id="dac-actor-1"><div class="flow-actor-icon" style="background:var(--color-actor-1)">人</div><span>业务 / Agent</span></div>
    <div class="flow-actor" id="dac-actor-2"><div class="flow-actor-icon" style="background:var(--color-actor-2)">网</div><span>网关 & 策略</span></div>
    <div class="flow-actor" id="dac-actor-3"><div class="flow-actor-icon" style="background:var(--color-actor-5)">库</div><span>数据源</span></div>
  </div>
  <div class="flow-label" id="dac-label">点击下方「下一步」开始</div>
  {flow_buttons("dac")}
</div>
{flow_script("dac", "dac", [{"hi": 1, "text": "① 用户或 Agent 用自然语言发起「问数」。"}, {"hi": 2, "text": "② 网关套用权限、限流，并记录审计信息。"}, {"hi": 3, "text": "③ 校验后的查询通过连接器到达真实数据库。"}])}
{translation_block(CODE_DAC, ["创建一个 FastAPI 应用对象，名字写在 OpenAPI 文档里。", "description 用一句话告诉使用者：这是孵化器统一数据出口。", "version 用来对齐发布与兼容性沟通。"])}
<div class="callout animate-in"><div class="callout-icon">💡</div><div><strong>直觉</strong><p style="margin:.35rem 0 0">网关的价值不在「多一个服务」，而在把危险与重复集中处理——就像机场安检统一做一遍。</p></div></div>
{std_quiz("quiz-dac-m1", [{"q": "你要限制某租户每日查询次数，优先改哪里？", "options": [("a", "在每个业务服务里手写计数器"), ("b", "在网关统一限流并写审计"), ("c", "在数据库里加触发器")], "correct": "b", "ok": "对：策略集中在网关，业务方少踩坑。", "bad": "分散实现容易漏掉一种调用路径。"}, {"q": "用户怀疑 SQL 被篡改，你最先查什么？", "options": [("a", "前端 CSS"), ("b", "审计日志与请求 ID 链路"), ("c", "浏览器缓存")], "correct": "b", "ok": "可观测性的第一证据通常是审计与追踪。", "bad": "再想想与请求绑定的记录。"}])}
""",
            },
            {
                "id": f"{slug}-m2",
                "title": "认识角色：谁在值班？",
                "subtitle": "路由、连接器、观测",
                "html": f"""
<div class="pattern-cards animate-in">
  <div class="pattern-card" style="border-top-color:var(--color-actor-1)"><h4 class="pattern-title">路由层</h4><p class="pattern-desc">把 {T('HTTP 是基于请求/响应的文本协议，常用于 REST API。', 'HTTP')} 路径分发给查询、连接器、向量检索等子系统。</p></div>
  <div class="pattern-card" style="border-top-color:var(--color-actor-2)"><h4 class="pattern-title">连接器</h4><p class="pattern-desc">把「某种数据库 / 对象存储」翻译成统一访问接口。</p></div>
  <div class="pattern-card" style="border-top-color:var(--color-actor-5)"><h4 class="pattern-title">观测与血缘</h4><p class="pattern-desc">延迟、错误率、字段血缘帮助回答「这次变更会影响谁」。 </p></div>
</div>
<div class="chat-window animate-in" id="chat_dac">
  <div class="chat-messages">
    <div class="chat-message" data-msg="0" data-sender="a">
      <div class="chat-avatar" style="background:var(--color-actor-1)">A</div>
      <div class="chat-bubble"><span class="chat-sender" style="color:var(--color-actor-1)">Agent</span><p>我要查订单表近 7 天 GMV。</p></div>
    </div>
    <div class="chat-message" data-msg="1" data-sender="b">
      <div class="chat-avatar" style="background:var(--color-actor-2)">G</div>
      <div class="chat-bubble"><span class="chat-sender" style="color:var(--color-actor-2)">网关</span><p>已检查租户权限与限流，生成 SQL 草案并送安全校验。</p></div>
    </div>
    <div class="chat-message" data-msg="2" data-sender="c">
      <div class="chat-avatar" style="background:var(--color-actor-5)">C</div>
      <div class="chat-bubble"><span class="chat-sender" style="color:var(--color-actor-5)">连接器</span><p>向 StarRocks 下发只读查询并流式取回结果集。</p></div>
    </div>
  </div>
  <div class="chat-typing"><div class="chat-avatar" style="background:#999">…</div><div style="display:flex;gap:4px;padding:8px 0"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div></div>
  <div class="chat-controls"><button type="button" class="btn secondary" onclick="chat_dac_next()">下一条</button><button type="button" class="btn secondary" onclick="chat_dac_reset()">重播</button></div>
</div>
{chat_script("chat_dac", "chat_dac")}
<div class="file-tree animate-in">src/main.py<br/>├─ register_builtin_connectors()  <span class="note"># 内置连接器注册</span><br/>├─ app.include_router(query_router)  <span class="note"># 查询 API</span><br/>└─ ... rbac / tenant / vector ...</div>
{translation_block('''<span class="code-keyword">register_builtin_connectors</span>()<br/><br/><span class="code-comment"># 注册路由</span><br/><span class="code-keyword">app</span>.include_router(query_router)<br/><span class="code-keyword">app</span>.include_router(connectors_router)''', ["启动时把「开箱即用」的数据源连接器注册进系统。", "include_router：把某一组 HTTP 路由挂到应用上。", "拆分路由文件，等于把菜单分门别类，避免单文件爆炸。"])}
{std_quiz("quiz-dac-m2", [{"q": "新增一种时序数据库接入，最少要动哪一类模块？", "options": [("a", "只改前端文案"), ("b", "实现连接器并注册到网关"), ("c", "只改 README")], "correct": "b", "ok": "连接器是扩展点。", "bad": "接入点通常在连接器与注册。"}, {"q": "为什么把 RBAC 放在服务里而不是浏览器？", "options": [("a", "前端不可信，权限必须在服务端强制执行"), ("b", "因为后端更快"), ("c", "为了好看")], "correct": "a", "ok": "安全边界在服务端。", "bad": "用户能改本地代码。"}])}
""",
            },
            {
                "id": f"{slug}-m3",
                "title": "数据如何在模块间旅行",
                "subtitle": "请求、校验、执行",
                "html": f"""
<p class="lead animate-in">{T('限流（rate limiting）限制单位时间内请求数量，防止打爆系统。', '限流')} 与 {T('RBAC（基于角色的访问控制）按角色授予操作范围。', 'RBAC')} 组合，才能既开放又安全。</p>
{translation_block('''<span class="code-keyword">from</span> api.query <span class="code-keyword">import</span> router <span class="code-keyword">as</span> query_router<br/><span class="code-keyword">from</span> core.rate_limiter <span class="code-keyword">import</span> rate_limiter''', ["从 query 模块导入一组 API 路由。", "rate_limiter 提供限流能力，供中间件或依赖注入使用。", "import as 给模块起别名，避免命名冲突。"])}
{std_quiz("quiz-dac-m3", [{"q": "某个查询偶发超时，你优先从哪里入手？", "options": [("a", "直接加机器"), ("b", "先看监控分位数与慢查询日志"), ("c", "重启开发机")], "correct": "b", "ok": "先定位再扩容。", "bad": "观测能告诉你是不是 SQL 本身问题。"}, {"q": "要把一次查询关联到业务责任人，靠什么？", "options": [("a", "随机猜"), ("b", "租户 ID + 审计字段 + 请求 ID"), ("c", "浏览器皮肤")], "correct": "b", "ok": "链路标识串联日志。", "bad": "需要可追踪字段。"}])}
""",
            },
            {
                "id": f"{slug}-m4",
                "title": "外面的世界：数据源与合规",
                "subtitle": "不是只有 MySQL",
                "html": f"""
<p class="lead animate-in">仓库里能看到 {T('向量索引把文本/图片等嵌入成向量，用于相似度检索。', '向量检索')}、非结构化加载器等——这意味着网关要同时服务「表格 SQL」与「语义检索」。</p>
{translation_block('''<span class="code-keyword">from</span> api.vector <span class="code-keyword">import</span> router <span class="code-keyword">as</span> vector_router<br/><span class="code-keyword">from</span> api.unstructured <span class="code-keyword">import</span> router <span class="code-keyword">as</span> unstructured_router''', ["vector_router：向量检索相关 HTTP 接口。", "unstructured_router：文档/网页等非结构化入口。", "多路由并存：同一网关暴露多种数据形态。"])}
{std_quiz("quiz-dac-m4", [{"q": "业务想上线「上传 PDF 问答」，你应该接哪条能力线？", "options": [("a", "只开 SQL 查询"), ("b", "非结构化加载 + 向量检索"), ("c", "只改图标")], "correct": "b", "ok": "先 ingestion 再检索。", "bad": "想想数据形态。"}, {"q": "合规团队要导出审计，你会暴露哪个 API 域？", "options": [("a", "logs/audit 相关路由"), ("b", "静态图片"), ("c", "favicon")], "correct": "a", "ok": "日志与审计接口服务合规。", "bad": "找与审计模型相关的路由。"}])}
""",
            },
            {
                "id": f"{slug}-m5",
                "title": "工程套路：可组合与可观测",
                "subtitle": "为什么拆这么多路由文件",
                "html": f"""
<div class="callout animate-in"><div class="callout-icon">🧭</div><div><strong>分离关注点</strong><p style="margin:.35rem 0 0">查询、监控、RBAC、租户、向量……各自演进，减少「改 A 崩 B」。</p></div></div>
{translation_block('''<span class="code-keyword">from</span> api.monitoring <span class="code-keyword">import</span> router <span class="code-keyword">as</span> monitoring_router<br/><span class="code-keyword">from</span> api.logs <span class="code-keyword">import</span> router <span class="code-keyword">as</span> logs_router''', ["monitoring_router：指标与健康检查入口。", "logs_router：日志检索/分析。", "运维与合规同事主要消费这两类端点。"])}
{std_quiz("quiz-dac-m5", [{"q": "要把 Grafana 接入告警，优先对接？", "options": [("a", "monitoring 服务暴露的指标"), ("b", "用户头像上传"), ("c", "前端主题色")], "correct": "a", "ok": "指标管道对接监控栈。", "bad": "找 observability 相关路由。"}, {"q": "为何把 schema 推荐独立成服务？", "options": [("a", "为了单点演化推荐算法而不影响核心查询"), ("b", "因为颜色更好看"), ("c", "没用")], "correct": "a", "ok": "独立模块可迭代。", "bad": "想想变更隔离。"}])}
""",
            },
            {
                "id": f"{slug}-m6",
                "title": "踩坑雷达与总览",
                "subtitle": "排障顺序建议",
                "html": f"""
<p class="lead animate-in">当你向 AI 描述需求时，用「数据源类型 + 操作类型 + 租户上下文 + 期望证据」四元组，能显著减少返工。</p>
{translation_block('''<span class="code-keyword">app</span> = FastAPI(<br/>    title=<span class="code-string">"Data-Agent Connector"</span>,<br/>    description=<span class="code-string">"孵化器统一数据出口：多源连接、Schema 发现、查询与 NL2SQL 在安全边界内可审计、可限流"</span>,<br/>    version=<span class="code-string">"1.3.0"</span><br/>)''', ["再次回到入口：title/description/version 是给人看的「铭牌」。", "把「安全 + 可审计 + 限流」写进描述，有助于对齐边界。", "版本号帮助判断示例代码是否过时。"])}
{std_quiz("quiz-dac-m6", [{"q": "用户看到 429 Too Many Requests，最先检查？", "options": [("a", "限流策略与配额"), ("b", "显示器亮度"), ("c", "字体大小")], "correct": "a", "ok": "429 通常与限流相关。", "bad": "HTTP 状态码含义。"}, {"q": "要把 NL2SQL 准确率问题交给产品同事，你应该给什么证据？", "options": [("a", "只有一句「很慢」"), ("b", "样例问句、生成 SQL、执行结果与审计 ID"), ("c", "随机截图")], "correct": "b", "ok": "可复现证据链。", "bad": "需要可验证材料。"}])}
""",
            },
        ],
    }


# 为节省篇幅，其余九个项目使用同一骨架 + 不同文案/代码引用

def _generic(slug: str, title: str, pill: str, accent: str, intro: str, code: str, code_lines: list[str], extra_m1: str = "") -> dict:
    fn = slug.replace("-", "_")
    chat_id = "chat_" + fn

    def qb(n: str, qs: list[dict]) -> str:
        return std_quiz(f"quiz-{slug}-m{n}", qs)

    m1 = f"""
<p class="lead animate-in">{extra_m1}</p>
<div class="flow-animation animate-in">
  <div class="flow-actors">
    <div class="flow-actor" id="{slug}-actor-1"><div class="flow-actor-icon" style="background:var(--color-actor-1)">用</div><span>用户 / 调用方</span></div>
    <div class="flow-actor" id="{slug}-actor-2"><div class="flow-actor-icon" style="background:var(--color-actor-2)">服</div><span>FastAPI 服务</span></div>
    <div class="flow-actor" id="{slug}-actor-3"><div class="flow-actor-icon" style="background:var(--color-actor-5)">外</div><span>外部能力</span></div>
  </div>
  <div class="flow-label" id="{slug}-label">点击下一步看链路</div>
  {flow_buttons(fn)}
</div>
{flow_script(slug, fn, [{"hi": 1, "text": "① 调用方发起 HTTP 请求。"}, {"hi": 2, "text": "② FastAPI 路由执行业务逻辑。"}, {"hi": 3, "text": "③ 访问数据库 / LLM / 第三方 API 并返回。"}])}
{translation_block(code, code_lines)}
{qb("1", [{"q": "需求是「可观测 + 可审计」，你应避免？", "options": [("a", "把密钥写进前端"), ("b", "服务端记录请求 ID"), ("c", "结构化日志")], "correct": "a", "ok": "秘密留在服务端。", "bad": "前端可被用户查看。"}, {"q": "上线前最重要的检查？", "options": [("a", "README 字数"), ("b", "健康检查与最小权限"), ("c", "图标圆角")], "correct": "b", "ok": "可用性与安全基线。", "bad": "再想工程风险。"}])}
"""

    m2 = f"""
<div class="chat-window animate-in" id="{chat_id}">
  <div class="chat-messages">
    <div class="chat-message"><div class="chat-avatar" style="background:var(--color-actor-1)">U</div><div class="chat-bubble"><span class="chat-sender" style="color:var(--color-actor-1)">客户端</span><p>调用一个需要鉴权的 API。</p></div></div>
    <div class="chat-message"><div class="chat-avatar" style="background:var(--color-actor-2)">S</div><div class="chat-bubble"><span class="chat-sender" style="color:var(--color-actor-2)">服务</span><p>校验 {T('API Key 是调用方持有的密钥，相当于长期门票。', 'API Key')} / JWT 并执行业务。</p></div></div>
    <div class="chat-message"><div class="chat-avatar" style="background:var(--color-actor-5)">X</div><div class="chat-bubble"><span class="chat-sender" style="color:var(--color-actor-5)">外部</span><p>访问模型或数据库并返回结构化结果。</p></div></div>
  </div>
  <div class="chat-typing"><div class="chat-avatar" style="background:#999">…</div><div style="display:flex;gap:4px;padding:8px 0"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div></div>
  <div class="chat-controls"><button type="button" class="btn secondary" onclick="{chat_id}_next()">下一条</button><button type="button" class="btn secondary" onclick="{chat_id}_reset()">重播</button></div>
</div>
{chat_script(chat_id, chat_id)}
{translation_block(code, code_lines)}
{qb("2", [{"q": "为什么拆分多个 router 文件？", "options": [("a", "减少单文件复杂度，边界清晰"), ("b", "让 Git 生气"), ("c", "必然更快")], "correct": "a", "ok": "维护性优先。", "bad": "想想协作成本。"}, {"q": "CORS 中间件主要解决？", "options": [("a", "浏览器跨域访问控制"), ("b", "数据库锁"), ("c", "CPU 温度")], "correct": "a", "ok": "浏览器安全模型相关。", "bad": "回忆前后端分离场景。"}])}
"""

    m3 = f"""<p class="lead animate-in">模块间通信多用 {T('HTTP 路由把 URL 映射到处理函数。', '路由')} 与 {T('依赖注入在请求生命周期内组装数据库会话等依赖。', '依赖注入')}；再配合 {T('集成测试验证多个模块连起来是否工作。', '集成测试')} 更稳。</p>
{translation_block(code, code_lines)}
{qb("3", [{"q": "要加缓存，最不容易翻车的是？", "options": [("a", "先定义键与失效策略"), ("b", "到处加 sleep"), ("c", "禁用日志")], "correct": "a", "ok": "缓存要先有契约。", "bad": "想想一致性。"}])}"""

    m4 = f"""<p class="lead animate-in">外部世界包括 {T('关系型数据库用表和 SQL 存结构化数据。', '数据库')}、消息队列、{T('LLM（大语言模型）用于生成与分析文本。', 'LLM')} 与 {T('SaaS（软件即服务）是别人托管的在线服务，按订阅使用。', 'SaaS')}。</p>
{translation_block(code, code_lines)}
{qb("4", [{"q": "密钥应放哪里？", "options": [("a", "环境变量 / 密钥管理系统"), ("b", "前端仓库"), ("c", "微信群")], "correct": "a", "ok": "秘密不进版本库。", "bad": "合规 Basics。"}])}"""

    m5 = f"""<div class="callout animate-in"><div class="callout-icon">💡</div><div><strong>模式</strong><p style="margin:.35rem 0 0">把横切关注点放进 {T('中间件在请求进入前后统一处理日志、鉴权等。', '中间件')} 或依赖；{T('技术栈指语言、框架、数据库等选型组合。', '技术栈')} 清晰后更易协作。</p></div></div>
{translation_block(code, code_lines)}
{qb("5", [{"q": "中间件最适合做？", "options": [("a", "统一日志与 trace id"), ("b", "业务规则细节"), ("c", "手写 SQL 字符串拼接")], "correct": "a", "ok": "横切关注点。", "bad": "想想重复劳动。"}])}"""

    m6 = f"""<p class="lead animate-in">排障：先复现 → 再看 {T('日志是运行时的文本记录，用于排查问题。', '日志')} / {T('分布式追踪用一条 trace id 串起多个服务调用。', 'trace')} → 最小化差异（版本、数据、配置）。</p>
{translation_block(code, code_lines)}
{qb("6", [{"q": "向 AI 描述 bug 时最有用的是？", "options": [("a", "期望 vs 实际 + 复现步骤 + 相关日志 ID"), ("b", "只说「坏了」"), ("c", "抱怨")], "correct": "a", "ok": "可复现信息。", "bad": "协作需要证据。"}])}"""

    return {
        "folder": slug,
        "slug": slug,
        "title": title,
        "pill": pill,
        "accent": accent,
        "intro": intro,
        "modules": [
            {"id": f"{slug}-m1", "title": "产品在做什么", "subtitle": "用户路径", "html": m1},
            {"id": f"{slug}-m2", "title": "关键角色", "subtitle": "对话与结构", "html": m2},
            {"id": f"{slug}-m3", "title": "模块如何协作", "subtitle": "路由与依赖", "html": m3},
            {"id": f"{slug}-m4", "title": "外部系统", "subtitle": "数据与模型", "html": m4},
            {"id": f"{slug}-m5", "title": "工程套路", "subtitle": "中间件与边界", "html": m5},
            {"id": f"{slug}-m6", "title": "排障与收束", "subtitle": "如何向 AI 描述问题", "html": m6},
        ],
    }


PROJECTS: list[dict] = [
    dac(),
    _generic(
        "ai-opportunity-miner",
        "AI Opportunity Miner · 商机挖掘",
        "B2B 情报 · DeerFlow 2.0",
        "#D94F30",
        "把公开与授权数据压成「可验证假设」：不是八卦新闻列表，而是能跟进、能证伪的线索。",
        CODE_MINER,
        [
            "创建 FastAPI 应用，标题出现在自动文档 /docs。",
            "description 强调 DeerFlow 2.0 与真实数据源。",
            "version 帮助判断示例是否匹配当前行为。",
        ],
        extra_m1="编排型 Agent 把抓取、评分、导出拆成可审计步骤。",
    ),
    _generic(
        "ai-code-understanding",
        "AI Code Understanding · 代码认知",
        "开发者工具 · 可溯源",
        "#E06B56",
        "为 Cursor/Claude 时代准备「地图」：全局结构、依赖影响、任务阅读顺序，而不是再做一个补全。",
        CODE_CU,
        [
            "FastAPI 承载 HTTP API。",
            "description 列出能力：解释、摘要、问答、地图、任务引导。",
            "version 标记迭代阶段（P5 等）。",
        ],
        extra_m1="当你说「帮我改计费」，系统应先指出跨文件影响面。",
    ),
    _generic(
        "ai-runtime-optimizer",
        "AI Runtime Optimizer · 运行态优化",
        "可观测性 + 修复闭环",
        "#2D8B55",
        "从指标与用户行为出发，走向根因与「可评审的代码改动」，而不是只贴 Grafana 截图。",
        CODE_RT,
        [
            "FastAPI 作为优化建议与修复提案的入口。",
            "description 写明需要人工/CI 评审。",
            "version 对齐发布与兼容性。",
        ],
        extra_m1="异常是信号，根因是故事，修复是补丁。",
    ),
    _generic(
        "ai-traffic-booster",
        "AI Traffic Booster · 流量增长",
        "增长参谋",
        "#D4A843",
        "弥合数据 → 洞察 → 行动：让建议能落地到页面/实验，并记录效果形成闭环。",
        CODE_TRAFFIC,
        [
            "应用在生命周期开始时打印名称与版本，便于日志对齐。",
            "f-string 把变量插进字符串。",
            "这是排障时最先搜索的关键字之一。",
        ],
        extra_m1="增长问题常常是漏斗里某一步断裂，而不是「全站流量」一个数。",
    ),
    _generic(
        "human-ai-community",
        "Human-AI Community · 人机社区",
        "身份 · 治理 · 协作",
        "#7B6DAA",
        "让人类、AI、混合身份同场竞技时仍透明：标注、审计、治理工具与社区经济。",
        CODE_COMM,
        [
            "community_router：社区核心 API（帖子、成员等）。",
            "router 是 FastAPI 的路由分组。",
            "import as 避免名字冲突。",
        ],
        extra_m1="像市政大厅：不仅要能发言，还要能查证「谁在说话」。",
    ),
    _generic(
        "ai-employee-platform",
        "AI Employee Platform · AI 员工出租",
        "平台经济 · 可度量",
        "#2A7B9B",
        "把可训练、可观测的 AI 能力包装成可租赁的「员工」，匹配、合约、结算都能讲清楚。",
        CODE_EMP,
        [
            "employees_router：雇员档案与雇佣关系。",
            "路由分文件承载不同子域能力。",
            "主入口负责装配，而不是写业务细节。",
        ],
        extra_m1="市场要的是「可交付的工作单元」，不是一次性 API 调用的幻觉。",
    ),
    _generic(
        "ai-hires-human",
        "AI Hires Human · AI 雇真人",
        "人机众包 · 结构化回传",
        "#C4432A",
        "当 AI 需要线下核实或主观判断时，用任务把人接进来，再把结构化结果喂回 Agent。",
        CODE_HIRE,
        [
            "模块文档字符串说明产品边界：AI 做不到时找人。",
            "docstring 会出现在部分工具的提示里。",
            "先讲清楚非目标，避免需求爆炸。",
        ],
        extra_m1="任务要声明能力缺口与验收标准，否则众包会沦为扯皮。",
    ),
    _generic(
        "matchmaker-agent",
        "Matchmaker Agent · 红娘",
        "严肃婚恋 · 可解释",
        "#D94F30",
        "深度匹配与安全：解释为什么推荐，而不是只给「滑卡片」式冷启动。",
        CODE_MATCH,
        [
            "FastAPI 承载匹配与消息等 API。",
            "description 写明 JWT 与 SQLite 持久化。",
            "debug  flag 影响日志详细程度。",
        ],
        extra_m1="婚恋场景最怕黑箱与隐私失控，可解释与合规是默认项。",
    ),
    _generic(
        "ai-community-buying",
        "AI Community Buying · 社区团购",
        "本地商业 · 预测与定价",
        "#2D8B55",
        "用预测与个性化帮助团长选品、成团与定价，而不是自建全国仓配。",
        CODE_BUY,
        [
            "products_router：商品与团购 SKU 相关接口。",
            "路由按业务域拆分，便于并行开发。",
            "主入口只负责装配。",
        ],
        extra_m1="社区零售的关键是「信 + 时效 + 成团概率」。",
    ),
]
