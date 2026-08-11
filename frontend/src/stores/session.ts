import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sessionAPI, aiAPI, logisticsAPI, type SessionItem, type MessageItem, type OrderItem, type ReplyItem, type LogisticsOrderItem } from '../api/session'

/**
 * AI 置信度纯函数：基于 risk/emotion/intent 推算。
 * 抽成独立函数便于「消息生成时打快照」与「面板实时显示」共用同一套规则，
 * 避免每条 AI 气泡都跟着当前会话状态联动变化。
 */
export function calcConfidence(risk?: string, emotion?: string, intent?: string): number {
  let score = 92 // 基础分（RAG+DeepSeek 通常能给出可靠回复）
  if (risk?.includes('高风险')) score -= 18
  else if (risk?.includes('中风险')) score -= 8
  const negativeEmotions = ['愤怒', '激动', '不满']
  if (negativeEmotions.includes(emotion || '')) score -= 15
  else if (emotion === '略有不满' || emotion === '略有焦虑') score -= 5
  if (!intent || intent === '待识别') score -= 12
  const wellCovered = ['产品咨询', '物流查询', '优惠咨询', '安装指导', '商品推荐', '退换咨询']
  if (intent && wellCovered.includes(intent)) score += 5
  return Math.max(0, Math.min(100, score))
}

