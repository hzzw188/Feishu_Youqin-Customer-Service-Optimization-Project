<template>
  <div class="server-page">
    <div class="server-shell">
      <!-- ============ 阶段1：主页（三个框 + 信息填写） ============ -->
      <section v-if="stage === 'home'" class="stage stage-home">
        <header class="home-header">
          <div class="brand-row">
            <span class="brand-name">优勤智服</span>
            <span class="brand-sub">智能客服 · 7×24h</span>
          </div>
          <p class="brand-desc">由 AI 智能助手为您提供即时服务</p>
        </header>

        <div class="home-body">
          <!-- 三个选择框 -->
          <div class="choice-grid">
            <div
              :class="['choice-card', { active: formType === 'pre-sale' }]"
              @click="enterChoice('pre-sale')"
            >
              <div class="choice-title">售前咨询</div>
              <div class="choice-desc">选购商品 / 参数咨询 / 推荐指南</div>
            </div>

            <div
              :class="['choice-card', { active: formType === 'after-sale' }]"
              @click="enterChoice('after-sale')"
            >
              <div class="choice-title">售后服务</div>
              <div class="choice-desc">订单问题 / 退换货 / 物流查询</div>
            </div>

            <div class="choice-card choice-history" @click="enterHistory">
              <div class="choice-title">历史会话</div>
              <div class="choice-desc">
                {{ history.length ? `共 ${history.length} 条记录` : '查看历史咨询' }}
              </div>
            </div>
          </div>

          <!-- 名称输入 -->
          <div class="form-block" v-if="formType">
            <label class="form-label">您的称呼</label>
            <el-input
              v-model="customerName"
              placeholder="如：张小姐"
              size="large"
              clearable
              maxlength="20"
            />
          </div>

          <!-- 平台选择 -->
          <div class="form-block" v-if="formType">
            <label class="form-label">购物平台</label>
            <div class="platform-grid">
              <button
                v-for="p in platforms"
                :key="p"
                type="button"
                :class="['platform-chip', { active: platform === p }]"
                @click="platform = p"
              >{{ p }}</button>
            </div>
          </div>

          <!-- 历史会话列表（点击历史框或填写名称+平台后显示） -->
          <div class="form-block" v-if="customerName.trim() && platform">
            <label class="form-label">
              历史聊天记录
              <span class="form-hint" v-if="history.length">（{{ history.length }}条）</span>
              <span class="form-hint" v-else-if="!customerName.trim() || !platform">（请先填写称呼并选择平台）</span>
            </label>
            <div v-loading="loadingHistory" class="history-wrap">
              <div v-if="history.length === 0 && !loadingHistory" class="empty-tip">
                暂无历史记录
              </div>
              <div
                v-for="h in history"
                :key="h.session_id"
                class="history-card"
              >
                <div class="history-head" @click="toggleHistory(h.session_id)">
                  <span :class="['history-tag', h.type === '售前' ? 'tag-pre' : 'tag-after']">
                    {{ h.type }}
                  </span>
                  <span class="history-preview">{{ h.preview || '暂无消息' }}</span>
                  <span class="history-time">{{ h.time }}</span>
                  <el-icon class="history-arrow" :class="{ expanded: expandedHistory === h.session_id }">
                    <ArrowDown />
                  </el-icon>
                </div>

                <div v-if="expandedHistory === h.session_id" class="history-detail">
                  <div class="recent-msgs">
                    <div
                      v-for="(m, i) in h.recent_messages"
                      :key="i"
                      :class="['recent-msg', m.dir === 'right' ? 'msg-customer' : 'msg-ai']"
                    >
                      <span class="recent-msg-role">{{ m.dir === 'right' ? '我' : 'AI' }}</span>
                      <span class="recent-msg-text">{{ m.text }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 售前：商品列表 -->
          <div v-if="formType === 'pre-sale' && customerName.trim() && platform" class="form-block">
            <label class="form-label">
              选择咨询的商品
              <span class="form-hint">（可选）</span>
            </label>
            <div v-loading="loadingList" class="list-wrap">
              <div v-if="products.length === 0 && !loadingList" class="empty-tip">暂无商品</div>
              <div
                v-for="p in products"
                :key="p.id"
                :class="['item-card', { selected: selectedProduct?.id === p.id }]"
                @click="selectedProduct = selectedProduct?.id === p.id ? null : p"
              >
                <div class="item-card-main">
                  <div class="item-name">{{ p.name }}</div>
                  <div class="item-meta">
                    <span v-if="p.spec">{{ p.spec }}</span>
                    <span v-if="p.material"> · {{ p.material }}</span>
                  </div>
                </div>
                <div class="item-card-right">
                  <div class="item-price">{{ formatPrice(p.price) }}</div>
                  <div class="item-check">
                    <el-icon v-if="selectedProduct?.id === p.id" :size="18"><Check /></el-icon>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 售后：订单列表 -->
          <div v-else-if="formType === 'after-sale' && customerName.trim() && platform" class="form-block">
            <label class="form-label">
              选择相关订单
              <span class="form-hint">（可选）</span>
            </label>
            <div v-loading="loadingList" class="list-wrap">
              <div v-if="orders.length === 0 && !loadingList" class="empty-tip">
                未找到该客户在此平台的订单
              </div>
              <div
                v-for="o in orders"
                :key="o.id"
                :class="['item-card', { selected: selectedOrder?.id === o.id }]"
                @click="selectedOrder = selectedOrder?.id === o.id ? null : o"
              >
                <div class="item-card-main">
                  <div class="item-name">{{ o.name }}</div>
                  <div class="item-meta">
                    <span>单号 {{ o.order_no }}</span>
                    <span> · {{ o.status }}</span>
                  </div>
                </div>
                <div class="item-card-right">
                  <div class="item-price">{{ formatPrice(o.price) }}</div>
                  <div class="item-check">
                    <el-icon v-if="selectedOrder?.id === o.id" :size="18"><Check /></el-icon>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <footer class="home-footer" v-if="formType">
          <el-button
            type="primary"
            size="large"
            :icon="ChatDotRound"
            class="action-btn"
            :loading="starting"
            :disabled="!canStart"
            @click="startChat"
          >开始咨询</el-button>
        </footer>
      </section>

      <!-- ============ 阶段2：历史会话列表页 ============ -->
      <section v-else-if="stage === 'history'" class="stage stage-history">
        <header class="chat-header">
          <span class="back-btn" @click="stage = 'home'">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </span>
          <div class="chat-header-info">
            <div class="chat-header-name">历史会话</div>
            <div class="chat-header-sub">
              {{ customerName || '请先输入称呼' }}{{ platform ? ' · ' + platform : '' }}
            </div>
          </div>
        </header>

        <!-- 历史会话查询：未输入称呼/平台时提示 -->
        <div class="history-query-bar" v-if="!customerName.trim() || !platform">
          <p class="query-tip">请先输入您的称呼并选择购物平台，才能查看历史会话</p>
          <el-button type="primary" @click="stage = 'home'">去填写</el-button>
        </div>

        <div v-else class="history-list-body" v-loading="loadingHistory">
          <div v-if="history.length === 0 && !loadingHistory" class="empty-tip">
            暂无历史记录
          </div>
          <div
            v-for="h in history"
            :key="h.session_id"
            class="history-card"
          >
            <div class="history-head" @click="toggleHistory(h.session_id)">
              <span :class="['history-tag', h.type === '售前' ? 'tag-pre' : 'tag-after']">
                {{ h.type }}
              </span>
              <span class="history-preview">{{ h.preview || '暂无消息' }}</span>
              <span class="history-time">{{ h.time }}</span>
              <el-icon class="history-arrow" :class="{ expanded: expandedHistory === h.session_id }">
                <ArrowDown />
              </el-icon>
            </div>

            <div v-if="expandedHistory === h.session_id" class="history-detail">
              <div class="recent-msgs">
                <div
                  v-for="(m, i) in h.recent_messages"
                  :key="i"
                  :class="['recent-msg', m.dir === 'right' ? 'msg-customer' : 'msg-ai']"
                >
                  <span class="recent-msg-role">{{ m.dir === 'right' ? '我' : 'AI' }}</span>
                  <span class="recent-msg-text">{{ m.text }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ============ 阶段3：聊天页 ============ -->
      <section v-else class="stage stage-chat">
        <header class="chat-header">
          <span class="back-btn" @click="backToHome">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </span>
          <div class="chat-header-info">
            <div class="chat-header-name">{{ customerName || '客户' }}</div>
            <div class="chat-header-sub">
              {{ platform }} · {{ formType === 'pre-sale' ? '售前' : '售后' }}
            </div>
          </div>
        </header>

        <div v-if="selectedProduct || selectedOrder" class="context-bar">
          <template v-if="selectedProduct">
            <el-icon :size="16"><Goods /></el-icon>
            <span class="ctx-name">{{ selectedProduct.name }}</span>
            <span class="ctx-price">{{ formatPrice(selectedProduct.price) }}</span>
          </template>
          <template v-else-if="selectedOrder">
            <el-icon :size="16"><Van /></el-icon>
            <span class="ctx-name">{{ selectedOrder.name }}</span>
            <span class="ctx-sub">{{ selectedOrder.order_no }}</span>
          </template>
        </div>

        <div ref="msgListRef" class="msg-list">
          <div
            v-for="m in messages"
            :key="m.id"
            :class="['msg-row', rowClass(m)]"
          >
            <div v-if="m.dir === 'center'" class="msg-system">{{ m.text }}</div>
            <template v-else>
              <div v-if="m.dir === 'left'" class="msg-avatar">
                <el-icon :size="18"><ChatDotRound /></el-icon>
              </div>
              <div :class="['msg-bubble', m.dir === 'right' ? 'msg-bubble-right' : 'msg-bubble-left']">
                {{ m.text }}
              </div>
            </template>
          </div>

          <!-- AI 思考中：三点动画 -->
          <div v-if="thinking" class="msg-row msg-row-left">
            <div class="msg-avatar">
              <el-icon :size="18"><ChatDotRound /></el-icon>
            </div>
            <div class="msg-bubble msg-bubble-left thinking-bubble">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>

        <!-- 输入框上方：6条关联提问复选框 -->
        <div class="quick-questions" v-if="currentQuestions.length">
          <div class="qq-title">关联提问（勾选后自动填入输入框）</div>
          <div class="qq-list">
            <label
              v-for="(q, qi) in currentQuestions"
              :key="qi"
              :class="['qq-item', { checked: checkedQuestion === q }]"
            >
              <el-checkbox
                :model-value="checkedQuestion === q"
                @change="checkQuestion(q)"
              />
              <span class="qq-text">{{ q }}</span>
            </label>
          </div>
        </div>

        <!-- 售前/售后结果操作条：下单 / 已解决（驱动营收贡献测算） -->
        <div v-if="sessionId !== null && formType" class="result-action-bar">
          <template v-if="formType === 'pre-sale'">
            <el-button
              type="success"
              round
              :icon="ShoppingCart"
              :loading="actionLoading"
              :disabled="dealDone"
              @click="placeOrder"
            >{{ dealDone ? '已下单 ✓' : '🛒 我下单了' }}</el-button>
            <span v-if="dealDone && lastConv > 0" class="result-tip">
              客服转化贡献 +¥{{ lastConv.toFixed(1) }}
            </span>
          </template>
          <template v-else>
            <el-button
              type="success"
              round
              :icon="CircleCheck"
              :loading="actionLoading"
              :disabled="resolvedDone"
              @click="resolveIssue"
            >{{ resolvedDone ? '已解决 ✓' : '✅ 问题已解决' }}</el-button>
            <span v-if="resolvedDone && lastRetain > 0" class="result-tip">
              客服挽回贡献 +¥{{ lastRetain.toFixed(1) }}
            </span>
          </template>
        </div>

        <footer class="input-area">
          <el-input
            v-model="inputText"
            placeholder="请输入您的问题..."
            :disabled="sending"
            @keydown.enter.prevent="sendMessage"
          />
          <el-button
            type="primary"
            :icon="Promotion"
            :loading="sending"
            :disabled="!inputText.trim()"
            @click="sendMessage"
          >发送</el-button>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  ArrowLeft,
  ArrowDown,
  Check,
  Goods,
  Van,
  Promotion,
  ShoppingCart,
  CircleCheck,
} from '@element-plus/icons-vue'
import {
  customerAPI,
  type Product,
  type CustomerOrder,
  type CustomerMessage,
  type HistorySession,
} from '../api/customer'

type Stage = 'home' | 'history' | 'chat'
type FormType = 'pre-sale' | 'after-sale' | null

const stage = ref<Stage>('home')
const formType = ref<FormType>(null)

const customerName = ref('')
const platform = ref('')
const platforms = [
  '淘宝', '天猫', '京东', '拼多多', '苏宁易购',
  '唯品会', '抖音', '快手', '小红书', '微信',
]

const products = ref<Product[]>([])
const orders = ref<CustomerOrder[]>([])
const selectedProduct = ref<Product | null>(null)
const selectedOrder = ref<CustomerOrder | null>(null)

const loadingList = ref(false)
const starting = ref(false)

// ===== 历史记录 =====
const history = ref<HistorySession[]>([])
const loadingHistory = ref(false)
const expandedHistory = ref<number | null>(null)

// ===== 聊天相关状态 =====
const sessionId = ref<number | null>(null)
const messages = ref<CustomerMessage[]>([])
const knownIds = new Set<number>()
const inputText = ref('')
const sending = ref(false)
const thinking = ref(false)
const msgListRef = ref<HTMLElement | null>(null)

// ===== 营收贡献操作（售前下单 / 售后已解决） =====
const actionLoading = ref(false)
const dealDone = ref(false)
const resolvedDone = ref(false)
const lastConv = ref(0)
const lastRetain = ref(0)
let pollTimer: number | null = null
let orderDebounce: number | null = null
let historyDebounce: number | null = null

// ===== 关联提问（聊天页输入框上方） =====
const PRE_SALE_QUESTIONS = [
  '这个商品多少钱？有优惠活动吗？',
  '商品有现货吗？什么时候能发货？',
  '支持七天无理由退换货吗？',
  '发什么快递？运费多少？',
  '材质是什么？尺寸规格多大？',
  '质量有保证吗？有售后质保吗？',
]
const AFTER_SALE_QUESTIONS = [
  '我的订单什么时候能送到？',
  '物流到哪了？能帮忙催一下吗？',
  '商品有质量问题，想申请退换货',
  '申请退款，大概多久能到账？',
  '能修改收货地址吗？',
  '需要开发票，怎么操作？',
]
const currentQuestions = computed(() => {
  // 如果选中了商品且有商品专属提问，用商品专属提问
  if (selectedProduct.value?.questions?.length) {
    return selectedProduct.value.questions
  }
  return formType.value === 'pre-sale' ? PRE_SALE_QUESTIONS : AFTER_SALE_QUESTIONS
})
const checkedQuestion = ref<string>('')

/** 勾选关联提问：填入输入框（单选切换） */
function checkQuestion(q: string) {
  if (checkedQuestion.value === q) {
    checkedQuestion.value = ''
    inputText.value = ''
  } else {
    checkedQuestion.value = q
    inputText.value = q
  }
}

const canStart = computed(
  () => !!customerName.value.trim() && !!platform.value,
)

/** 点击售前/售后框 */
function enterChoice(t: 'pre-sale' | 'after-sale') {
  formType.value = t
  selectedProduct.value = null
  selectedOrder.value = null
  if (t === 'pre-sale') {
    loadProducts()
  }
}

/** 点击历史会话框，进入历史会话列表页 */
function enterHistory() {
  stage.value = 'history'
  if (customerName.value.trim() && platform.value) {
    loadHistory()
  }
}

async function loadProducts() {
  loadingList.value = true
  try {
    products.value = await customerAPI.getProducts()
  } catch {
    ElMessage.error('商品加载失败')
    products.value = []
  } finally {
    loadingList.value = false
  }
}

async function loadOrders() {
  if (!customerName.value.trim() || !platform.value) return
  loadingList.value = true
  try {
    orders.value = await customerAPI.getOrders({
      name: customerName.value.trim(),
      platform: platform.value,
    })
  } catch {
    orders.value = []
  } finally {
    loadingList.value = false
  }
}

async function loadHistory() {
  if (!customerName.value.trim() || !platform.value) {
    history.value = []
    return
  }
  loadingHistory.value = true
  try {
    history.value = await customerAPI.getHistory({
      name: customerName.value.trim(),
      platform: platform.value,
    })
  } catch {
    history.value = []
  } finally {
    loadingHistory.value = false
  }
}

function toggleHistory(sid: number) {
  expandedHistory.value = expandedHistory.value === sid ? null : sid
}

// 填写称呼并选择平台后自动查询订单和历史记录（防抖）
watch([customerName, platform], () => {
  if (stage.value !== 'home') return
  if (!customerName.value.trim() || !platform.value) return
  if (orderDebounce !== null) clearTimeout(orderDebounce)
  orderDebounce = window.setTimeout(() => {
    if (formType.value === 'after-sale') loadOrders()
  }, 400)
  if (historyDebounce !== null) clearTimeout(historyDebounce)
  historyDebounce = window.setTimeout(() => {
    loadHistory()
  }, 400)
})

onBeforeUnmount(() => {
  stopPolling()
  if (orderDebounce !== null) clearTimeout(orderDebounce)
  if (historyDebounce !== null) clearTimeout(historyDebounce)
})

async function startChat() {
  if (!canStart.value || !formType.value) return
  starting.value = true
  try {
    const payload: {
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
    } = {
      name: customerName.value.trim(),
      platform: platform.value,
      type: formType.value,
    }
    if (formType.value === 'pre-sale' && selectedProduct.value) {
      payload.product_id = selectedProduct.value.id
    }
    if (formType.value === 'after-sale' && selectedOrder.value) {
      payload.order_info = {
        order_no: selectedOrder.value.order_no,
        name: selectedOrder.value.name,
        price: selectedOrder.value.price,
        status: selectedOrder.value.status,
      }
    }

    const resp = await customerAPI.start(payload)
    sessionId.value = resp.session_id
    messages.value = []
    knownIds.clear()
    // 重置营收贡献操作状态（每次新会话干净开始）
    dealDone.value = false
    resolvedDone.value = false
    lastConv.value = 0
    lastRetain.value = 0
    if (resp.welcome_message) {
      messages.value.push(resp.welcome_message)
      knownIds.add(resp.welcome_message.id)
    }
    stage.value = 'chat'
    await nextTick()
    scrollToBottom()
    startPolling()
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '连接失败，请重试'
    ElMessage.error(detail)
  } finally {
    starting.value = false
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || sending.value || sessionId.value === null) return

  // 快照当前 sessionId，防止异步回调中 sessionId 被切换
  const currentSid = sessionId.value

  // ===== 乐观更新：立即本地追加自己的消息气泡，不等后端响应 =====
  const tempId = -Date.now()
  const tempMsg: CustomerMessage = {
    id: tempId,
    dir: 'right',
    text,
    type: 'user',
    created_at: new Date().toISOString(),
  }
  messages.value.push(tempMsg)

  inputText.value = ''
  checkedQuestion.value = ''
  sending.value = true
  thinking.value = true
  await nextTick()
  scrollToBottom()
  try {
    const resp = await customerAPI.send(currentSid, { text })
    // 跨会话检测：如果响应返回时用户已切换到其他会话，丢弃结果
    if (sessionId.value !== currentSid) return
    // 用后端返回的真实消息替换本地临时气泡
    if (resp.customer_message) {
      replaceTempMessage(tempId, resp.customer_message)
    } else {
      removeTempMessage(tempId)
    }
    await nextTick()
    scrollToBottom()
    await delay(500)
    // 再次检查，防止 delay 期间切换了会话
    if (sessionId.value !== currentSid) return
    thinking.value = false
    if (resp.ai_reply && !knownIds.has(resp.ai_reply.id)) {
      messages.value.push(resp.ai_reply)
      knownIds.add(resp.ai_reply.id)
    }
    await nextTick()
    scrollToBottom()
  } catch (e: any) {
    if (sessionId.value !== currentSid) return
    thinking.value = false
    removeTempMessage(tempId)
    const detail = e?.response?.data?.detail || e?.message || '发送失败'
    ElMessage.error(detail)
    inputText.value = text
  } finally {
    if (sessionId.value === currentSid) {
      sending.value = false
    }
  }
}

/** 用后端真实消息替换本地临时气泡 */
function replaceTempMessage(tempId: number, real: CustomerMessage) {
  const idx = messages.value.findIndex(m => m.id === tempId)
  if (idx !== -1) {
    messages.value[idx] = real
  } else if (!knownIds.has(real.id)) {
    messages.value.push(real)
  }
  knownIds.add(real.id)
}

/** 移除指定的本地临时气泡（发送失败时） */
function removeTempMessage(tempId: number) {
  messages.value = messages.value.filter(m => m.id !== tempId)
}

/** 移除所有本地临时气泡（id < 0，轮询拉到真实消息前先清理） */
function removeTempMessages() {
  if (messages.value.some(m => m.id < 0)) {
    messages.value = messages.value.filter(m => m.id >= 0)
  }
}

/** 追加一条后端消息（去重）并滚动到底部 */
function appendMessage(m: CustomerMessage) {
  if (!knownIds.has(m.id)) {
    messages.value.push(m)
    knownIds.add(m.id)
  }
  nextTick().then(scrollToBottom)
}

/** 售前：客户下单 → 标记成交并计算客服转化贡献 Vconv */
async function placeOrder() {
  if (!sessionId.value || dealDone.value || actionLoading.value) return
  actionLoading.value = true
  try {
    const resp = await customerAPI.placeOrder(sessionId.value)
    if (resp.already_deal) {
      dealDone.value = true
      lastConv.value = resp.contribution.conv
      ElMessage.info(`该会话已下单，客服转化贡献 +¥${resp.contribution.conv.toFixed(1)}`)
      return
    }
    if (resp.message) appendMessage(resp.message)
    dealDone.value = true
    lastConv.value = resp.contribution.conv
    ElMessage.success(`下单成功！客服转化贡献 +¥${resp.contribution.conv.toFixed(1)}`)
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '下单失败'
    ElMessage.error(detail)
  } finally {
    actionLoading.value = false
  }
}

/** 售后：问题已解决 → 标记挽回并计算退款挽回贡献 Vretain */
async function resolveIssue() {
  if (!sessionId.value || resolvedDone.value || actionLoading.value) return
  actionLoading.value = true
  try {
    const resp = await customerAPI.resolveIssue(sessionId.value)
    if (resp.already_resolved) {
      resolvedDone.value = true
      lastRetain.value = resp.contribution.retain
      ElMessage.info(`该会话已解决，客服挽回贡献 +¥${resp.contribution.retain.toFixed(1)}`)
      return
    }
    if (resp.message) appendMessage(resp.message)
    resolvedDone.value = true
    lastRetain.value = resp.contribution.retain
    ElMessage.success(`售后已解决！客服挽回贡献 +¥${resp.contribution.retain.toFixed(1)}`)
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '提交失败'
    ElMessage.error(detail)
  } finally {
    actionLoading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(pollMessages, 3000)
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollMessages() {
  if (sessionId.value === null) return
  const currentSid = sessionId.value
  try {
    const list = await customerAPI.getMessages(currentSid)
    // 跨会话检测：如果轮询返回时已切换到其他会话，丢弃结果
    if (sessionId.value !== currentSid) return
    if (list.some(m => !knownIds.has(m.id))) {
      // 后端已有新消息：先移除本地临时气泡，避免与真实消息重复
      removeTempMessages()
    }
    let appended = false
    for (const m of list) {
      if (!knownIds.has(m.id)) {
        messages.value.push(m)
        knownIds.add(m.id)
        appended = true
      }
    }
    if (appended) {
      await nextTick()
      scrollToBottom()
    }
  } catch {
    // 轮询失败静默处理
  }
}

function rowClass(m: CustomerMessage) {
  if (m.dir === 'center') return 'msg-row-center'
  if (m.dir === 'right') return 'msg-row-right'
  return 'msg-row-left'
}

function scrollToBottom() {
  const el = msgListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function backToHome() {
  stopPolling()
  stage.value = 'home'
  sessionId.value = null
  messages.value = []
  knownIds.clear()
  thinking.value = false
  sending.value = false
  inputText.value = ''
  checkedQuestion.value = ''
  if (customerName.value.trim() && platform.value) {
    loadHistory()
  }
}

function delay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

/** 价格格式化：数据可能带¥前缀或为数字，统一输出 ¥xx.xx */
function formatPrice(price: string | number): string {
  if (typeof price === 'number') return `¥${price}`
  const s = String(price).trim()
  if (s.startsWith('¥')) return s
  return `¥${s}`
}
</script>

<style scoped>
.server-page {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  background: #f0f2f5;
  overflow: hidden;
}

.server-shell {
  width: 100%;
  max-width: 480px;
  height: 100vh;
  background: #fff;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: 0 0 40px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.stage {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ===== 主页头部 ===== */
.home-header {
  padding: 24px 20px 18px;
  background: #2563EB;
  color: #fff;
}
.brand-row { display: flex; align-items: baseline; gap: 10px; }
.brand-name { font-size: 22px; font-weight: 700; }
.brand-sub { font-size: 12px; opacity: 0.85; }
.brand-desc { font-size: 13px; opacity: 0.85; margin-top: 6px; }

.home-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 三个选择框 ===== */
.choice-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
.choice-card {
  padding: 18px 16px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e5e7eb;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: border-color 0.2s, background 0.2s, transform 0.15s, box-shadow 0.2s;
}
.choice-card:hover {
  border-color: #93c5fd;
  background: #f0f7ff;
}
.choice-card:active { transform: scale(0.98); }
/* 售前/售后选中高亮 */
.choice-card.active {
  border-color: #2563EB;
  background: #eff6ff;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
}
.choice-card.active .choice-title { color: #2563EB; }
/* 历史会话框特殊高亮 */
.choice-history:hover {
  border-color: #c4b5fd;
  background: #f5f3ff;
}

.choice-title { font-size: 16px; font-weight: 600; color: #111827; }
.choice-desc { font-size: 12px; color: #6b7280; margin-top: 2px; }

/* ===== 历史会话列表页 ===== */
.stage-history { background: #fff; }
.history-query-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 20px;
}
.query-tip { font-size: 14px; color: #6b7280; text-align: center; line-height: 1.6; }
.history-list-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-block { display: flex; flex-direction: column; }
.form-label {
  font-size: 13px; font-weight: 600; color: #374151;
  margin-bottom: 8px; display: flex; align-items: center; gap: 4px;
}
.form-hint { font-size: 11px; color: #9ca3af; font-weight: 400; }

.platform-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.platform-chip {
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #fff;
  font-size: 13px; color: #6b7280;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.platform-chip:hover { border-color: #93c5fd; color: #2563EB; }
.platform-chip:active { transform: scale(0.96); }
.platform-chip.active {
  background: #2563EB; color: #fff; border-color: #2563EB;
}

/* ===== 历史记录列表 ===== */
.history-wrap { display: flex; flex-direction: column; gap: 8px; }
.history-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}
.history-head {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.15s;
}
.history-head:hover { background: #f9fafb; }
.history-tag {
  font-size: 11px; padding: 2px 8px; border-radius: 4px;
  font-weight: 500; flex-shrink: 0;
}
.tag-pre { background: #dbeafe; color: #2563EB; }
.tag-after { background: #d1fae5; color: #059669; }
.history-preview {
  flex: 1; min-width: 0;
  font-size: 13px; color: #374151;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.history-time { font-size: 11px; color: #9ca3af; flex-shrink: 0; }
.history-arrow {
  color: #9ca3af; transition: transform 0.2s; flex-shrink: 0;
}
.history-arrow.expanded { transform: rotate(180deg); }

.history-detail {
  border-top: 1px solid #f3f4f6;
  padding: 10px 12px;
  background: #fafbfc;
}
.recent-msgs { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.recent-msg { display: flex; gap: 6px; font-size: 12px; }
.recent-msg-role {
  flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 600;
}
.msg-customer .recent-msg-role { background: #2563EB; color: #fff; }
.msg-ai .recent-msg-role { background: #e5e7eb; color: #374151; }
.recent-msg-text { color: #4b5563; line-height: 1.5; }

/* ===== 商品/订单卡片 ===== */
.list-wrap { display: flex; flex-direction: column; gap: 8px; min-height: 60px; }
.item-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.item-card:hover { border-color: #93c5fd; background: #f0f7ff; }
.item-card:active { transform: scale(0.99); }
.item-card.selected {
  border-color: #2563EB;
  background: #eff6ff;
}
.item-card-main { flex: 1; min-width: 0; }
.item-name {
  font-size: 14px; font-weight: 500; color: #111827;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.item-meta { font-size: 12px; color: #9ca3af; margin-top: 3px; }
.item-card-right {
  display: flex; flex-direction: column; align-items: flex-end; gap: 4px;
  margin-left: 10px; flex-shrink: 0;
}
.item-price { font-size: 15px; font-weight: 600; color: #2563EB; }
.item-check { width: 20px; height: 20px; color: #2563EB; }
.empty-tip { font-size: 13px; color: #9ca3af; padding: 18px 0; text-align: center; }

.home-footer {
  padding: 12px 18px 18px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.selected-count {
  font-size: 12px; color: #059669; text-align: center;
  font-weight: 500;
}
.action-btn { width: 100%; }

/* ===== 聊天页 ===== */
.chat-header {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px;
  background: #2563EB;
  color: #fff;
}
.back-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
  cursor: pointer;
  transition: background 0.15s;
}
.back-btn:hover { background: rgba(255, 255, 255, 0.32); }
.chat-header-info { flex: 1; min-width: 0; }
.chat-header-name { font-size: 15px; font-weight: 600; }
.chat-header-sub { font-size: 11px; opacity: 0.85; margin-top: 1px; }

.context-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px;
  background: #eff6ff;
  border-bottom: 1px solid #dbeafe;
  font-size: 12px; color: #2563EB;
}
.ctx-name {
  font-weight: 500; flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ctx-price { font-weight: 600; }
.ctx-sub { color: #6b7280; font-size: 11px; }

.msg-list {
  flex: 1; overflow-y: auto;
  padding: 16px 14px;
  display: flex; flex-direction: column; gap: 12px;
  background: #f5f7fa;
}
.msg-row { display: flex; gap: 8px; align-items: flex-start; }
.msg-row-left { justify-content: flex-start; }
.msg-row-right { justify-content: flex-end; }
.msg-row-center { justify-content: center; }

.msg-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: #2563EB;
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.msg-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px; line-height: 1.6;
  word-break: break-word;
}
.msg-bubble-left {
  background: #fff; color: #111827;
  border: 1px solid #e5e7eb;
  border-top-left-radius: 4px;
}
.msg-bubble-right {
  background: #2563EB; color: #fff;
  border-top-right-radius: 4px;
}
.msg-system {
  font-size: 12px; color: #9ca3af;
  padding: 2px 10px; text-align: center;
}

/* AI 思考中三点动画 */
.thinking-bubble { padding: 14px 16px; display: inline-flex; gap: 5px; align-items: center; }
.thinking-bubble .dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #9ca3af;
  animation: dot-bounce 1.2s infinite ease-in-out;
}
.thinking-bubble .dot:nth-child(2) { animation-delay: 0.15s; }
.thinking-bubble .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes dot-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* ===== 输入框上方：6条关联提问 ===== */
.quick-questions {
  border-top: 1px solid #eef2f7;
  background: #f8fafc;
  padding: 8px 12px;
  display: flex; flex-direction: column; gap: 6px;
}
.qq-title {
  font-size: 11px; font-weight: 600; color: #6b7280;
}
.qq-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 10px;
}
.qq-item {
  display: flex; align-items: flex-start; gap: 6px;
  padding: 5px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  border: 1px solid transparent;
}
.qq-item:hover { background: #eef4ff; }
.qq-item.checked {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.qq-text {
  font-size: 12px; color: #374151; line-height: 1.5;
}
.qq-item.checked .qq-text { color: #2563EB; font-weight: 500; }

/* ===== 售前/售后结果操作条（下单/已解决） ===== */
.result-action-bar {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px;
  border-top: 1px solid #eef2f7;
  background: linear-gradient(90deg, #f0fdf4 0%, #fff 60%);
}
.result-tip {
  font-size: 12px; font-weight: 600; color: #059669;
}

.input-area {
  display: flex; gap: 8px; align-items: center;
  padding: 10px 12px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}
.input-area .el-input { flex: 1; }
</style>
