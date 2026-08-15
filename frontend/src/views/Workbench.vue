<template>
  <div class="workbench-page">
    <!-- ========== 顶部导航栏（和设计稿一致：logo|标题 + tab + 消息/用户） ========== -->
    <header class="wb-header">
      <div class="wb-header-left">
        <span class="logo-text">YOUQIN</span>
        <span class="brand-divider"></span>
        <span class="brand-title">优勤智服 · AI客服利润引擎</span>
      </div>
      <div class="wb-header-right">
        <button :class="['wb-nav-btn', { active: $route.path === '/workbench' }]" @click="$router.push('/workbench')">
          <el-icon><Headset /></el-icon>客服工作台
        </button>
        <button :class="['wb-nav-btn', { active: $route.path === '/cockpit' }]" @click="$router.push('/cockpit')">
          <el-icon><Odometer /></el-icon>利润驾驶舱
        </button>
        <span class="wb-right-divider"></span>
        <span class="wb-icon-btn" title="消息"><el-icon :size="18"><Bell /></el-icon></span>
        <span class="wb-user-info">
          <el-icon :size="14"><UserFilled /></el-icon>
          <span>{{ authStore.user?.username || '客服001' }}</span>
        </span>
        <el-button text size="small" @click="handleLogout" class="wb-logout">退出</el-button>
      </div>
    </header>

    <!-- ========== 三栏主内容 ========== -->
    <div class="wb-body">
      <!-- 左栏：会话列表 -->
      <aside class="wb-left">
        <div class="wb-search">
          <el-input
            v-model="store.searchKeyword"
            placeholder="搜索用户 / 订单号 / 关键词"
            :prefix-icon="Search"
            clearable
            @input="store.fetchSessions()"
          />
          <el-button
            class="wb-init-btn"
            type="danger"
            :icon="Delete"
            @click="handleClearAll"
          >初始化</el-button>
        </div>
        <div class="wb-tabs">
          <div
            :class="['wb-tab', { active: store.currentTab === 'all' }]"
            @click="store.currentTab = 'all'; store.fetchSessions()"
          >
            全部 <em>{{ store.tabCounts.all }}</em>
          </div>
          <div
            :class="['wb-tab', { active: store.currentTab === 'ai' }]"
            @click="store.currentTab = 'ai'; store.fetchSessions()"
          >
            AI接待 <em>{{ store.tabCounts.ai }}</em>
          </div>
          <div
            :class="['wb-tab', { active: store.currentTab === 'wait' }]"
            @click="store.currentTab = 'wait'; store.fetchSessions()"
          >
            待接手 <em>{{ store.tabCounts.wait }}</em>
          </div>
        </div>
        <div class="wb-session-list" v-loading="store.loading">
          <div
            v-for="s in store.filteredSessions"
            :key="s.id"
            :class="['wb-session-item', { active: store.currentSession?.id === s.id }]"
            @click="selectSession(s.id)"
          >
            <div class="wb-session-row">
              <div class="wb-session-avatar" :style="{ background: avatarColor(s.user_name) }">
                {{ s.user_avatar }}
              </div>
              <div class="wb-session-info">
                <div class="wb-session-top">
                  <span class="wb-session-name">{{ s.user_name }}</span>
                  <span class="wb-session-time">{{ s.time }}</span>
                </div>
                <div class="wb-session-preview">{{ s.preview || '暂无消息' }}</div>
                <div class="wb-session-tags" v-if="s.tags && s.tags.length">
                  <span
                    v-for="(t, i) in s.tags"
                    :key="i"
                    :class="['wb-tag', getTagClass(t.cls)]"
                  >{{ t.text }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-if="store.filteredSessions.length === 0 && !store.loading" class="wb-empty">
            <div class="wb-empty-icon">📭</div>
            <p>没有匹配的会话</p>
            <p class="wb-empty-sub">试试切换标签或调整搜索关键词</p>
          </div>
        </div>
      </aside>

      <!-- 中栏：聊天区 -->
      <main class="wb-center">
        <template v-if="store.currentSession">
          <!-- 用户信息条 -->
          <div class="wb-chat-top">
            <div class="wb-chat-user">
              <div class="wb-chat-avatar" :style="{ background: avatarColor(store.currentSession.user_name) }">
                {{ store.currentSession.user_avatar }}
              </div>
              <div class="wb-chat-user-info">
                <div class="wb-chat-user-top">
                  <span class="wb-chat-username">{{ store.currentSession.user_name }}</span>
                  <span class="wb-tag tag-outline-danger">{{ store.currentSession.user_tag }}</span>
                  <span class="wb-chat-source">来自 {{ store.currentSession.source }}</span>
                </div>
                <div class="wb-chat-user-meta">{{ store.currentSession.user_desc }}</div>
              </div>
            </div>
            <div class="wb-chat-user-actions">
              <el-button size="small" class="wb-btn-outline" @click="showUserDetail = true">
                <el-icon><User /></el-icon>用户详情
              </el-button>
              <el-button size="small" type="primary" @click="handleSimulate" :loading="simLoading">
                <el-icon><ChatDotSquare /></el-icon>模拟客户消息
              </el-button>
              <el-button size="small" :type="store.simulating ? 'danger' : ''" class="wb-btn-outline" @click="store.toggleAutoSimulate()">
                <el-icon><VideoPlay /></el-icon>{{ store.simulating ? '停止自动模拟' : '自动模拟' }}
              </el-button>
              <el-button size="small" class="wb-btn-outline" @click="handleClearMessages" :disabled="store.messages.length === 0">
                <el-icon><Delete /></el-icon>清空记录
              </el-button>
            </div>
          </div>

          <!-- 消息流 -->
          <div class="wb-chat-messages chat-bg" ref="chatContainer">
            <template v-for="msg in renderedMessages" :key="msg.id">
              <div v-if="msg.type === 'system-msg'" class="wb-msg-system">{{ msg.text }}</div>

              <!-- 客户消息：左，白底 + 浅边 + 大圆角 -->
              <div v-else-if="msg.dir === 'right'" class="wb-msg-row wb-msg-row-left">
                <div class="wb-msg-avatar" :style="{ background: avatarColor(store.currentSession?.user_name || '客') }">
                  {{ store.currentSession?.user_avatar }}
                </div>
                <div class="wb-msg-bubble wb-msg-bubble-customer">
                  <div style="white-space: pre-wrap;">{{ msg.text }}</div>
                </div>
              </div>

              <!-- AI/客服消息：右，蓝色圆角气泡 -->
              <div v-else-if="msg.dir === 'left'" class="wb-msg-row wb-msg-row-right">
                <div class="wb-msg-bubble wb-msg-bubble-agent">
                  <div style="white-space: pre-wrap;">{{ msg.text }}</div>
                  <div v-if="msg.has_product" class="wb-product-card">
                    <div class="wb-product-tip">AI推荐商品</div>
                    <div class="wb-product-body">
                      <div class="wb-product-img"><el-icon :size="22"><Box /></el-icon></div>
                      <div class="wb-product-info">
                        <div class="wb-product-name">厨房挂钩免打孔挂杆</div>
                        <div class="wb-product-price">¥ 29.9</div>
                      </div>
                      <el-button size="small" class="wb-product-btn">去看看</el-button>
                    </div>
                  </div>
                  <div v-if="msg.type === 'ai'" class="wb-ai-sign">
                    <span class="wb-ai-circle">AI</span>
                    <span class="wb-ai-txt">AI回答</span>
                    <span
                      v-if="typeof msg.confidence === 'number'"
                      class="wb-ai-confidence"
                      :class="confidenceLevel(msg.confidence).class"
                    >
                      {{ confidenceLevel(msg.confidence).text }} {{ msg.confidence }}%
                    </span>
                    <span class="wb-ai-time">
                      {{ formatMsgTime(msg.created_at) }}
                    </span>
                  </div>
                </div>
                <div class="wb-msg-avatar wb-msg-avatar-agent">
                  {{ msg.type === 'ai' ? 'AI' : '客服' }}
                </div>
              </div>
            </template>
          </div>

          <!-- 快捷按钮 + 输入 -->
          <div class="wb-input-area">
            <div class="wb-quick">
              <div
                class="wb-quick-pill"
                v-for="r in quickReplies"
                :key="r"
                @click="inputText = quickReplyMap[r]"
              >
                <el-icon size="14"><component :is="quickRepliesIcons[r]" /></el-icon>
                <span>{{ r }}</span>
              </div>
              <div class="wb-quick-pill" @click="insertProductCard()">
                <el-icon size="14"><ShoppingBag /></el-icon>
                <span>商品卡片</span>
              </div>
              <div class="wb-quick-pill" @click="handleSendCoupon">
                <el-icon size="14"><Present /></el-icon>
                <span>发优惠券</span>
              </div>
              <div class="wb-quick-pill" @click="handleQuickReply">
                <el-icon size="14"><ChatLineSquare /></el-icon>
                <span>快捷话术</span>
              </div>
            </div>
            <div class="wb-input-row">
              <el-input
                v-model="inputText"
                type="textarea"
                :rows="2"
                placeholder="输入回复内容，AI将实时辅助生成建议..."
                resize="none"
                @keydown.enter.exact.prevent="handleSend"
              />
              <div class="wb-send">
                <el-button type="primary" size="large" @click="handleSend" :loading="sending" class="wb-send-btn">
                  发送
                </el-button>
                <span class="wb-send-hint">Enter ↵</span>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="wb-chat-empty">
            <div class="wb-empty-circle">
              <el-icon :size="34" color="#2563EB"><ChatDotRound /></el-icon>
            </div>
            <p class="wb-empty-title">等待接待的客户</p>
            <p class="wb-empty-sub">从左侧选择一位客户，开始高效服务</p>
          </div>
        </template>
      </main>

      <!-- 右栏：AI 面板（卡片化：AI智能分析 + AI推荐回复 + 订单 + 物流） -->
      <aside class="wb-right" v-if="store.currentSession">
        <!-- AI 智能分析卡片 -->
        <div class="wb-card wb-ai-card">
          <h3 class="wb-card-title">
            <span class="wb-card-title-dot" style="background:#8B5CF6"></span>
            AI 智能分析
          </h3>
          <div class="wb-analysis-list">
            <!-- 用户意图 + 情绪状态：两列并排 -->
            <div class="wb-analysis-row2">
              <div class="wb-analysis-item wb-analysis-item-block">
                <span class="wb-analysis-label">用户意图</span>
                <div class="wb-analysis-tags">
                  <span
                    v-for="opt in intentOptions"
                    :key="opt"
                    class="wb-analysis-tag"
                    :class="{ active: (store.currentSession.intent || '待识别') === opt }"
                    @click="store.currentSession && (store.currentSession.intent = opt)"
                  >{{ opt }}</span>
                </div>
              </div>
              <div class="wb-analysis-item wb-analysis-item-block">
                <span class="wb-analysis-label">情绪状态</span>
                <div class="wb-analysis-tags">
                  <span
                    v-for="opt in emotionOptions"
                    :key="opt"
                    class="wb-analysis-tag"
                    :class="{ active: (store.currentSession.emotion || '平稳') === opt }"
                    @click="store.currentSession && (store.currentSession.emotion = opt)"
                  >{{ emotionEmojiMap[opt] }} {{ opt }}</span>
                </div>
              </div>
            </div>
            <!-- 价值评分 + AI置信度：两列并排 -->
            <div class="wb-analysis-row2">
              <div class="wb-analysis-item wb-analysis-item-block">
                <span class="wb-analysis-label">价值评分</span>
                <div class="wb-score-bar">
                  <el-progress
                    :percentage="store.currentSession.score"
                    :color="scoreColor(store.currentSession.score)"
                    :show-text="false"
                    :stroke-width="6"
                  />
                  <div class="wb-score-label">
                    <span class="wb-score-level" :style="{ color: scoreColor(store.currentSession.score) }">
                      {{ store.currentSession.score }}分 · {{ scoreLevel(store.currentSession.score) }}
                    </span>
                    <span class="wb-score-hint" v-if="store.currentSession.score >= 70">转人工</span>
                  </div>
                </div>
              </div>
              <div class="wb-analysis-item wb-analysis-item-block">
                <span class="wb-analysis-label">AI 置信度</span>
                <div class="wb-score-bar">
                  <el-progress
                    :percentage="confidenceScore"
                    :color="confidenceColor(confidenceScore)"
                    :show-text="false"
                    :stroke-width="6"
                  />
                  <div class="wb-score-label">
                    <span class="wb-score-level" :style="{ color: confidenceColor(confidenceScore) }">
                      {{ confidenceScore }}% · {{ confidenceLevel(confidenceScore).text.replace(/[🟢🟡🟠🔴]\s*/, '') }}
                    </span>
                    <span class="wb-score-hint" v-if="confidenceScore < 80">转人工</span>
                  </div>
                </div>
              </div>
            </div>
            <!-- 推荐处理路径 -->
            <div class="wb-analysis-item wb-analysis-item-block">
              <span class="wb-analysis-label">推荐处理路径</span>
              <div class="wb-analysis-tags">
                <span
                  v-for="opt in pathOptions"
                  :key="opt"
                  class="wb-analysis-path-item"
                  :class="{ active: currentPath === opt }"
                  @click="currentPath = opt"
                >{{ opt }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- AI 推荐回复卡片 -->
        <div class="wb-card wb-reply-card">
          <h3 class="wb-card-title">
            <span class="wb-card-title-dot" style="background:#14B8A6"></span>
            AI 推荐回复
          </h3>

          <div v-if="store.aiThinking" class="wb-ai-thinking">
            <div class="wb-ai-thinking-head">
              <div class="wb-dots">
                <span></span><span></span><span></span>
              </div>
              <span>AI正在检索知识库并生成回复...</span>
            </div>
            <div class="wb-thinking-steps">
              <div :class="['wb-step', { active: thinkingStep >= 0 }]"><el-icon><Search /></el-icon>RAG检索知识库</div>
              <div :class="['wb-step', { active: thinkingStep >= 1 }]"><el-icon><Setting /></el-icon>意图识别 & 情绪分析</div>
              <div :class="['wb-step', { active: thinkingStep >= 2 }]"><el-icon><ChatLineSquare /></el-icon>生成推荐话术</div>
            </div>
            <div class="wb-thinking-bar"></div>
          </div>

          <div v-else class="wb-reply-box">
            <div
              v-for="(r, idx) in store.replies"
              :key="r.id"
              class="wb-reply-item wb-reply-slide"
              :style="{ animationDelay: idx * 0.1 + 's' }"
              @click="useReply(r.text)"
            >
              <span>{{ r.text }}</span>
              <div class="wb-reply-footer">
                <span class="wb-reply-tag">
                  <el-icon :size="13"><Link /></el-icon>
                  自动关联工单
                </span>
              </div>
            </div>

            <el-button
              v-if="!store.aiThinking"
              text
              type="primary"
              size="small"
              class="wb-more"
              :loading="regeneratingReplies"
              @click="loadMoreReplies"
            >查看更多话术 →</el-button>
          </div>
        </div>

        <!-- 订单 + 物流：保持数据逻辑不变，只换卡片样式 -->
        <div class="wb-card wb-orders-card">
          <h3 class="wb-card-title">
            <span class="wb-card-title-dot" style="background:#2563EB"></span>
            关联订单
            <span class="wb-card-sub">最近{{ store.orders.length }}笔</span>
          </h3>
          <div class="wb-order-list">
            <div v-for="o in store.orders" :key="o.id" class="wb-order-item">
              <div class="wb-order-row">
                <span class="wb-order-name">{{ o.name }}</span>
                <span :class="['wb-order-status', getLogisticsStatusClass(o.logistics_status)]">
                  {{ o.status }}
                </span>
              </div>
              <div class="wb-order-meta">订单号：{{ o.order_no }} · {{ o.price }}</div>
            </div>
          </div>
        </div>

        <div class="wb-card wb-logistics-card" v-if="store.logistics.length">
          <h3 class="wb-card-title">
            <span class="wb-card-title-dot" style="background:#F59E0B"></span>
            物流轨迹
            <span class="wb-card-sub">{{ store.logistics.length }}个包裹</span>
          </h3>
          <div class="wb-log-list">
            <div v-for="log in store.logistics" :key="log.order_id" class="wb-log-item">
              <template v-if="log.tracking_no">
                <div class="wb-log-header">
                  <span class="wb-log-product">{{ log.product_name }}</span>
                  <span :class="['wb-log-status', getLogisticsStatusClass(log.status)]">{{ log.status_label }}</span>
                </div>
                <div class="wb-log-meta">{{ log.carrier }} · {{ log.tracking_no }}</div>
                <div class="wb-log-timeline" v-if="log.timeline.length">
                  <div v-for="(track, i) in log.timeline" :key="i" class="wb-log-tline">
                    <div class="wb-log-dot" :class="{ active: i === log.timeline.length - 1 }"></div>
                    <div class="wb-log-content">
                      <div class="wb-log-time">{{ track.time }} · {{ track.location }}</div>
                      <div class="wb-log-desc">{{ track.desc }}</div>
                    </div>
                  </div>
                </div>
                <el-button
                  v-if="log.status !== 'delivered' && log.status !== 'pending'"
                  size="small" text type="primary"
                  :loading="urgingTracking === log.tracking_no"
                  @click="handleUrge(log.tracking_no)"
                >催件</el-button>
              </template>
              <template v-else>
                <div class="wb-log-header">
                  <span class="wb-log-product">{{ log.product_name }}</span>
                  <span class="wb-log-status status-pending">待发货</span>
                </div>
                <div class="wb-log-meta">订单号：{{ log.order_no }} · 预计48小时内发货</div>
              </template>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="wb-card wb-action-card">
          <el-button size="large" class="wb-action-btn wb-action-ticket" @click="showTicketDialog = true">
            <el-icon><Tickets /></el-icon>创建工单
          </el-button>
          <el-button size="large" class="wb-action-btn wb-action-warn" @click="handleMarkRisk">
            <el-icon><WarningFilled /></el-icon>标记风险并升级
          </el-button>
          <el-button size="large" class="wb-action-btn wb-action-ok" @click="handleEndSession">
            <el-icon><CircleCheck /></el-icon>结束会话并归档
          </el-button>
        </div>
      </aside>
    </div>

    <!-- 用户详情 Dialog -->
    <el-dialog v-model="showUserDetail" title="用户详情" width="520px">
      <div class="user-detail" v-if="store.currentSession">
        <div class="detail-header">
          <div class="detail-avatar" :style="{ background: avatarColor(store.currentSession.user_name) }">
            {{ store.currentSession.user_avatar }}
          </div>
          <div>
            <h3>{{ store.currentSession.user_name }}</h3>
            <p class="detail-id">User ID: UQ-20250310-01823</p>
          </div>
        </div>
        <div class="detail-grid">
          <div class="detail-item"><span class="d-label">来源平台</span><span class="d-value">{{ store.currentSession.source }}</span></div>
          <div class="detail-item"><span class="d-label">会员等级</span><span class="d-value">🥇 金卡会员</span></div>
          <div class="detail-item"><span class="d-label">累计消费</span><span class="d-value">¥5,280.00</span></div>
          <div class="detail-item"><span class="d-label">订单数</span><span class="d-value">3单</span></div>
          <div class="detail-item"><span class="d-label">空间类型</span><span class="d-value">中户型 (90㎡)</span></div>
          <div class="detail-item"><span class="d-label">家庭人数</span><span class="d-value">3-4人</span></div>
          <div class="detail-item"><span class="d-label">风格偏好</span><span class="d-value">简约现代</span></div>
          <div class="detail-item"><span class="d-label">购买偏好</span><span class="d-value">收纳 · 厨房</span></div>
          <div class="detail-item"><span class="d-label">预算敏感度</span><span class="d-value">中敏感</span></div>
          <div class="detail-item"><span class="d-label">风险标签</span><span class="d-value text-danger">⚠ 退款风险</span></div>
        </div>
      </div>
    </el-dialog>

    <!-- 创建工单 Dialog -->
    <el-dialog v-model="showTicketDialog" title="创建工单" width="560px">
      <el-form :model="ticketForm" label-width="90px" size="default">
        <el-form-item label="工单标题" required>
          <el-input v-model="ticketForm.title" placeholder="自动生成，可修改" />
        </el-form-item>
        <el-form-item label="工单类型" required>
          <el-select v-model="ticketForm.type" placeholder="选择工单类型" style="width:100%">
            <el-option label="售前咨询" value="售前咨询" />
            <el-option label="售后问题" value="售后问题" />
            <el-option label="质量问题" value="质量问题" />
            <el-option label="物流问题" value="物流问题" />
            <el-option label="投诉建议" value="投诉建议" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" required>
          <el-select v-model="ticketForm.priority" style="width:100%">
            <el-option label="低" value="低" />
            <el-option label="中" value="中" />
            <el-option label="高" value="高" />
            <el-option label="紧急" value="紧急" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理人">
          <el-select v-model="ticketForm.assignee" placeholder="自动分配" style="width:100%" clearable>
            <el-option label="自动分配" value="自动分配" />
            <el-option label="指定客服" value="指定客服" />
            <el-option label="指定售后" value="指定售后" />
            <el-option label="指定主管" value="指定主管" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联订单">
          <el-input v-model="ticketForm.orderNo" placeholder="输入订单号（可选）" />
        </el-form-item>
        <el-form-item label="问题描述">
          <el-input v-model="ticketForm.description" type="textarea" :rows="3" placeholder="自动填充会话摘要，可修改" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTicketDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateTicket">创建工单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, computed, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Headset, Odometer, Bell, UserFilled, Search, User,
  ChatDotRound, Setting, ChatLineSquare, ShoppingBag,
  WarningFilled, CircleCheckFilled, CircleCheck, Box,
  ChatDotSquare, VideoPlay, Delete, Van, Link,
  Search as SearchIcon, Goods, RefreshRight, Tickets, Present,
} from '@element-plus/icons-vue'
import { useSessionStore, calcConfidence } from '../stores/session'
import { useAuthStore } from '../stores/auth'
import { aiAPI } from '../api/session'

const store = useSessionStore()
const authStore = useAuthStore()
const router = useRouter()
const inputText = ref('')
const sending = ref(false)
const simLoading = ref(false)
const showUserDetail = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const urgingTracking = ref('')

// 创建工单弹窗状态
const showTicketDialog = ref(false)
const ticketForm = ref({
  title: '',
  type: '',
  priority: '中',
  assignee: '自动分配',
  orderNo: '',
  description: '',
})

// AI 智能分析可选项
const intentOptions = ['产品咨询', '物流查询', '退换咨询', '优惠咨询', '安装指导', '商品推荐', '售后投诉', '退款咨询', '投诉升级', '一般咨询']
const emotionOptions = ['平稳', '积极', '略有不满', '略有焦虑', '不满', '愤怒', '激动']
const emotionEmojiMap: Record<string, string> = {
  '平稳': '😊',
  '积极': '😄',
  '略有不满': '😕',
  '略有焦虑': '😟',
  '不满': '😞',
  '愤怒': '😡',
  '激动': '😤',
}
const pathOptions = ['AI自动回复', '售后挽回', '转人工客服', '转售后专员', '创建工单', '升级主管']
// 当前推荐处理路径（可点击切换）
const currentPath = ref('AI自动回复')

// AI 思考分步激活：-1 表示未激活，0/1/2 表示第 0~2 步激活
const thinkingStep = ref(-1)
let thinkingTimers: number[] = []
let pollTimer: number | undefined
let msgPollTimer: number | undefined

// 消息去重视图层：按 id 去重，防止同一消息被渲染两次（不管是 store 重复 push 或后端重复落库）
const renderedMessages = computed(() => {
  const seen = new Set<number>()
  const out: typeof store.messages = []
  for (const m of store.messages) {
    if (m.id == null) { out.push(m); continue }
    if (seen.has(m.id)) continue
    seen.add(m.id)
    out.push(m)
  }
  return out
})

/** AI 置信度：基于 risk/emotion/intent 前端推算，用于提示客服是否需要转人工 */
const confidenceScore = computed(() => {
  if (!store.currentSession) return 0
  const s = store.currentSession
  return calcConfidence(s.risk, s.emotion, s.intent)
})

/** 置信度等级文字与样式类 */
function confidenceLevel(score: number) {
  if (score >= 90) return { text: '🟢 高置信', class: 'conf-high' }
  if (score >= 80) return { text: '🟡 中等置信', class: 'conf-mid' }
  if (score >= 50) return { text: '🟠 低置信', class: 'conf-low' }
  return { text: '🔴 无信心', class: 'conf-none' }
}

/** 会话价值评分等级文字 */
function scoreLevel(score: number): string {
  if (score >= 85) return '极高价值'
  if (score >= 70) return '高价值'
  if (score >= 40) return '中等价值'
  return '常规价值'
}

/** 会话价值评分对应进度条颜色 */
function scoreColor(score: number): string {
  if (score >= 70) return '#10B981'
  if (score >= 40) return '#F59E0B'
  return '#EF4444'
}

/** 置信度对应进度条颜色 */
function confidenceColor(score: number): string {
  if (score >= 90) return '#10B981'
  if (score >= 80) return '#F59E0B'
  if (score >= 50) return '#F97316'
  return '#EF4444'
}

watch(
  () => store.aiThinking,
  v => {
    // 清理之前的定时器
    thinkingTimers.forEach(t => window.clearTimeout(t))
    thinkingTimers = []
    if (v) {
      thinkingStep.value = -1
      thinkingTimers.push(window.setTimeout(() => { thinkingStep.value = 0 }, 120))
      thinkingTimers.push(window.setTimeout(() => { thinkingStep.value = 1 }, 450))
      thinkingTimers.push(window.setTimeout(() => { thinkingStep.value = 2 }, 820))
    } else {
      thinkingStep.value = -1
    }
  },
  { immediate: true },
)

const quickReplies = ['查询中', '推荐商品', '退换说明', '物流更新']
const quickRepliesIcons: Record<string, Component> = {
  '查询中': SearchIcon,
  '推荐商品': Goods,
  '退换说明': RefreshRight,
  '物流更新': Tickets,
}
const quickReplyMap: Record<string, string> = {
  '查询中': '亲，您的问题我已经了解了，正在为您查询中～',
  '推荐商品': '根据您的需求，为您推荐以下几款商品：',
  '退换说明': '这款商品支持7天无理由退换，上门取件，您完全不用担心～',
  '物流更新': '您的订单已发货，物流单号已更新，预计3-5天送达～',
}

/** 根据姓名首字返回稳定的浅彩色（对应设计稿头像颜色） */
function avatarColor(name: string): string {
  const palette = [
    '#FEE2E2', '#FDE68A', '#BBF7D0', '#A5F3FC',
    '#BFDBFE', '#DDD6FE', '#FBCFE8', '#E0E7FF',
  ]
  let h = 0
  for (let i = 0; i < (name || '').length; i++) {
    h = (h * 31 + name.charCodeAt(i)) >>> 0
  }
  return palette[h % palette.length]
}

/** 对应设计稿情绪表情的分数分级样式 */
function scoreClass(score: number): string {
  if (score >= 70) return 'score-ok'
  if (score >= 50) return 'score-warn'
  return 'score-danger'
}

/** 把 Date/time 字符串格式化成 HH:mm 短时间 */
function formatMsgTime(t?: string | Date | null): string {
  if (!t) return ''
  const d = t instanceof Date ? t : new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  return d.toTimeString().slice(0, 5)
}

function getTagClass(cls: string) {
  if (cls.includes('danger') || cls.includes('red')) return 'tag-danger'
  if (cls.includes('warning') || cls.includes('orange')) return 'tag-warning'
  if (cls.includes('success') || cls.includes('green')) return 'tag-success'
  if (cls.includes('primary') || cls.includes('blue')) return 'tag-primary'
  return 'tag-gray'
}

function getScoreColor(score: number) {
  if (score >= 70) return '#10B981'
  if (score >= 50) return '#2563EB'
  return '#EF4444'
}

function getLogisticsStatusClass(status: string) {
  if (status === 'delivered') return 'status-delivered'
  if (status === 'delivering') return 'status-delivering'
  if (status === 'in_transit') return 'status-transit'
  if (status === 'shipped') return 'status-shipped'
  if (status === 'exception') return 'status-exception'
  if (status === 'pending') return 'status-pending'
  return 'status-pending'
}

async function handleUrge(trackingNo: string) {
  urgingTracking.value = trackingNo
  try {
    const result = await store.urgeLogistics(trackingNo)
    ElMessage.success(result.message)
  } catch {
    ElMessage.error('催件失败，请重试')
  } finally {
    urgingTracking.value = ''
  }
}

async function selectSession(id: number) {
  // 切换会话前停止上一个会话的自动模拟，避免后台继续向旧会话发消息
  store.stopAutoSimulate()
  await store.loadSession(id)
  await nextTick()
  scrollToBottom()
  // 选中会话后启动消息轮询，实时接收客户端发来的新消息
  startMsgPolling()
}

/** 启动当前会话消息轮询（每3秒拉取新消息） */
function startMsgPolling() {
  stopMsgPolling()
  msgPollTimer = window.setInterval(async () => {
    if (!store.currentSession) return
    const appended = await store.pollCurrentMessages()
    if (store.needsHumanTip) {
      const intent = store.currentSession?.intent || '待识别'
      ElMessage.warning(`📩 客户发来新消息（${intent}），需人工处理，AI已生成${store.replies.length}条推荐话术`)
      store.needsHumanTip = false
    }
    if (appended) scrollToBottom()
  }, 3000)
}

/** 停止消息轮询 */
function stopMsgPolling() {
  if (msgPollTimer) {
    window.clearInterval(msgPollTimer)
    msgPollTimer = undefined
  }
}

/** 客服发送消息 */
async function handleSend() {
  const text = inputText.value.trim()
  if (!text) { ElMessage.warning('请输入回复内容'); return }
  if (!store.currentSession) return

  sending.value = true
  try {
    // 客服手动回复，type为agent，不显示AI标签；保存到后端
    await store.sendMessage(text, 'agent', false)
    inputText.value = ''
    scrollToBottom()
  } catch {
    ElMessage.error('发送失败，请重试')
  } finally {
    sending.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

function useReply(text: string) {
  inputText.value = text
  ElMessage.success('话术已填入输入框，可直接发送或修改')
}

async function insertProductCard() {
  ElMessage.success('商品卡片已插入聊天区')
  // 保存到后端
  await store.sendMessage('为您推荐以下商品：', 'ai', true)
  scrollToBottom()
}

/** 清空聊天记录 */
async function handleClearMessages() {
  try {
    await ElMessageBox.confirm('确定要清空当前会话的聊天记录吗？', '提示', {
      type: 'warning',
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
    })
    await store.clearMessages()
    ElMessage.success('聊天记录已清空')
  } catch {
    // 用户取消
  }
}

/** 一键清除所有客户信息（初始化工作台） */
async function handleClearAll() {
  try {
    await ElMessageBox.confirm(
      '确定要清除所有客户信息吗？此操作将删除全部会话、消息、订单和物流记录，不可恢复！',
      '初始化工作台',
      { type: 'error', confirmButtonText: '确认清除', cancelButtonText: '取消' },
    )
    stopMsgPolling()
    const resp = await store.clearAll()
    ElMessage.success(`已清除：${resp.deleted.sessions}个会话 / ${resp.deleted.messages}条消息 / ${resp.deleted.orders}个订单`)
  } catch {
    // 用户取消
  }
}

/** 模拟客户发消息 */
async function handleSimulate() {
  simLoading.value = true
  try {
    // 不传intent，让后端随机选择不同场景
    const result = await store.simulateCustomer()
    if (result) {
      if (result.status === 'waiting') {
        ElMessage.info('⏳ 客户正在等待你的回复，请先回复客户消息')
      } else if (result.is_urge) {
        ElMessage.warning('⏰ 客户在催你回复了！')
        scrollToBottom()
      } else if (result.analysis) {
        const canAuto = result.analysis.can_auto_answer
        const tip = canAuto
          ? `📩 客户发来新消息（${result.analysis.intent}），AI已自动回答`
          : `📩 客户发来新消息（${result.analysis.intent}），需人工处理，AI已生成${result.analysis.suggested_replies.length}条推荐话术`
        ElMessage.success(tip)
      }
    }
    scrollToBottom()
    await nextTick()
    scrollToBottom()
  } catch {
    ElMessage.error('模拟消息失败')
  } finally {
    simLoading.value = false
  }
}

/** 标记风险 */
async function handleMarkRisk() {
  await store.markRisk()
  ElMessage.warning('⚠ 已标记为高风险会话')
  await store.loadSession(store.currentSession!.id)
  scrollToBottom()
}

/** 结束会话并归档 */
async function handleEndSession() {
  if (!store.currentSession) return
  try {
    await ElMessageBox.confirm('确定要结束当前会话并归档吗？', '结束会话', {
      confirmButtonText: '确定归档',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await store.endSession()
    // 会话结束后停止消息轮询，避免继续请求已归档会话
    stopMsgPolling()
    ElMessage.success('✅ 会话已结束，已自动归档')
    // 归档系统消息保存到后端
    await store.sendSystemMessage('📁 会话已结束并归档。会话摘要已生成。')
    scrollToBottom()
    // 刷新会话列表
    await store.fetchSessions()
  } catch {
    // 用户取消
  }
}

const regeneratingReplies = ref(false)

async function loadMoreReplies() {
  if (!store.currentSession) return
  regeneratingReplies.value = true
  try {
    const res = await aiAPI.regenerateReplies(store.currentSession.id)
    const batch = Date.now()
    store.replies = res.replies.map((r, i) => ({ id: batch + i, text: r.text, sort_order: i }))
    // 注意：store 内部维护了 cache（未导出），此处无法直接同步更新 cache.replies。
    // 切换会话后 store.loadSession 会重新拉取并覆盖 replies，因此不会出现脏数据；
    // 若未来需要在不切换会话的情况下保持 cache 一致，请将本方法下沉到 store 中。
    ElMessage.success('已重新生成推荐话术')
  } catch {
    ElMessage.error('生成话术失败，请重试')
  } finally {
    regeneratingReplies.value = false
  }
}

/** 创建工单 */
function handleCreateTicket() {
  if (!ticketForm.value.title || !ticketForm.value.type) {
    ElMessage.warning('请填写工单标题和类型')
    return
  }
  ElMessage.success(`工单已创建：${ticketForm.value.title}（${ticketForm.value.type}·${ticketForm.value.priority}）`)
  showTicketDialog.value = false
  // 重置表单
  ticketForm.value = { title: '', type: '', priority: '中', assignee: '自动分配', orderNo: '', description: '' }
}

/** 发优惠券 */
function handleSendCoupon() {
  ElMessage.success('已向客户发送10元无门槛优惠券')
}

/** 快捷话术：随机填入一条常用话术 */
function handleQuickReply() {
  const replies = [
    '亲，您好！很高兴为您服务，请问有什么可以帮您的吗？',
    '亲，您的问题我已收到，马上为您处理～',
    '亲，请稍等，我帮您查询一下订单信息。',
    '亲，感谢您的耐心等待，问题已为您解决～',
  ]
  inputText.value = replies[Math.floor(Math.random() * replies.length)]
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  // 工作台初始为空，等待客户从 /server 客户端发起咨询
  store.fetchSessions()
  // 每 5 秒静默轮询刷新会话列表（不触发 loading，增量对比避免闪烁）
  pollTimer = window.setInterval(() => {
    store.fetchSessions(true)
  }, 5000)
})

// 监听渲染消息变化和AI思考状态，自动滚动到底部
watch(() => renderedMessages.value.length, () => { scrollToBottom() })
watch(() => store.aiThinking, () => { scrollToBottom() })

// 打开工单弹窗时自动填充会话信息
watch(showTicketDialog, (v) => {
  if (v && store.currentSession) {
    ticketForm.value.title = `${store.currentSession.intent || '问题'} - ${store.currentSession.user_name}`
    ticketForm.value.description = `客户${store.currentSession.user_name}（来自${store.currentSession.source}）咨询${store.currentSession.intent || '问题'}，情绪：${store.currentSession.emotion || '平稳'}，风险：${store.currentSession.risk || '低'}`
  }
})

// 切换会话时根据风险/情绪/意图重置推荐处理路径
watch(() => store.currentSession?.id, () => {
  if (!store.currentSession) return
  const s = store.currentSession
  if (s.risk?.includes('高风险') || s.emotion === '愤怒') currentPath.value = '升级主管'
  else if (s.score >= 70) currentPath.value = '转人工客服'
  else if (s.intent?.includes('售后') || s.intent?.includes('投诉')) currentPath.value = '售后挽回'
  else currentPath.value = 'AI自动回复'
}, { immediate: true })

onUnmounted(() => {
  store.stopAutoSimulate()
  if (pollTimer) window.clearInterval(pollTimer)
  stopMsgPolling()
  // 清理 AI 思考分步激活定时器，避免组件卸载后回调仍触发
  thinkingTimers.forEach(t => window.clearTimeout(t))
  thinkingTimers = []
})
</script>

<style scoped>
/* =========================================================
   Workbench 工作台 —— 严格对照设计稿样式
   ========================================================= */
.workbench-page {
  display: flex; flex-direction: column;
  height: 100vh; overflow: hidden;
  background: var(--bg-page);
  color: var(--text-primary);
}

/* ---------- 顶部导航 ---------- */
.wb-header {
  display: flex; align-items: center; justify-content: space-between;
  height: 64px; padding: 0 28px;
  background: #fff; border-bottom: 1px solid var(--border-gray);
  flex-shrink: 0;
}
.wb-header-left { display: flex; align-items: center; gap: 14px; }
.brand-divider { width: 1px; height: 22px; background: var(--border-gray); display: inline-block; }
.brand-title { font-size: 14px; color: var(--text-secondary); letter-spacing: 0.3px; }
.wb-header-right { display: flex; align-items: center; gap: 12px; }
.wb-nav-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 18px; border-radius: var(--r-lg);
  border: 1px solid var(--border-gray);
  background: #fff; color: var(--text-secondary);
  font-size: 13px; cursor: pointer; transition: all 0.15s;
}
.wb-nav-btn:hover { color: var(--primary); border-color: var(--primary-tint); }
.wb-nav-btn.active {
  background: var(--primary); color: #fff; border-color: var(--primary);
  box-shadow: 0 2px 6px rgba(37,99,235,0.25);
}
.wb-right-divider { width: 1px; height: 22px; background: var(--border-gray); margin: 0 4px; }
.wb-icon-btn {
  width: 34px; height: 34px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--border-gray); color: var(--text-secondary);
  cursor: pointer; transition: all 0.15s;
}
.wb-icon-btn:hover { color: var(--primary); border-color: var(--primary-tint); }
.wb-user-info {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--text-secondary); padding: 6px 10px;
  border-radius: var(--r-lg); border: 1px solid var(--border-gray);
}
.wb-user-info:hover { color: var(--primary); }
.wb-logout { color: var(--text-tertiary) !important; }
.wb-logout:hover { color: var(--danger) !important; }

/* ---------- 主内容三栏 ---------- */
.wb-body { display: flex; flex: 1; overflow: hidden; background: var(--bg-gray); }

/* ---------- 左栏：会话列表 ---------- */
.wb-left {
  width: 300px; background: #fff; border-right: 1px solid var(--border-gray);
  display: flex; flex-direction: column; flex-shrink: 0;
}
.wb-search {
  padding: 16px;
  border-bottom: 1px solid var(--border-gray);
  display: flex;
  align-items: center;
  gap: 8px;
}
.wb-search .el-input { flex: 1; }
.wb-init-btn {
  flex-shrink: 0;
  font-weight: 600;
  letter-spacing: 1px;
}
.wb-tabs { display: flex; border-bottom: 1px solid var(--border-gray); padding: 0 10px; }
.wb-tab {
  flex: 1; text-align: center; padding: 12px 6px; cursor: pointer;
  color: var(--text-secondary); transition: all 0.2s; position: relative;
  font-size: 13px; font-weight: 500;
}
.wb-tab em {
  font-style: normal; margin-left: 4px; padding: 0 6px;
  background: var(--bg-gray); color: var(--text-tertiary);
  font-size: 11px; border-radius: var(--r-full);
}
.wb-tab.active { color: var(--primary); }
.wb-tab.active::after {
  content: ''; position: absolute; bottom: -1px; left: 20%; right: 20%;
  height: 2px; background: var(--primary); border-radius: 2px 2px 0 0;
}
.wb-session-list { flex: 1; overflow-y: auto; padding: 6px; }
.wb-session-item {
  border-radius: var(--r-lg); cursor: pointer;
  transition: background 0.15s var(--ease-soft);
  margin-bottom: 4px; border: 1px solid transparent;
}
.wb-session-row { display: flex; gap: 10px; padding: 12px 12px; }
.wb-session-item:hover { background: var(--bg-gray); }
.wb-session-item.active {
  background: var(--primary-soft); border-color: var(--primary-tint);
}
.wb-session-avatar {
  width: 38px; height: 38px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600; color: var(--text-primary);
  flex-shrink: 0;
}
.wb-session-info { flex: 1; min-width: 0; }
.wb-session-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.wb-session-name { font-weight: 600; font-size: 13px; }
.wb-session-time { font-size: 11px; color: var(--text-tertiary); }
.wb-session-preview {
  font-size: 12px; color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.wb-session-tags { display: flex; gap: 4px; margin-top: 6px; flex-wrap: wrap; }
.wb-tag {
  font-size: 11px; line-height: 1.4; padding: 1px 8px;
  border-radius: var(--r-full); font-weight: 500;
  display: inline-flex; align-items: center; gap: 2px;
  border: 1px solid transparent;
}
.wb-tag.tag-danger { background: var(--danger-soft); color: var(--danger); }
.wb-tag.tag-warning { background: var(--warning-soft); color: var(--warning); }
.wb-tag.tag-success { background: var(--success-soft); color: var(--success); }
.wb-tag.tag-primary { background: var(--primary-soft); color: var(--primary); }
.wb-tag.tag-purple  { background: var(--purple-soft);  color: var(--purple); }
.wb-tag.tag-gray    { background: var(--bg-gray);      color: var(--text-secondary); border-color: var(--border-gray); }
.wb-tag.tag-outline-danger { background:#fff; color: var(--danger); border-color: var(--danger); }

.wb-empty { padding: 40px 20px; text-align: center; color: var(--text-tertiary); font-size: 13px; }
.wb-empty-icon { font-size: 32px; margin-bottom: 8px; opacity: 0.6; }
.wb-empty-sub { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }

/* ---------- 中栏：聊天区 ---------- */
.wb-center { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #fff; }
.wb-chat-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; border-bottom: 1px solid var(--border-gray);
  background: #fff;
}
.wb-chat-user { display: flex; align-items: center; gap: 12px; }
.wb-chat-avatar {
  width: 42px; height: 42px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 600; color: var(--text-primary);
}
.wb-chat-user-top { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
.wb-chat-username { font-weight: 600; font-size: 15px; }
.wb-chat-source { font-size: 11px; color: var(--text-tertiary); }
.wb-chat-user-meta { font-size: 12px; color: var(--text-tertiary); }
.wb-chat-user-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.wb-btn-outline {
  background: #fff; color: var(--text-secondary); border: 1px solid var(--border-gray);
}
.wb-btn-outline:hover { color: var(--primary); border-color: var(--primary-tint); background: var(--primary-soft); }

.wb-chat-messages {
  flex: 1; overflow-y: auto; padding: 24px 28px;
  display: flex; flex-direction: column; gap: 18px;
}
.wb-msg-system {
  text-align: center; font-size: 12px; color: var(--text-tertiary);
  padding: 4px 0;
}
.wb-msg-row { display: flex; gap: 10px; align-items: flex-start; }
.wb-msg-row-left  { justify-content: flex-start; }
.wb-msg-row-right { justify-content: flex-end; }
.wb-msg-avatar {
  width: 38px; height: 38px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; flex-shrink: 0;
  color: var(--text-primary);
}
.wb-msg-avatar-agent { background: #10B981; color: #fff; }
.wb-msg-bubble {
  max-width: 480px; padding: 12px 16px;
  border-radius: 16px; font-size: 13px; line-height: 1.7;
  box-shadow: var(--shadow-sm);
}
.wb-msg-bubble-customer {
  background: #fff; color: var(--text-primary);
  border: 1px solid var(--border-gray);
  border-top-left-radius: 4px;
}
.wb-msg-bubble-agent {
  background: var(--primary); color: #fff;
  border-top-right-radius: 4px;
  box-shadow: 0 2px 10px rgba(37,99,235,0.22);
  padding-bottom: 10px;
}
.wb-ai-sign {
  margin-top: 10px; display: flex; align-items: center; gap: 6px;
  padding-top: 8px; border-top: 1px dashed rgba(255,255,255,0.25);
  font-size: 11px; color: rgba(255,255,255,0.7);
}
.wb-ai-circle {
  width: 18px; height: 18px; border-radius: 50%;
  background: rgba(255,255,255,0.18);
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-size: 10px; font-weight: 700;
}
.wb-ai-txt { font-weight: 500; }
.wb-ai-time { margin-left: auto; opacity: 0.75; }

/* AI 推荐商品卡（气泡内） */
.wb-product-card {
  margin-top: 10px; padding: 10px 12px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: var(--r-lg);
}
.wb-product-tip { font-size: 11px; opacity: 0.85; margin-bottom: 8px; }
.wb-product-body { display: flex; align-items: center; gap: 10px; }
.wb-product-img {
  width: 44px; height: 44px; background: #fff; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; color: var(--text-tertiary);
}
.wb-product-info { flex: 1; }
.wb-product-name { font-size: 13px; font-weight: 500; }
.wb-product-price { font-size: 15px; font-weight: 600; margin-top: 2px; }
.wb-product-btn {
  background: #fff !important; color: var(--primary) !important;
  border-color: #fff !important;
}

/* 输入区 */
.wb-input-area {
  background: #fff; border-top: 1px solid var(--border-gray);
  padding: 14px 20px 18px;
}
.wb-quick { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.wb-quick-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: var(--r-full);
  background: #fff; border: 1px solid var(--border-gray);
  font-size: 12px; color: var(--text-secondary);
  cursor: pointer; transition: all 0.15s;
}
.wb-quick-pill:hover {
  background: var(--primary-soft); color: var(--primary);
  border-color: var(--primary-tint);
}
.wb-input-row { display: flex; gap: 14px; align-items: flex-end; }
.wb-send { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.wb-send-btn {
  padding: 0 30px !important; height: 44px !important;
  border-radius: var(--r-lg) !important;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(37,99,235,0.28);
}
.wb-send-hint { font-size: 11px; color: var(--text-tertiary); }

/* 空状态 */
.wb-chat-empty {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: #fff;
  padding: 40px 20px;
}
.wb-empty-circle {
  width: 72px; height: 72px; border-radius: 50%;
  background: var(--primary-soft); display: flex; align-items: center; justify-content: center;
  margin-bottom: 16px;
  animation: empty-pulse 3s ease-in-out infinite;
}
@keyframes empty-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(37,99,235,0.10); }
  50% { box-shadow: 0 0 0 14px rgba(37,99,235,0); }
}
.wb-empty-title { font-size: 15px; color: var(--text-secondary); font-weight: 500; margin-bottom: 4px; }
.wb-empty-sub { font-size: 13px; color: var(--text-tertiary); }

/* ---------- 右栏：AI 分析 / 推荐 / 订单 / 物流 ---------- */
.wb-right {
  width: 320px; background: var(--bg-gray);
  overflow-y: auto; flex-shrink: 0;
  padding: 10px 10px 16px; display: flex; flex-direction: column; gap: 10px;
}
.wb-card {
  background: #fff; border: 1px solid var(--border-gray);
  border-radius: var(--r-lg); padding: 12px 14px;
  box-shadow: var(--shadow-sm);
}
.wb-card-title {
  font-size: 13px; font-weight: 600;
  margin: 0 0 10px; padding: 0;
  display: flex; align-items: center; gap: 6px;
  color: var(--text-primary);
}
.wb-card-title-dot {
  width: 6px; height: 6px; border-radius: 50%; display: inline-block;
}
.wb-card-sub {
  margin-left: auto; font-size: 11px;
  color: var(--text-tertiary); font-weight: 400;
}

/* AI 智能分析卡片 */
.wb-analysis-list { display: flex; flex-direction: column; gap: 6px; }
.wb-analysis-item {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px;
}
.wb-analysis-label { color: var(--text-secondary); }
.wb-analysis-score {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 600;
}
.wb-analysis-score.score-danger { color: var(--danger); }
.wb-analysis-score.score-warn   { color: var(--warning); }
.wb-analysis-score.score-ok     { color: var(--success); }
.wb-analysis-emoji { font-size: 14px; }

/* AI 推荐回复卡片 */
.wb-ai-thinking {
  background: var(--primary-soft); border-radius: var(--r-md);
  padding: 12px; border: 1px solid var(--primary-tint);
}
.wb-ai-thinking-head {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 10px; font-size: 12px; color: var(--primary); font-weight: 600;
}
.wb-dots { display: flex; gap: 4px; }
.wb-dots span {
  width: 7px; height: 7px; border-radius: 50%; background: var(--primary);
  animation: dots-bounce 1.4s infinite ease-in-out both;
}
.wb-dots span:nth-child(1) { animation-delay: -0.32s; }
.wb-dots span:nth-child(2) { animation-delay: -0.16s; }
@keyframes dots-bounce {
  0%, 80%, 100% { transform: scale(0.55); opacity: 0.45; }
  40% { transform: scale(1.1); opacity: 1; }
}
.wb-thinking-steps { display: flex; flex-direction: column; gap: 4px; }
.wb-step {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--text-tertiary);
  padding: 5px 8px; border-radius: var(--r-sm);
  background: rgba(255,255,255,0.55); opacity: 0.5;
  transform: translateX(-6px);
  transition: color 0.3s, background 0.3s, opacity 0.3s, transform 0.3s;
}
.wb-step.active {
  color: var(--primary); font-weight: 600;
  background: rgba(37,99,235,0.12); opacity: 1;
  transform: translateX(0);
}
.wb-thinking-bar {
  height: 3px; border-radius: 2px; margin-top: 10px; overflow: hidden;
  background: rgba(37,99,235,0.10); position: relative;
}
.wb-thinking-bar::after {
  content: ''; position: absolute; top:0; left:0; bottom:0; width: 40%;
  background: linear-gradient(90deg, transparent, var(--primary), transparent);
  animation: bar-sweep 1.4s ease-in-out infinite;
}
@keyframes bar-sweep {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(350%); }
}

.wb-reply-box { display: flex; flex-direction: column; gap: 6px; }
.wb-reply-item {
  position: relative; padding: 7px 10px;
  background: var(--primary-soft);
  border: 1px solid var(--primary-tint);
  border-radius: var(--r-md);
  font-size: 11px; line-height: 1.5;
  cursor: pointer; transition: all 0.15s var(--ease-soft);
  color: var(--text-primary);
}
.wb-reply-item:hover {
  border-color: var(--primary);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37,99,235,0.15);
}
.wb-reply-footer {
  display: flex; justify-content: flex-end; align-items: center;
  margin-top: 5px; padding-top: 4px;
  border-top: 1px dashed var(--border-gray);
  font-size: 9px; color: var(--text-tertiary);
}
.wb-reply-tag { display: inline-flex; align-items: center; gap: 4px; }
.wb-reply-slide { animation: reply-slide 0.4s ease both; }
@keyframes reply-slide {
  from { opacity: 0; transform: translateX(12px); }
  to   { opacity: 1; transform: translateX(0); }
}
.wb-more { margin-top: 4px !important; width: 100%; justify-content: flex-start !important; }

/* 订单卡片 */
.wb-order-list { display: flex; flex-direction: column; gap: 8px; }
.wb-order-item {
  padding: 10px 12px; border: 1px solid var(--border-gray);
  border-radius: var(--r-lg); transition: all 0.15s; cursor: pointer;
}
.wb-order-item:hover { border-color: var(--primary-tint); background: var(--primary-soft); }
.wb-order-row { display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px; }
.wb-order-name { font-weight: 500; color: var(--text-primary); }
.wb-order-status {
  font-size: 11px; font-weight: 500; padding: 2px 8px;
  border-radius: var(--r-full);
}
.wb-order-meta { font-size: 11px; color: var(--text-tertiary); }

/* 物流轨迹 */
.wb-log-list { display: flex; flex-direction: column; gap: 10px; }
.wb-log-item {
  padding: 10px 12px; border: 1px solid var(--border-gray);
  border-radius: var(--r-lg);
}
.wb-log-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 12px; }
.wb-log-product { font-weight: 500; color: var(--text-primary); }
.wb-log-status {
  font-size: 11px; font-weight: 500; padding: 2px 8px;
  border-radius: var(--r-full);
}
.wb-log-meta { font-size: 11px; color: var(--text-tertiary); margin-bottom: 8px; }
.wb-log-timeline { position: relative; padding-left: 16px; }
.wb-log-tline { position: relative; padding-bottom: 10px; padding-left: 8px; border-left: 2px solid var(--border-gray); }
.wb-log-tline:last-child { padding-bottom: 0; border-left-color: transparent; }
.wb-log-dot {
  position: absolute; left: -7px; top: 2px; width: 8px; height: 8px;
  border-radius: 50%; background: #CBD5E1; border: 2px solid #fff;
}
.wb-log-dot.active { background: var(--primary); box-shadow: 0 0 0 3px var(--primary-tint); }
.wb-log-content { font-size: 11px; }
.wb-log-time { color: var(--text-tertiary); margin-bottom: 2px; }
.wb-log-desc { color: var(--text-secondary); line-height: 1.45; }