/** 单个会话的详情缓存 */
interface SessionCache {
  messages: MessageItem[]
  orders: OrderItem[]
  replies: ReplyItem[]
  logistics: LogisticsOrderItem[]
  loadedAt: number  // 加载时间戳，用于判断是否需要刷新
}

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<SessionItem[]>([])
  const currentSession = ref<SessionItem | null>(null)
  const messages = ref<MessageItem[]>([])
  const orders = ref<OrderItem[]>([])
  const replies = ref<ReplyItem[]>([])
  const logistics = ref<LogisticsOrderItem[]>([])
  const currentTab = ref('all')
  const searchKeyword = ref('')
  const loading = ref(false)
  const simulating = ref(false)        // 是否正在模拟中
  const aiThinking = ref(false)        // AI正在思考（模拟客户消息后等待AI分析）
  let simTimer: ReturnType<typeof setInterval> | null = null

  /** 会话详情缓存：sessionId -> SessionCache */
  const cache = new Map<number, SessionCache>()
  /** 缓存有效期：60秒，超过则后台刷新 */
  const CACHE_TTL = 60_000
  /** 当前正在加载的会话ID（防止重复请求） */
  let loadingSessionId: number | null = null
  /** 正在预取的会话：sessionId -> 完成Promise */
  const prefetching = new Map<number, Promise<void>>()

  const filteredSessions = computed(() => {
    let list = sessions.value
    if (currentTab.value === 'ai') list = list.filter(s => s.tab === 'ai')
    else if (currentTab.value === 'wait') list = list.filter(s => s.tab === 'wait')
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase()
      list = list.filter(s => s.user_name.includes(kw) || s.preview.includes(kw))
    }
    return list
  })

  const tabCounts = computed(() => ({
    all: sessions.value.length,
    ai: sessions.value.filter(s => s.tab === 'ai').length,
    wait: sessions.value.filter(s => s.tab === 'wait').length,
  }))

  async function fetchSessions(silent: boolean = false) {
    if (!silent) loading.value = true
    try {
      // 始终拉取全部会话，前端自己过滤，保证tab计数正确
      const list = await sessionAPI.list({ tab: 'all' })
      // 增量更新：按 id 建立旧列表索引比较，避免排序变化导致整表替换闪烁
      const oldList = sessions.value
      const oldMap = new Map(oldList.map(s => [s.id, s]))
      const changed = list.length !== oldList.length ||
        list.some(s => {
          const o = oldMap.get(s.id)
          return !o || o.preview !== s.preview || o.tab !== s.tab ||
            o.time !== s.time || o.score !== s.score || o.intent !== s.intent ||
            o.emotion !== s.emotion
        })
      if (changed) {
        sessions.value = list
      }
    } finally {
      if (!silent) loading.value = false
    }
  }

  /** 从缓存填充到当前响应式状态 */
  function applyCache(c: SessionCache) {
    messages.value = c.messages
    orders.value = c.orders
    replies.value = c.replies
    logistics.value = c.logistics
  }

  /** 预取会话数据（后台静默加载，完成后才写入缓存，不更新界面） */
  function prefetchSession(id: number) {
    if (cache.has(id) || prefetching.has(id)) return
    const promise = (async () => {
      try {
        const [msgs, ords, reps, logs] = await Promise.all([
          sessionAPI.getMessages(id).catch(() => []),
          sessionAPI.getOrders(id).catch(() => []),
          sessionAPI.getReplies(id).catch(() => []),
          logisticsAPI.getBySession(id).catch(() => ({ orders: [] })),
        ])
        cache.set(id, {
          messages: msgs,
          orders: ords,
          replies: reps,
          logistics: logs.orders || [],
          loadedAt: Date.now(),
        })
      } finally {
        prefetching.delete(id)
      }
    })()
    prefetching.set(id, promise)
  }

  /** 预取列表中相邻的会话（上下各一个） */
  function prefetchAdjacent(id: number) {
    const idx = sessions.value.findIndex(s => s.id === id)
    if (idx === -1) return
    if (idx > 0) prefetchSession(sessions.value[idx - 1].id)
    if (idx < sessions.value.length - 1) prefetchSession(sessions.value[idx + 1].id)
  }

  /**
   * 加载会话详情：分批更新，每个请求完成即更新对应数据，不互相阻塞。
   * 第一批（基本信息+消息）完成后返回，其余后台陆续填充。
   */
  async function refreshSessionData(id: number) {
    const isCurrent = () => currentSession.value?.id === id

    // 第一批：基本信息 + 聊天消息（用户最关心的聊天区，优先加载）
    const pSession = sessionAPI.get(id)
      .then(s => { if (isCurrent()) currentSession.value = s })
      .catch(() => {})
    const pMessages = sessionAPI.getMessages(id)
      .then(msgs => {
        if (isCurrent()) messages.value = msgs
        // 写入缓存
        let c = cache.get(id)
        if (!c) {
          c = { messages: msgs, orders: [], replies: [], logistics: [], loadedAt: Date.now() }
          cache.set(id, c)
        } else {
          c.messages = msgs
          c.loadedAt = Date.now()
        }
      })
      .catch(() => {})

    // 等第一批完成即可返回（界面已有聊天内容）
    await Promise.all([pSession, pMessages])

    // 第二批：订单 + 推荐话术 + 物流（后台独立加载，完成一个显示一个）
    sessionAPI.getOrders(id)
      .then(ords => {
        if (isCurrent()) orders.value = ords
        const c = cache.get(id); if (c) c.orders = ords
      })
      .catch(() => {})
    sessionAPI.getReplies(id)
      .then(reps => {
        if (isCurrent()) replies.value = reps
        const c = cache.get(id); if (c) c.replies = reps
      })
      .catch(() => {})
    logisticsAPI.getBySession(id)
      .then(logs => {
        if (isCurrent()) logistics.value = logs.orders || []
        const c = cache.get(id); if (c) c.logistics = logs.orders || []
      })
      .catch(() => {})
  }

  async function loadSession(id: number) {
    // 防止重复加载同一会话
    if (loadingSessionId === id) return
    loadingSessionId = id

    try {
      // 切换会话时重置 AI 思考状态，避免旧会话的思考动画泄漏到新会话
      aiThinking.value = false

      // 1. 乐观更新：先从 sessions 列表取基本信息立即显示
      const cachedSession = sessions.value.find(s => s.id === id)
      if (cachedSession) {
        currentSession.value = { ...cachedSession }
      }

      // 2. 如果有正在进行的预取，等待它完成（比从头加载快，请求已发出）
      const pending = prefetching.get(id)
      if (pending) await pending

      // 3. 检查缓存
      const c = cache.get(id)
      if (c) {
        applyCache(c)
        // 缓存未过期，无需后台刷新
        if (Date.now() - c.loadedAt < CACHE_TTL) {
          prefetchAdjacent(id)
          return
        }
        // 缓存过期，后台静默刷新
        refreshSessionData(id)
        prefetchAdjacent(id)
        return
      }

      // 4. 无缓存：清空所有面板数据，分批加载（第一批消息很快到达）
      messages.value = []
      orders.value = []
      replies.value = []
      logistics.value = []
      await refreshSessionData(id)
      prefetchAdjacent(id)
    } finally {
      loadingSessionId = null
    }
  }

  async function sendMessage(text: string, type: string = 'agent', hasProduct: boolean = false) {
    if (!currentSession.value) return
    const sid = currentSession.value.id
    const msg = await sessionAPI.sendMessage(sid, {
      session_id: sid,
      dir: 'left',
      text,
      type,
      has_product: hasProduct ? 1 : 0,
    })
    // 按 id 去重添加（防止后端已保存的消息和本地 push 重复）
    const exists = messages.value.some(m => m.id === msg.id)
    if (!exists) messages.value.push(msg)
    // 同步更新缓存
    const c = cache.get(sid)
    if (c) {
      const cachedExists = c.messages.some(m => m.id === msg.id)
      if (!cachedExists) c.messages.push(msg)
    }
    // 更新会话预览
    if (currentSession.value) {
      currentSession.value.preview = text
      currentSession.value.time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    return msg
  }

  /** 发送系统消息（归档、提示等） */
  async function sendSystemMessage(text: string) {
    if (!currentSession.value) return
    const sid = currentSession.value.id
    const msg = await sessionAPI.sendMessage(sid, {
      session_id: sid,
      dir: 'center',
      text,
      type: 'system-msg',
      has_product: 0,
    })
    const exists = messages.value.some(m => m.id === msg.id)
    if (!exists) messages.value.push(msg)
    // 同步更新缓存
    const c = cache.get(sid)
    if (c) {
      const cachedExists = c.messages.some(m => m.id === msg.id)
      if (!cachedExists) c.messages.push(msg)
    }
    return msg
  }

  async function transferSession() {
    if (!currentSession.value) return
    await sessionAPI.updateTab(currentSession.value.id, 'wait')
    currentSession.value.tab = 'wait'
    currentSession.value.tags = [{ text: '已转人工', cls: 'bg-orange-50 text-warning' }]
    await fetchSessions()
  }

  async function markRisk() {
    if (!currentSession.value) return
    await sessionAPI.markRisk(currentSession.value.id)
    currentSession.value.risk = '🔴 高风险'
    currentSession.value.risk_class = 'bg-red-50 text-danger'
    currentSession.value.tab = 'wait'
    currentSession.value.tags = [{ text: '高风险标记', cls: 'bg-red-50 text-danger' }]
    await fetchSessions()
  }

  async function endSession() {
    if (!currentSession.value) return
    await sessionAPI.updateStatus(currentSession.value.id, 'closed')
    currentSession.value.status = 'closed'
    currentSession.value.tags = [{ text: '已结束', cls: 'bg-gray-100 text-gray-500' }]
  }

  /** 清除当前会话聊天记录 */
  async function clearMessages() {
    if (!currentSession.value) return
    const sid = currentSession.value.id
    await sessionAPI.clearMessages(sid)
    messages.value = []
    replies.value = []
    aiThinking.value = false
    // 同步清空缓存
    const c = cache.get(sid)
    if (c) {
      c.messages = []
      c.replies = []
    }
    if (currentSession.value) {
      currentSession.value.preview = ''
      currentSession.value.intent = ''
      currentSession.value.emotion = ''
      currentSession.value.emotion_class = ''
      currentSession.value.risk = ''
      currentSession.value.risk_class = ''
      currentSession.value.segment = ''
      currentSession.value.score = 0
      currentSession.value.score_color = ''
      currentSession.value.value_desc = ''
    }
  }

  /** 删除会话 */
  async function deleteSession(id: number) {
    await sessionAPI.deleteSession(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    cache.delete(id)
    if (currentSession.value?.id === id) {
      currentSession.value = null
      messages.value = []
      orders.value = []
      replies.value = []
      logistics.value = []
    }
  }

  /** 一键清除所有客户信息（初始化工作台） */
  async function clearAll() {
    const resp = await sessionAPI.clearAll()
    // 清空所有前端状态
    cache.clear()
    sessions.value = []
    currentSession.value = null
    messages.value = []
    orders.value = []
    replies.value = []
    logistics.value = []
    return resp
  }

  /** 模拟客户发送消息，分步展示：客户消息 → AI思考 → AI回答 */
  async function simulateCustomer(intent?: string) {
    if (!currentSession.value) return null
    const sid = currentSession.value.id

    try {
      // ====== Step 1: 调用simulate-customer，生成客户消息并立即返回 ======
      const simResult = await aiAPI.simulateCustomer(sid, intent)

      // 如果后端返回 waiting，说明客服/AI还没回复，客户在等待
      if (simResult.status === 'waiting' || !simResult.message) {
        return { status: 'waiting' }
      }

      // ====== Step 2: 立即显示客户消息（左侧白色气泡），按 id 去重 ======
      const exists1 = messages.value.some(m => m.id === simResult.message.id)
      if (!exists1) {
        messages.value.push(simResult.message)
      }
      // 同步更新缓存
      const c = cache.get(sid)
      if (c) {
        const cachedExists1 = c.messages.some(m => m.id === simResult.message.id)
        if (!cachedExists1) c.messages.push(simResult.message)
      }
      if (currentSession.value) {
        currentSession.value.preview = simResult.message.text
        currentSession.value.time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      }

      // 催促消息不需要AI分析（客户只是在催客服回复）
      if (simResult.is_urge) {
        return { status: 'ok', message: simResult.message, is_urge: true }
      }

      // ====== Step 3: 开启AI思考动画，调用analyze-customer进行RAG+DeepSeek分析 ======
      // 最少展示 1100ms，确保动画可见
      aiThinking.value = true
      const minShow = new Promise<void>(r => setTimeout(r, 1100))
      const analyzePromise = aiAPI.analyzeCustomer(sid)
      const [analyzeResult] = await Promise.all([analyzePromise, minShow])
      // 等待结束后若会话已切换，不再追加任何内容（避免污染新会话）
      if (currentSession.value?.id !== sid) return { status: 'ok', message: simResult.message, is_urge: !!simResult.is_urge }

      // ====== Step 4: 显示AI回答（如果可自动回答），按 id 去重 ======
      if (analyzeResult.auto_answer) {
        // confidence 由后端在生成时计算并写入数据库，前端直接使用，无需再赋值
        const exists2 = messages.value.some(m => m.id === analyzeResult.auto_answer.id)
        if (!exists2) {
          messages.value.push(analyzeResult.auto_answer)
        }
        const c2 = cache.get(sid)
        if (c2) {
          const cachedExists2 = c2.messages.some(m => m.id === analyzeResult.auto_answer.id)
          if (!cachedExists2) c2.messages.push(analyzeResult.auto_answer)
        }
      }

      // ====== Step 5: 更新AI分析面板和推荐话术 ======
      if (currentSession.value) {
        const a = analyzeResult.analysis
        currentSession.value.intent = a.intent
        currentSession.value.emotion = a.emotion
        currentSession.value.emotion_class = a.emotion_class
        currentSession.value.risk = a.risk
        currentSession.value.risk_class = a.risk_class
        currentSession.value.segment = a.segment
        currentSession.value.score = a.score
        currentSession.value.score_color = a.score_color
        currentSession.value.value_desc = a.value_desc
      }
      // 更新推荐话术（用时间戳生成唯一 id，确保 Vue 重建 DOM 触发进场动画）
      const replyBatch = Date.now()
      const newReplies = analyzeResult.analysis.suggested_replies.map((text, i) => ({
        id: replyBatch + i,
        text,
        sort_order: i,
      }))
      replies.value = newReplies
      // 同步更新缓存
      const c3 = cache.get(sid)
      if (c3) c3.replies = newReplies

      return {
        status: 'ok',
        message: simResult.message,
        analysis: analyzeResult.analysis,
      }
    } catch (e) {
      console.error('模拟客户消息失败:', e)
      return null
    } finally {
      // 只有当前会话仍是本次模拟的会话时，才重置 aiThinking
      // 避免旧会话的 finally 关闭新会话的思考动画
      if (currentSession.value?.id === sid) {
        aiThinking.value = false
      }
    }
  }

  /** 开启/关闭自动模拟 */
  function toggleAutoSimulate() {
    if (simTimer) {
      clearInterval(simTimer)
      simTimer = null
      simulating.value = false
    } else {
      simulating.value = true
      // 自动模式：每8秒尝试发一条消息
      // 如果客户在等待回复（返回waiting），会自动跳过，等下个周期再试
      simTimer = setInterval(() => {
        simulateCustomer()
      }, 8000)
    }
  }

  /** 停止自动模拟 */
  function stopAutoSimulate() {
    if (simTimer) {
      clearInterval(simTimer)
      simTimer = null
    }
    simulating.value = false
  }

  /** 催件 */
  async function urgeLogistics(trackingNo: string) {
    const result = await logisticsAPI.urge(trackingNo)
    // 重新加载物流数据
    if (currentSession.value) {
      const sid = currentSession.value.id
      const logs = await logisticsAPI.getBySession(sid)
      logistics.value = logs.orders || []
      // 同步更新缓存
      const c = cache.get(sid)
      if (c) c.logistics = logs.orders || []
    }
    return result
  }

  /**
   * 轮询当前会话的新消息（客户端发来的消息会自动出现在工作台）。
   * 检测到新的客户消息时，先显示客户消息 → AI思考动画 → 显示AI回复 → 刷新推荐话术。
   */
  async function pollCurrentMessages() {
    if (!currentSession.value) return false
    const sid = currentSession.value.id
    // 判断当前会话是否仍是本次轮询的会话（防止切换会话后旧轮询污染新会话）
    const stillCurrent = () => currentSession.value?.id === sid
    try {
      const msgs = await sessionAPI.getMessages(sid)
      // 拉取完成后，如果会话已切换，丢弃本次结果
      if (!stillCurrent()) return false
      // 区分新消息（按 id 去重）
      const newMsgs = msgs.filter(m => !messages.value.some(x => x.id === m.id))
      if (newMsgs.length === 0) return false

      const c = cache.get(sid)
      // 分离客户消息和 AI/客服消息
      const newCustomerMsgs = newMsgs.filter(m => m.dir === 'right')
      const newOtherMsgs = newMsgs.filter(m => m.dir !== 'right')

      // 如果有新的客户消息：先显示客户消息，再播放 AI 思考动画
      if (newCustomerMsgs.length > 0) {
        // 先只追加客户消息
        for (const m of newCustomerMsgs) {
          messages.value.push(m)
          if (c && !c.messages.some(x => x.id === m.id)) c.messages.push(m)
        }
        // 更新会话预览
        const lastCust = newCustomerMsgs[newCustomerMsgs.length - 1]
        if (stillCurrent()) {
          currentSession.value!.preview = lastCust.text
          currentSession.value!.time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        }

        // 开启 AI 思考动画，最少展示 1100ms
        aiThinking.value = true
        await new Promise<void>(r => setTimeout(r, 1100))
        // 等待结束后，如果会话已切换，不再追加任何消息（避免污染新会话）
        if (!stillCurrent()) {
          // 仅当当前会话没有其他思考中的操作时才关闭，避免关闭新会话的动画
          return false
        }
        aiThinking.value = false

        // 显示其他新消息（后端已生成的 AI 回复等），按 id 去重
        for (const m of newOtherMsgs) {
          if (!messages.value.some(x => x.id === m.id)) {
            messages.value.push(m)
          }
          if (c && !c.messages.some(x => x.id === m.id)) c.messages.push(m)
        }

        // 刷新推荐话术和分析面板（后端在客户发消息时已更新 Reply 表和 Session 字段）
        try {
          const [sessionDetail, newReplies] = await Promise.all([
            sessionAPI.get(sid),
            sessionAPI.getReplies(sid),
          ])
          if (!stillCurrent()) return false
          if (currentSession.value) {
            currentSession.value.intent = sessionDetail.intent
            currentSession.value.emotion = sessionDetail.emotion
            currentSession.value.emotion_class = sessionDetail.emotion_class
            currentSession.value.risk = sessionDetail.risk
            currentSession.value.risk_class = sessionDetail.risk_class
            currentSession.value.segment = sessionDetail.segment
            currentSession.value.score = sessionDetail.score
            currentSession.value.score_color = sessionDetail.score_color
            currentSession.value.value_desc = sessionDetail.value_desc
            currentSession.value.tab = sessionDetail.tab
            currentSession.value.tags = sessionDetail.tags
          }
          // 用时间戳生成唯一 id，确保 Vue 重建 DOM 触发进场动画
          const replyBatch = Date.now()
          replies.value = newReplies.map((r, i) => ({
            id: replyBatch + i,
            text: r.text,
            sort_order: i,
          }))
          if (c) c.replies = replies.value
        } catch (e) {
          console.error('刷新分析面板失败:', e)
        }
      } else {
        // 没有新的客户消息，直接追加其他新消息
        for (const m of newOtherMsgs) {
          messages.value.push(m)
          if (c && !c.messages.some(x => x.id === m.id)) c.messages.push(m)
        }
        // 更新会话预览
        const last = newOtherMsgs[newOtherMsgs.length - 1]
        if (last && stillCurrent()) {
          currentSession.value!.preview = last.text
          currentSession.value!.time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        }
      }

      return true
    } catch {
      return false
    }
  }

  return {
    sessions, currentSession, messages, orders, replies, logistics,
    currentTab, searchKeyword, loading, simulating, aiThinking,
    filteredSessions, tabCounts,
    fetchSessions, loadSession, sendMessage, sendSystemMessage, transferSession, markRisk, endSession,
    clearMessages, deleteSession, clearAll, urgeLogistics, pollCurrentMessages,
    simulateCustomer, toggleAutoSimulate, stopAutoSimulate,
  }
})
