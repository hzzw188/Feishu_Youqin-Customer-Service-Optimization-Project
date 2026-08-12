import api from './index'

/** 商品 */
export interface Product {
  id: number
  name: string
  sku: string
  price: string | number
  stock: number
  category: string
  material: string
  size: string
  spec: string
  scenes: string
  desc: string
  questions?: string[]
}

/** 客户历史订单 */
export interface CustomerOrder {
  id: number
  order_no: string
  name: string
  price: string | number
  status: string
  logistics: string
  platform: string
}

/** 聊天消息 */
export interface CustomerMessage {
  id: number
  dir: 'left' | 'right' | 'center'
  text: string
  type: string
  has_product?: boolean
  created_at: string
}

/** 历史会话记录 */
export interface HistorySession {
  session_id: number
  type: string
  preview: string
  time: string
  message_count: number
  recent_messages: { dir: string; text: string; time: string }[]
  questions: string[]
}

/** 创建会话返回 */
export interface StartSessionResp {
  session_id: number
  welcome_message: CustomerMessage
}

/** 发送消息返回 */
export interface SendResp {
  customer_message: CustomerMessage
  ai_reply: CustomerMessage
  analysis: {
    intent: string
    emotion: string
    can_auto_answer: boolean
  }
}

/** 营收贡献（基于客户价值视角测算模型） */
export interface Contribution {
  gmv: number
  base_convert_prob: number
  base_refund_prob: number
  conv: number
  retain: number
  total: number
}

/** 下单/已解决 标记返回 */
export interface ActionResp {
  already_deal?: boolean
  already_resolved?: boolean
  message: CustomerMessage | null
  session?: { deal_amount?: number; resolved?: number; contrib_total?: number }
  contribution: Contribution
}

export const customerAPI = {
  /** 获取商品列表 */
  getProducts() {
    return api.get('/customer/products') as Promise<Product[]>
  },
  /** 获取客户历史订单 */
  getOrders(params: { name: string; platform: string }) {
    return api.get('/customer/orders', { params }) as Promise<CustomerOrder[]>
  },
  /** 获取客户历史会话 + 6条关联提问 */
  getHistory(params: { name: string; platform: string }) {
    return api.get('/customer/history', { params }) as Promise<HistorySession[]>
  },
  /** 创建会话 */
  start(data: {
    name: string
    platform: string
    type: 'pre-sale' | 'after-sale'
    product_id?: number
    order_info?: {
      order_no: string
      name: string
      price: string | number
      status: string
    }
  }) {
    return api.post('/customer/start', data) as Promise<StartSessionResp>
  },
  /** 获取消息列表 */
  getMessages(sessionId: number) {
    return api.get(`/customer/${sessionId}/messages`) as Promise<CustomerMessage[]>
  },
  /** 客户发送消息 */
  send(sessionId: number, data: { text: string }) {
    return api.post(`/customer/${sessionId}/send`, data) as Promise<SendResp>
  },
  /** 售前：客户下单（标记成交，计算客服转化贡献） */
  placeOrder(sessionId: number) {
    return api.post(`/customer/${sessionId}/place-order`) as Promise<ActionResp>
  },
  /** 售后：问题已解决（标记挽回，计算退款挽回贡献） */
  resolveIssue(sessionId: number) {
    return api.post(`/customer/${sessionId}/resolve`) as Promise<ActionResp>
  },
}
