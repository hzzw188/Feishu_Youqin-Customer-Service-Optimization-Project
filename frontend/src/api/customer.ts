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
}
