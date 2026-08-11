<template>
  <div class="cockpit-page">
    <!-- Header 顶部导航（和工作台一致） -->
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

    <!-- Content -->
    <div class="cockpit-content">
      <!-- 顶部：标题 + 周期选择 -->
      <div class="cp-top-bar">
        <div class="cp-top-left">
          <h2 class="cp-title">利润驾驶舱</h2>
          <p class="cp-subtitle">数据更新时间：{{ updateTime }} · <i class="cp-live-dot"></i>实时监控中</p>
        </div>
        <div class="cp-top-right">
          <el-select v-model="store.currentPeriod" @change="onPeriodChange" size="default" class="cp-period">
            <el-option label="近30天" value="30d" />
            <el-option label="近7天" value="7d" />
            <el-option label="今日" value="today" />
            <el-option label="618大促周期" value="618" />
          </el-select>
          <el-button type="primary" @click="openFeishuDialog" :icon="Link">同步到飞书</el-button>
        </div>
      </div>

      <!-- 空数据占位 -->
      <div v-if="kpiList.length === 0 && !store.loading" class="cp-empty">
        <el-icon :size="48" color="#CBD5E1"><TrendCharts /></el-icon>
        <p>暂无会话数据</p>
        <p class="cp-empty-hint">前往客服工作台发起会话后，此处将自动展示实时数据</p>
        <el-button type="primary" @click="$router.push('/workbench')">前往工作台</el-button>
      </div>

      <template v-else>
        <!-- KPI Cards（4列 x 1行，共4张） -->
        <div class="cp-kpi-grid" v-loading="store.loading">
          <div
            v-for="(kpi, idx) in kpiList"
            :key="kpi.id"
            :class="['cp-kpi', `cp-kpi-${idx % 4}`]"
            :style="{ animationDelay: idx * 0.06 + 's' }"
          >
            <div class="cp-kpi-side"></div>
            <div class="cp-kpi-body">
              <div class="cp-kpi-head">
                <span class="cp-kpi-name">{{ kpi.name }}</span>
                <span class="cp-kpi-icon">
                  <el-icon><component :is="kpiIcon(idx)" /></el-icon>
                </span>
              </div>
              <div class="cp-kpi-value">
                <span class="cp-kpi-num">{{ kpi.value }}</span>
                <span v-if="kpi.unit" class="cp-kpi-unit">{{ kpi.unit }}</span>
              </div>
              <div class="cp-kpi-foot">
                <span :class="['cp-kpi-trend', trendClass(kpi.trend_class)]">{{ kpi.trend_text }} 较上月</span>
                <span class="cp-kpi-desc">{{ kpi.desc }}</span>
              </div>
              <div v-if="kpi.progress > 0" class="cp-kpi-progress">
                <el-progress :percentage="kpi.progress" :color="progressColor(kpi.progress_color)" :stroke-width="6" :show-text="false" />
              </div>
            </div>
          </div>
        </div>

        <!-- 图表行：左咨询量柱状+解决率折线（综合） / 右 Top 高频问题 -->
        <div class="cp-chart-row">
          <div class="cp-card cp-chart-card cp-chart-wide">
            <div class="cp-card-head">
              <div>
                <div class="cp-card-title-main">近7日咨询量与 AI 解决率趋势</div>
                <div class="cp-card-title-sub">会话量统计与 AI 自助解决百分比</div>
              </div>
              <div class="cp-chart-legend">
                <span class="cp-legend-item"><i class="dot dot-bar"></i>总会话量</span>
                <span class="cp-legend-item"><i class="dot dot-line"></i>AI解决率</span>
              </div>
            </div>
            <div ref="trendChartRef" class="cp-chart-canvas"></div>
          </div>

          <div class="cp-card cp-chart-card cp-chart-narrow">
            <div class="cp-card-head">
              <div>
                <div class="cp-card-title-main">Top 高频问题</div>
                <div class="cp-card-title-sub">按本月咨询次数排序</div>
              </div>
            </div>
            <div v-if="questionList.length" class="cp-question-list">
              <div v-for="q in questionList" :key="q.rank" class="cp-question-item">
                <span :class="['cp-qrank', qRankClass(q.rank)]">{{ q.rank }}</span>
                <div class="cp-qbody">
                  <div class="cp-qtext">{{ q.question }}</div>
                  <el-progress :percentage="q.progress" :color="qColor(q.color)" :stroke-width="6" :show-text="false" />
                </div>
                <span class="cp-qcount">{{ q.count.toLocaleString() }}</span>
              </div>
            </div>
            <div v-else class="cp-nodata">暂无高频问题数据</div>
          </div>
        </div>

        <!-- 3 张分布卡：意图 / 满意度 / 时段分布 -->
        <div class="cp-dist-row">
          <!-- 用户意图分布 -->
          <div class="cp-card cp-dist-card">
            <div class="cp-card-head">
              <div>
                <div class="cp-card-title-main">用户意图分布</div>
                <div class="cp-card-title-sub">基于 Top 高频问题分类</div>
              </div>
            </div>
            <div class="cp-dist-list">
              <div v-for="(q, idx) in questionList.slice(0, 5)" :key="q.rank" class="cp-dist-item">
                <div class="cp-dist-head">
                  <span class="cp-dist-legend">
                    <i class="legend-dot" :style="{ background: qColor(q.color) }"></i>
                    {{ q.question }}
                  </span>
                  <span class="cp-dist-value" :style="{ color: qColor(q.color) }">{{ q.progress }}%</span>
                </div>
                <div class="cp-dist-bar-track">
                  <div
                    class="cp-dist-bar-fill"
                    :style="{
                      width: q.progress + '%',
                      background: `linear-gradient(90deg, ${qColorHex(q.color)}33 0%, ${qColorHex(q.color)} 100%)`,
                    }"
                  ></div>
                </div>
              </div>
              <div v-if="questionList.length === 0" class="cp-nodata">暂无意图数据</div>
            </div>
          </div>

          <!-- 用户满意度分布 -->
          <div class="cp-card cp-dist-card">
            <div class="cp-card-head">
              <div>
                <div class="cp-card-title-main">用户满意度分布</div>
                <div class="cp-card-title-sub">基于会话评分统计</div>
              </div>
            </div>
            <div class="cp-dist-list">
              <div v-for="(row, idx) in csatRows" :key="row.label" class="cp-dist-item">
                <div class="cp-dist-head">
                  <span class="cp-dist-label">{{ row.label }}</span>
                  <span class="cp-dist-value" :style="{ color: csatColors[idx] }">{{ row.value }}%</span>
                </div>
                <div class="cp-dist-bar-track">
                  <div
                    class="cp-dist-bar-fill"
                    :style="{
                      width: row.value + '%',
                      background: `linear-gradient(90deg, ${csatColors[idx]}33 0%, ${csatColors[idx]} 100%)`,
                    }"
                  ></div>
                </div>
              </div>
              <div class="cp-csat-box">
                <div class="cp-csat-label">整体满意率</div>
                <div class="cp-csat-value">{{ csatTotal }}%</div>
              </div>
            </div>
          </div>

          <!-- 会话时段分布 -->
          <div class="cp-card cp-dist-card">
            <div class="cp-card-head">
              <div>
                <div class="cp-card-title-main">会话时段分布</div>
                <div class="cp-card-title-sub">近7日按小时汇总</div>
              </div>
            </div>
            <div ref="hourChartRef" class="cp-chart-canvas cp-histogram"></div>
          </div>
        </div>

        <!-- 归因明细表（完全取后端 attributions，和控制台 1:1） -->
        <div class="cp-card cp-table-card">
          <div class="cp-card-head">
            <div>
              <div class="cp-card-title-main">客服动作归因明细</div>
              <div class="cp-card-title-sub">基于真实会话与订单数据 · 含 A/B 对照标记</div>
            </div>
            <span class="cp-table-tip">共 {{ attributionList.length }} 条</span>
          </div>
          <el-table
            :data="attributionList"
            stripe
            style="width: 100%"
            size="default"
            :header-cell-style="{ background: '#F7F8FA', color: '#475569', fontWeight: 600, fontSize: '12px' }"
            :cell-style="{ fontSize: '13px', color: '#1E293B' }"
          >
            <el-table-column prop="session_id" label="会话ID" min-width="160" />
            <el-table-column prop="event_type" label="事件类型" min-width="120" />
            <el-table-column prop="event_amount" label="事件金额" min-width="100" align="right" />
            <el-table-column prop="attrib_window" label="归因窗口" min-width="100" align="center" />
            <el-table-column prop="confidence" label="置信度" min-width="100" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="row.confidence === '确定' ? 'success' : row.confidence === '高' ? 'primary' : row.confidence === '中' ? 'warning' : 'info'"
                  size="small"
                  effect="light"
                >
                  {{ row.confidence }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="increment_value" label="增量价值" min-width="120" align="right">
              <template #default="{ row }">
                <span
                  :style="{
                    color: row.increment_value.startsWith('+')
                      ? '#10B981'
                      : row.increment_value.startsWith('-')
                      ? '#EF4444'
                      : '#94A3B8',
                    fontWeight: 600,
                  }"
                >
                  {{ row.increment_value }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="group" label="分组" min-width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.group === '实验组' ? 'primary' : 'info'" size="small" effect="plain">
                  {{ row.group }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </div>

    <!-- 飞书同步对话框 -->
    <el-dialog v-model="feishuDialogVisible" title="同步数据到飞书多维表格" width="640px">
      <div v-loading="feishuLoading">
        <div class="feishu-status-card">
          <div class="status-row">
            <span class="status-label">对接状态：</span>
            <el-tag :type="feishuStatus.configured ? 'success' : 'info'" size="small">
              {{ feishuStatus.configured ? '已配置凭证' : '未配置凭证（Mock模式）' }}
            </el-tag>
          </div>
          <div class="status-row" v-if="feishuStatus.app_id">
            <span class="status-label">App ID：</span>
            <code>{{ feishuStatus.app_id }}</code>
          </div>
          <div class="status-row">
            <span class="status-label">运行模式：</span>
            <span>{{ feishuStatus.mode === 'real' ? '真实对接' : 'Mock降级' }}</span>
          </div>
          <div class="status-row" v-if="feishuStatus.message">
            <span class="status-label">说明：</span>
            <span style="color: #94A3B8; font-size: 12px;">{{ feishuStatus.message }}</span>
          </div>
        </div>
        <div class="feishu-actions">
          <el-button type="primary" @click="initBitable" :loading="initLoading">1. 创建多维表格</el-button>
          <el-button type="success" @click="syncAll" :loading="syncLoading">2. 一键同步全部数据</el-button>
        </div>
        <div v-if="syncResult" class="sync-result">
          <el-alert
            :title="syncResult.message || '同步完成'"
            :type="syncResult.success ? 'success' : 'error'"
            :description="syncResult.details ? `会话: ${syncResult.details.sessions?.synced_count || 0}条 / 消息: ${syncResult.details.messages?.synced_count || 0}条 / KPI: ${syncResult.details.kpi?.synced_count || 0}条` : ''"
            show-icon
            :closable="false"
          />
        </div>
        <div v-if="feishuStatus.app_token" class="view-bitable-link">
          <el-link type="primary" :href="`https://feishu.cn/base/${feishuStatus.app_token}`" target="_blank">
            <el-icon><Link /></el-icon>点击查看飞书多维表格 →
          </el-link>
        </div>
        <el-divider content-position="left">同步的数据表（8张）</el-divider>
        <div class="tables-guide">
          <div class="table-item"><div class="table-name">👤 用户表</div></div>
          <div class="table-item"><div class="table-name">📦 商品表</div></div>
          <div class="table-item"><div class="table-name">📋 会话表</div></div>
          <div class="table-item"><div class="table-name">🧾 订单表</div></div>
          <div class="table-item"><div class="table-name">🤝 客服动作表</div></div>
          <div class="table-item"><div class="table-name">🎯 结果事件表</div></div>
          <div class="table-item"><div class="table-name">💬 聊天消息表</div></div>
          <div class="table-item"><div class="table-name">📊 KPI驾驶舱指标表</div></div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Headset, Odometer, Bell, UserFilled,
  TrendCharts, Link, MagicStick, Timer, Star, Money,
  Connection, ChatDotRound,
} from '@element-plus/icons-vue'
import type { Component } from 'vue'
import { useCockpitStore } from '../stores/cockpit'
import { useAuthStore } from '../stores/auth'
import * as echarts from 'echarts'

const store = useCockpitStore()
const authStore = useAuthStore()
const router = useRouter()

const trendChartRef = ref<HTMLElement | null>(null)
const hourChartRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let hourChart: echarts.ECharts | null = null

const updateTime = ref(new Date().toLocaleString('zh-CN', { hour12: false }))

// ========= 数据 1:1 绑定后端 summary =========
const kpiList = computed(() => store.summary?.kpis || [])
const trendList = computed(() => store.summary?.trends || [])
const questionList = computed(() => store.summary?.top_questions || [])
const attributionList = computed(() => store.summary?.attributions || [])

// KPI 图标（6个，按索引对应）
const iconPool: Component[] = [MagicStick, Timer, Star, Money, Connection, ChatDotRound]
function kpiIcon(idx: number) {
  return iconPool[idx % iconPool.length]
}

function trendClass(c: string): 'up' | 'down' | 'flat' {
  if (!c) return 'flat'
  if (c.includes('green')) return 'up'
  if (c.includes('warn') || c.includes('orange') || c.includes('danger') || c.includes('red')) return 'down'
  return 'flat'
}

function progressColor(c: string) {
  if (!c) return '#2563EB'
  if (c.includes('success')) return '#10B981'
  if (c.includes('primary')) return '#2563EB'
  if (c.includes('warning')) return '#F59E0B'
  if (c.includes('danger')) return '#EF4444'
  if (c.includes('purple')) return '#8B5CF6'
  return '#2563EB'
}

function qRankClass(rank: number) {
  if (rank === 1) return 'rank-1'
  if (rank === 2) return 'rank-2'
  if (rank === 3) return 'rank-3'
  return 'rank-other'
}

function qColor(c: string) {
  if (!c) return '#2563EB'
  if (c.includes('danger')) return '#EF4444'
  if (c.includes('warning')) return '#F59E0B'
  if (c.includes('primary')) return '#2563EB'
  if (c.includes('success')) return '#10B981'
  if (c.includes('purple')) return '#8B5CF6'
  return '#94A3B8'
}

function qColorHex(c: string): string {
  const v = qColor(c)
  if (v.startsWith('#')) return v
  return '#2563EB'
}

// CSAT 满意度分布：优先用后端真实数据（基于会话解决状态推算）
const csatRows = computed(() => {
  const backendCsat = store.summary?.csat
  if (backendCsat && backendCsat.length > 0) {
    return backendCsat
  }
  // 后端无数据时的兜底
  return [
    { label: '非常满意', value: 0 },
    { label: '满意', value: 0 },
    { label: '一般', value: 0 },
    { label: '不满意', value: 0 },
    { label: '非常不满意', value: 0 },
  ]
})
const csatColors = ['#10B981', '#3CCFA7', '#F59E0B', '#F97316', '#EF4444']
const csatTotal = computed(() => csatRows.value[0].value + csatRows.value[1].value)

// ========= 图表 1：咨询量柱 + AI解决率折线 =========
function initTrendChart() {
  if (!trendChartRef.value) return
  if (trendChart) trendChart.dispose()
  trendChart = echarts.init(trendChartRef.value)

  const trends = trendList.value
  const dates = trends.length ? trends.map(t => t.date_label) : ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24']
  const sessions = trends.length ? trends.map(t => t.session_count) : [82, 96, 110, 128, 142, 158, 172]
  const resolve = trends.length ? trends.map(t => t.ai_resolve_rate) : [76, 78.5, 80.2, 79.8, 82.1, 83, 84.6]

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0F172A',
      borderColor: 'transparent',
      textStyle: { color: '#fff', fontSize: 12 },
      axisPointer: { type: 'cross' },
    },
    legend: { show: false },
    grid: { left: 50, right: 60, top: 16, bottom: 24 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisTick: { show: false },
      axisLabel: { color: '#64748B', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        name: '会话量',
        nameTextStyle: { color: '#94A3B8', fontSize: 11 },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
        axisLabel: { color: '#64748B', fontSize: 11 },
      },
      {
        type: 'value',
        name: 'AI解决率(%)',
        nameTextStyle: { color: '#94A3B8', fontSize: 11 },
        min: 50,
        max: 100,
        splitLine: { show: false },
        axisLabel: { color: '#64748B', fontSize: 11, formatter: '{value}%' },
      },
    ],
    series: [
      {
        name: '总会话量',
        type: 'bar',
        data: sessions,
        barWidth: 34,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#60A5FA' },
            { offset: 1, color: '#DBEAFE' },
          ]),
        },
      },
      {
        name: 'AI解决率',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: resolve,
        lineStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#10B981' },
            { offset: 1, color: '#2563EB' },
          ]),
          width: 3,
        },
        itemStyle: { color: '#10B981', borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16,185,129,0.18)' },
            { offset: 1, color: 'rgba(16,185,129,0.00)' },
          ]),
        },
      },
    ],
  })
}

