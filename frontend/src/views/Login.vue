<template>
  <div class="login-page">
    <div class="login-card">
      <!-- Logo -->
      <div class="login-header">
        <div class="logo-text">YOUQIN</div>
        <p class="login-subtitle">优勤智服 · AI客服利润引擎</p>
      </div>

      <!-- Tabs -->
      <div class="auth-tabs">
        <button :class="['auth-tab', { active: mode === 'login' }]" @click="mode = 'login'">登录</button>
        <button :class="['auth-tab', { active: mode === 'register' }]" @click="mode = 'register'">注册</button>
      </div>

      <!-- Form -->
      <div class="auth-form">
        <div class="form-field">
          <label>用户名</label>
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            size="large"
            @keydown.enter="handleSubmit"
          />
        </div>
        <div class="form-field">
          <label>密码</label>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keydown.enter="handleSubmit"
          />
        </div>

        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          @click="handleSubmit"
        >
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>

        <!-- 测试账号提示 -->
        <div v-if="mode === 'login'" class="test-hint" @click="fillTestAccount">
          <div class="hint-title">
            <el-icon><InfoFilled /></el-icon>
            点击一键填入测试账号
          </div>
          <div class="hint-row">
            <span class="hint-label">账号</span>
            <code>admin</code>
          </div>
          <div class="hint-row">
            <span class="hint-label">密码</span>
            <code>password</code>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部品牌信息 -->
    <p class="login-footer">© 2026 优勤智服 · 让客服成为利润中心</p>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, InfoFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const mode = ref<'login' | 'register'>('login')
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

/** 一键填入测试账号 */
function fillTestAccount() {
  form.username = 'admin'
  form.password = 'password'
}

async function handleSubmit() {
  if (!form.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!form.password) {
    ElMessage.warning('请输入密码')
    return
  }

  loading.value = true
  try {
    if (mode.value === 'login') {
      await authStore.login(form.username, form.password)
      ElMessage.success('登录成功')
      router.push('/workbench')
    } else {
      await authStore.register(form.username, form.password)
      ElMessage.success('注册成功，请登录')
      mode.value = 'login'
      form.password = ''
    }
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '操作失败'
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--bg-warm);
  background-image:
    linear-gradient(rgba(37, 99, 235, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(37, 99, 235, 0.025) 1px, transparent 1px);
  background-size: 28px 28px;
}

.login-card {
  width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 40px 36px;
  box-shadow: 0 2px 24px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--border-soft);
  animation: card-rise 0.5s var(--ease-out);
}
@keyframes card-rise {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}
.login-subtitle {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-top: 8px;
  letter-spacing: 0.3px;
}

/* Tabs */
.auth-tabs {
  display: flex;
  background: var(--bg-gray);
  border-radius: 8px;
  padding: 3px;
  margin-bottom: 24px;
}
.auth-tab {
  flex: 1;
  padding: 9px 0;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  color: var(--text-tertiary);
  background: transparent;
  transition: all 0.2s;
}
.auth-tab.active {
  background: #fff;
  color: var(--primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* Form */
.form-field {
  margin-bottom: 18px;
}
.form-field label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  font-weight: 500;
}

.submit-btn {
  width: 100%;
  margin-top: 6px;
  font-size: 15px;
  letter-spacing: 2px;
}

/* 测试账号提示 */
.test-hint {
  margin-top: 24px;
  padding: 14px 16px;
  background: var(--primary-soft);
  border-radius: 8px;
  border: 1px solid var(--border-soft);
  cursor: pointer;
  transition: border-color 0.15s var(--ease-soft), background 0.15s var(--ease-soft);
}
.test-hint:hover { border-color: rgba(37, 99, 235, 0.3); background: #DBEAFE; }
.hint-title {
  font-size: 12px;
  color: var(--primary);
  font-weight: 600;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.hint-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 4px;
}
.hint-row:last-child {
  margin-bottom: 0;
}
.hint-label {
  color: var(--text-tertiary);
  min-width: 32px;
}
.hint-row code {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  color: var(--primary);
  background: #fff;
  padding: 1px 8px;
  border-radius: 3px;
}

.login-footer {
  margin-top: 32px;
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>
