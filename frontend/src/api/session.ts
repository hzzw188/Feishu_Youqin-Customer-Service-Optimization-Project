import api from './index'

export interface SessionItem {
  id: number
  user_name: string
  user_avatar: string
  user_tag: string
  user_tag_class: string
  source: string
  platform: string
  user_desc: string
  intent: string
  emotion: string
  emotion_class: string
  risk: string
  risk_class: string
  segment: string
  score: number
  score_color: string
  value_desc: string
  preview: string
  tab: string
  status: string
  time: string
  tags: { text: string; cls: string }[]
  created_at: string
  updated_at: string
}

export interface MessageItem {
  id: number
  dir: string
  text: string
  type: string
  has_product: boolean
  created_at: string
  /** AI 回答生成时的置信度快照（仅 type==='ai' 有值），避免所有气泡跟随当前会话状态联动 */
  confidence?: number
}

export interface OrderItem {
  id: number
  name: string
  status: string
  status_class: string
  order_no: string
  price: string
  platform: string
  logistics_status?: string
  tracking_no?: string
  carrier?: string
}

export interface ReplyItem {
  id: number
  text: string
  sort_order: number
}

export interface LogisticsTrackItem {
  time: string
  location: string
  desc: string
}

export interface LogisticsOrderItem {
  order_id: number
  order_no: string
  product_name: string
  tracking_no: string
  carrier: string
  status: string
  status_label: string
  timeline: LogisticsTrackItem[]
}

export const sessionAPI = {
  list(params?: { tab?: string; search?: string; platform?: string }) {
    return api.get('/sessions', { params }) as Promise<SessionItem[]>
  },
  get(id: number) {
    return api.get(`/sessions/${id}`) as Promise<SessionItem>
  },
  getMessages(id: number) {
    return api.get(`/sessions/${id}/messages`) as Promise<MessageItem[]>
  },
  sendMessage(id: number, data: { session_id: number; dir: string; text: string; type: string; has_product?: number }) {
    return api.post(`/sessions/${id}/messages`, data) as Promise<MessageItem>
  },
  getOrders(id: number) {
    return api.get(`/sessions/${id}/orders`) as Promise<OrderItem[]>
  },
  getReplies(id: number) {
    return api.get(`/sessions/${id}/replies`) as Promise<ReplyItem[]>
  },
  updateTab(id: number, tab: string) {
    return api.put(`/sessions/${id}/tab`, null, { params: { tab } })
  },
  updateStatus(id: number, status: string) {
    return api.put(`/sessions/${id}/status`, null, { params: { status } })
  },
  markRisk(id: number) {
    return api.put(`/sessions/${id}/risk`)
  },
  clearMessages(id: number) {
    return api.delete(`/sessions/${id}/messages`)
  },
  deleteSession(id: number) {
    return api.delete(`/sessions/${id}`)
  },
  /** 一键清除所有客户信息（会话/消息/订单/话术/物流） */
  clearAll() {
    return api.delete('/sessions/all') as Promise<{
      ok: boolean; message: string;
      deleted: { sessions: number; messages: number; orders: number; replies: number; logistics_tracks: number }
    }>
  },
}

export const aiAPI = {
  analyze(data: { session_id: number; latest_message: string }) {
    return api.post('/ai/analyze', data) as Promise<{
      intent: string; emotion: string; emotion_class: string; risk: string; risk_class: string;
      segment: string; score: number; value_desc: string; suggested_replies: string[]
    }>
  },
  getSuggestions(sessionId: number) {
    return api.get(`/ai/suggestions/${sessionId}`) as Promise<{ id: number; text: string }[]>
  },
  regenerateReplies(sessionId: number) {
    return api.post(`/ai/regenerate-replies/${sessionId}`) as Promise<{ replies: { id: number; text: string }[] }>
  },
  /** 第一步：模拟客户发消息（带对话流和等待检测） */
  simulateCustomer(sessionId: number, intent?: string) {
    return api.post('/ai/simulate-customer', null, { params: { session_id: sessionId, intent } }) as Promise<{
      status: 'ok' | 'waiting'
      message: MessageItem | null
      chosen_intent: string | null
      is_urge?: boolean
    }>
  },
  /** 第二步：AI分析最新客户消息，返回分析结果和自动回答 */
  analyzeCustomer(sessionId: number) {
    return api.post('/ai/analyze-customer', null, { params: { session_id: sessionId } }) as Promise<{
      auto_answer: MessageItem | null
      analysis: {
        intent: string; emotion: string; emotion_class: string; risk: string; risk_class: string;
        segment: string; score: number; score_color: string; value_desc: string
        can_auto_answer: boolean; auto_answer: string; suggested_replies: string[]; analysis_note: string
      }
    }>
  },
}

export const platformAPI = {
  getOrders(platform: string, orderNo?: string) {
    return api.get(`/platforms/${platform}/orders`, { params: { order_no: orderNo } }) as Promise<any[]>
  },
  getProducts(platform: string, keyword?: string) {
    return api.get(`/platforms/${platform}/products`, { params: { keyword } }) as Promise<any[]>
  },
  getSummary() {
    return api.get('/platforms/summary') as Promise<any>
  },
}

export const logisticsAPI = {
  getBySession(sessionId: number) {
    return api.get(`/logistics/session/${sessionId}`) as Promise<{ orders: LogisticsOrderItem[] }>
  },
  urge(trackingNo: string) {
    return api.post(`/logistics/urge/${trackingNo}`) as Promise<{ success: boolean; message: string; tracking_no: string }>
  },
}