// ========= 图表 2：时段分布柱状（真实小时数据） =========
function initHourChart() {
  if (!hourChartRef.value) return
  if (hourChart) hourChart.dispose()
  hourChart = echarts.init(hourChartRef.value)

  const hourlyData = store.summary?.hourly || []
  const hours = hourlyData.map(h => h.hour)
  const counts = hourlyData.map(h => h.count)

  hourChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0F172A', borderColor: 'transparent',
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (params: any) => `${params[0].axisValue}点<br/>会话数：${params[0].data} 个`,
    },
    grid: { left: 36, right: 10, top: 10, bottom: 22 },
    xAxis: {
      type: 'category',
      data: hours,
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisTick: { show: false },
      axisLabel: { color: '#64748B', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#64748B', fontSize: 10 },
      splitLine: { lineStyle: { color: '#F1F5F9' } },
    },
    series: [
      {
        type: 'bar',
        data: counts,
        barWidth: 14,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#F59E0B' },
            { offset: 1, color: '#FDE68A' },
          ]),
        },
      },
    ],
  })
}

// ========= 飞书同步（保留原有逻辑） =========
const feishuDialogVisible = ref(false)
const feishuLoading = ref(false)
const initLoading = ref(false)
const syncLoading = ref(false)
const feishuStatus = ref<any>({ configured: false, mode: 'mock' })
const syncResult = ref<any>(null)