/* 物流状态色 */
.status-delivered  { color: var(--success); background: var(--success-soft); }
.status-delivering { color: var(--primary); background: var(--primary-soft); }
.status-transit    { color: var(--primary); background: var(--primary-soft); }
.status-shipped    { color: var(--info);    background: #ECFEFF; }
.status-exception  { color: var(--danger);  background: var(--danger-soft); }
.status-pending    { color: var(--text-tertiary); background: var(--bg-gray); }

/* 操作按钮卡 */
.wb-action-card { display: flex; flex-direction: column; gap: 10px; }
.wb-action-btn { width: 100%; }
.wb-action-warn {
  background: var(--warning-soft) !important;
  color: var(--warning) !important;
  border: 1px solid #FDE68A !important;
}
.wb-action-ok {
  background: var(--success-soft) !important;
  color: var(--success) !important;
  border: 1px solid #A7F3D0 !important;
}

.text-success { color: var(--success); }
.text-warning { color: var(--warning); }
.text-danger { color: var(--danger); }

/* 用户详情 Dialog */
.user-detail .detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.detail-avatar {
  width: 48px; height: 48px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 700; color: var(--text-primary);
}
.detail-id { font-size: 12px; color: var(--text-tertiary); }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.detail-item {
  background: var(--bg-gray); padding: 10px 12px;
  border-radius: var(--r-lg); font-size: 13px;
}
.d-label { display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 2px; }
.d-value { font-weight: 500; }

/* =========================================================
   AI 分析可选项 / 置信度 / 工单 / AI气泡置信度 扩展样式
   ========================================================= */
/* 分析项块状布局：标签在上、内容在下 */
.wb-analysis-item-block {
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
}
.wb-analysis-item-block .wb-analysis-label {
  font-size: 10px;
  color: var(--text-tertiary);
}
/* 两列并排布局 */
.wb-analysis-row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

/* AI分析可选项标签 */
.wb-analysis-tags {
  display: flex; flex-wrap: wrap; gap: 3px;
}
.wb-analysis-tag {
  padding: 1px 6px;
  font-size: 10px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid #E2E8F0;
  background: #F8FAFC;
  color: #64748B;
  transition: all 0.15s;
  line-height: 1.4;
}
.wb-analysis-tag:hover { border-color: #C7D2FE; background: #EEF2FF; }
.wb-analysis-tag.active {
  background: #6366F1; color: #fff; border-color: #6366F1;
  font-weight: 500;
}
.wb-analysis-path-item {
  padding: 2px 8px; font-size: 11px; border-radius: 10px;
  cursor: pointer; border: 1px solid #E2E8F0; background: #fff;
  color: #47556B; transition: all 0.15s;
}
.wb-analysis-path-item:hover { border-color: #A78BFA; background: #F5F3FF; }
.wb-analysis-path-item.active {
  background: #8B5CF6; color: #fff; border-color: #8B5CF6; font-weight: 500;
}

/* 价值评分/置信度进度条区 */
.wb-score-bar { margin-top: 2px; width: 100%; }
.wb-score-bar :deep(.el-progress-bar__outer) { height: 6px !important; }
.wb-score-label {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 10px; margin-top: 2px;
}
.wb-score-level { font-weight: 600; }
.wb-score-hint {
  font-size: 9px; color: #EF4444;
  padding: 1px 5px; background: #FEF2F2; border-radius: 3px;
  display: inline-block;
}

/* 工单按钮 */
.wb-action-ticket {
  background: #8B5CF6 !important; border-color: #8B5CF6 !important;
  color: #fff !important;
}
.wb-action-ticket:hover {
  background: #7C3AED !important; border-color: #7C3AED !important;
}

/* AI气泡置信度标签 */
.wb-ai-confidence {
  font-size: 10px; padding: 1px 6px; border-radius: 8px;
  font-weight: 500; margin-left: 4px;
}
.wb-ai-confidence.conf-high { background: #D1FAE5; color: #059669; }
.wb-ai-confidence.conf-mid { background: #FEF3C7; color: #D97706; }
.wb-ai-confidence.conf-low { background: #FED7AA; color: #EA580C; }
.wb-ai-confidence.conf-none { background: #FEE2E2; color: #DC2626; }
</style>