async function openFeishuDialog() {
  feishuDialogVisible.value = true
  syncResult.value = null
  await fetchFeishuStatus()
}

// 飞书 API 基础路径：云部署用 VITE_API_BASE，本地开发用 /api
const apiBase = import.meta.env.VITE_API_BASE || '/api'

async function fetchFeishuStatus() {
  feishuLoading.value = true
  try {
    const res = await fetch(`${apiBase}/feishu/status`)
    feishuStatus.value = await res.json()
  } catch (e) {
    feishuStatus.value = { configured: false, mode: 'mock', message: '后端服务未启动' }
  } finally {
    feishuLoading.value = false
  }
}

async function initBitable() {
  initLoading.value = true
  try {
    const res = await fetch(`${apiBase}/feishu/bitable/init-browser`)
    const data = await res.json()
    if (data.success) {
      ElMessage.success(`✅ ${data.message}`)
      if (data.app_token) {
        ElMessage.info(`多维表格 app_token: ${data.app_token.slice(0, 12)}...，请保存到 .env 文件`)
      }
    } else {
      ElMessage.error(data.message || '创建失败')
    }
  } catch (e: any) {
    ElMessage.error('请求失败: ' + e.message)
  } finally {
    initLoading.value = false
  }
}

async function syncAll() {
  syncLoading.value = true
  syncResult.value = null
  try {
    const res = await fetch(`${apiBase}/feishu/bitable/sync-all-browser`)
    syncResult.value = await res.json()
    if (syncResult.value.success) {
      ElMessage.success(syncResult.value.message || '同步完成')
    } else {
      ElMessage.warning(syncResult.value.message || '同步失败')
    }
  } catch (e: any) {
    ElMessage.error('请求失败: ' + e.message)
    syncResult.value = { success: false, message: '请求失败: ' + e.message }
  } finally {
    syncLoading.value = false
  }
}

watch(
  () => store.summary,
  () => {
    nextTick(() => {
      initTrendChart()
      initHourChart()
    })
  },
)

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

// 切换统计周期时：立即刷新 + 重置 30s 轮询
async function onPeriodChange(period: string) {
  stopRefreshLoop()
  await store.fetchSummary(period)
  updateTime.value = new Date().toLocaleString('zh-CN', { hour12: false })
  startRefreshLoop()
}

// 30s 实时轮询 + 时间戳更新（驾驶舱动态刷新效果）
let refreshTimer: any = null
let tickTimer: any = null
function startRefreshLoop() {
  stopRefreshLoop()
  refreshTimer = setInterval(async () => {
    try {
      await store.fetchSummary(store.currentPeriod)
      updateTime.value = new Date().toLocaleString('zh-CN', { hour12: false })
    } catch {
      /* ignore */
    }
  }, 30000)
  tickTimer = setInterval(() => {
    updateTime.value = new Date().toLocaleString('zh-CN', { hour12: false })
  }, 30000)
}
function stopRefreshLoop() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
  if (tickTimer) { clearInterval(tickTimer); tickTimer = null }
}

onMounted(() => {
  store.fetchSummary()
  startRefreshLoop()
})

onUnmounted(() => {
  stopRefreshLoop()
  trendChart?.dispose()
  hourChart?.dispose()
})
</script>

<style scoped>
.cockpit-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: #F7F8FA;
}

/* =============== 顶部导航（与工作台一致） =============== */
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

/* =============== 内容区（浅灰底 + 白色卡片） =============== */
.cockpit-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 32px;
}

/* 顶栏 */
.cp-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.cp-top-left { display: flex; flex-direction: column; gap: 4px; }
.cp-title { margin: 0; font-size: 22px; font-weight: 700; color: #0F172A; letter-spacing: 0.3px; }
.cp-subtitle { margin: 0; font-size: 12px; color: #94A3B8; display: inline-flex; align-items: center; gap: 6px; }
.cp-live-dot {
  width: 8px; height: 8px; display: inline-block;
  background: #10B981; border-radius: 50%;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6);
  animation: cp-live-pulse 1.6s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
@keyframes cp-live-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.55); }
  70%  { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
.cp-top-right { display: flex; align-items: center; gap: 10px; }
.cp-period { width: 140px; }

/* 空态 */
.cp-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 80px 20px; gap: 8px; color: #94A3B8;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #E2E8F0;
}
.cp-empty p { margin: 0; font-size: 14px; }
.cp-empty-hint { font-size: 12px !important; color: #CBD5E1 !important; margin-bottom: 16px !important; }

/* =============== 通用卡片 =============== */
.cp-card {
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}
.cp-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 18px 20px 10px;
}
.cp-card-title-main { font-size: 15px; font-weight: 600; color: #0F172A; }
.cp-card-title-sub { font-size: 11px; color: #94A3B8; margin-top: 4px; }
.cp-nodata {
  display: flex; align-items: center; justify-content: center;
  height: 180px; color: #94A3B8; font-size: 13px;
}

/* =============== KPI 4列 x 1行 共 4张 =============== */
.cp-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.cp-kpi {
  position: relative;
  display: flex;
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  transition: transform 0.2s, box-shadow 0.2s;
  opacity: 0;
  transform: translateY(8px);
  animation: cp-kpi-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes cp-kpi-in {
  to { opacity: 1; transform: translateY(0); }
}
.cp-kpi:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.08);
}
.cp-kpi-side {
  width: 4px; flex-shrink: 0;
  background: #2563EB;
}
.cp-kpi-0 .cp-kpi-side { background: #2563EB; }
.cp-kpi-1 .cp-kpi-side { background: #10B981; }
.cp-kpi-2 .cp-kpi-side { background: #F59E0B; }
.cp-kpi-3 .cp-kpi-side { background: #EF4444; }
.cp-kpi-4 .cp-kpi-side { background: #8B5CF6; }
.cp-kpi-5 .cp-kpi-side { background: #0EA5E9; }

.cp-kpi-body { flex: 1; padding: 8px 12px 8px 10px; min-width: 0; }
.cp-kpi-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 4px;
}
.cp-kpi-name { font-size: 12px; color: #64748B; }
.cp-kpi-icon {
  width: 20px; height: 20px; border-radius: 5px;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; flex-shrink: 0;
}
.cp-kpi-0 .cp-kpi-icon { color: #2563EB; background: #EFF4FF; }
.cp-kpi-1 .cp-kpi-icon { color: #10B981; background: #ECFDF5; }
.cp-kpi-2 .cp-kpi-icon { color: #F59E0B; background: #FFFBEB; }
.cp-kpi-3 .cp-kpi-icon { color: #EF4444; background: #FEF2F2; }
.cp-kpi-4 .cp-kpi-icon { color: #8B5CF6; background: #F5F3FF; }
.cp-kpi-5 .cp-kpi-icon { color: #0EA5E9; background: #F0F9FF; }

.cp-kpi-value {
  display: flex; align-items: baseline; gap: 4px;
  margin-bottom: 4px;
}
.cp-kpi-num { font-size: 20px; font-weight: 700; color: #0F172A; letter-spacing: 0.4px; line-height: 1.1; }
.cp-kpi-unit { font-size: 12px; color: #94A3B8; font-weight: 500; }

.cp-kpi-foot {
  display: flex; justify-content: space-between; align-items: center;
  gap: 10px; flex-wrap: wrap;
}
.cp-kpi-trend {
  display: inline-flex; align-items: center;
  padding: 2px 8px; border-radius: 999px;
  font-size: 10px; font-weight: 600;
}
.cp-kpi-trend.up   { background: #ECFDF5; color: #10B981; }
.cp-kpi-trend.down { background: #FEF2F2; color: #EF4444; }
.cp-kpi-trend.flat { background: #EFF4FF; color: #2563EB; }
.cp-kpi-desc { font-size: 10px; color: #94A3B8; }
.cp-kpi-progress { margin-top: 4px; }

/* =============== 图表大卡行 =============== */
.cp-chart-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.cp-chart-card { padding-bottom: 18px; }
.cp-chart-wide .cp-chart-canvas { height: 280px; padding: 0 16px; }
.cp-chart-narrow { padding-bottom: 14px; }

.cp-chart-legend { display: flex; gap: 16px; padding-top: 4px; }
.cp-legend-item { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #64748B; }
.cp-legend-item .dot { width: 14px; height: 10px; border-radius: 3px; display: inline-block; }
.cp-legend-item .dot-bar { background: #60A5FA; }
.cp-legend-item .dot-line {
  height: 2px; width: 18px; background: linear-gradient(90deg, #10B981, #2563EB);
  position: relative; border-radius: 2px;
}
.cp-legend-item .dot-line::after {
  content: '';
  position: absolute;
  left: 50%; top: 50%;
  width: 8px; height: 8px;
  background: #10B981;
  border: 2px solid #fff;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 1px #10B981;
}

/* Top 问题列表 */
.cp-question-list {
  padding: 4px 20px 0;
  display: flex; flex-direction: column; gap: 14px;
}
.cp-question-item {
  display: flex; align-items: center; gap: 10px;
}
.cp-qrank {
  width: 24px; height: 24px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.cp-qrank.rank-1 { background: #EF4444; }
.cp-qrank.rank-2 { background: #F59E0B; }
.cp-qrank.rank-3 { background: #2563EB; }
.cp-qrank.rank-other { background: #94A3B8; }
.cp-qbody { flex: 1; min-width: 0; }
.cp-qtext {
  font-size: 13px; color: #1E293B;
  margin-bottom: 6px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cp-qcount { font-size: 12px; color: #64748B; flex-shrink: 0; }

/* =============== 3分布卡 =============== */
.cp-dist-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.cp-dist-card { padding-bottom: 20px; }
.cp-dist-list { padding: 0 20px; display: flex; flex-direction: column; gap: 12px; }
.cp-dist-item { display: flex; flex-direction: column; gap: 6px; }
.cp-dist-head {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px;
}
.cp-dist-legend {
  display: inline-flex; align-items: center; gap: 6px;
  color: #475569;
}
.legend-dot { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }
.cp-dist-label { color: #475569; font-size: 12px; }
.cp-dist-value { font-weight: 600; font-size: 12px; }

.cp-dist-bar-track {
  width: 100%; height: 6px; border-radius: 999px;
  background: #F1F5F9;
  overflow: hidden;
}
.cp-dist-bar-fill { height: 100%; border-radius: 999px; transition: width 0.6s; }

.cp-csat-box {
  margin-top: 4px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  display: flex; justify-content: space-between; align-items: center;
}
.cp-csat-label { font-size: 12px; color: #64748B; }
.cp-csat-value { font-size: 22px; font-weight: 700; color: #10B981; }

.cp-histogram { height: 210px; padding: 0 6px; }

/* =============== 归因明细表 =============== */
.cp-table-card { overflow: hidden; margin-bottom: 24px; }
.cp-table-tip {
  font-size: 12px; color: #94A3B8; padding-top: 6px;
}

/* 飞书同步对话框 */
.feishu-status-card {
  background: #F7F8FA;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}
.status-row:last-child { margin-bottom: 0; }
.status-label { color: #94A3B8; min-width: 80px; }
.status-row code {
  background: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: #2563EB;
  border: 1px solid #E2E8F0;
}
.feishu-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.feishu-actions .el-button { flex: 1; }
.sync-result { margin-bottom: 16px; }
.view-bitable-link {
  text-align: center;
  padding: 12px 0;
  margin-bottom: 4px;
}
.view-bitable-link .el-link { font-size: 15px; font-weight: 500; }
.tables-guide { display: flex; flex-wrap: wrap; gap: 8px; }
.table-item {
  padding: 6px 12px;
  background: #F7F8FA;
  border-radius: 6px;
}
.table-name { font-weight: 500; font-size: 13px; white-space: nowrap; }
.table-desc { font-size: 12px; color: #94A3B8; }

/* 响应式：窄屏 */
@media (max-width: 1360px) {
  .cp-kpi-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 1100px) {
  .cp-chart-row { grid-template-columns: 1fr; }
  .cp-dist-row { grid-template-columns: 1fr; }
}
</style>
