import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI, type AuthUser } from '../api/auth'

const TOKEN_KEY = 'youqin_token'
const USER_KEY = 'youqin_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<AuthUser | null>(
    (() => {
      try {
        const raw = localStorage.getItem(USER_KEY)
        return raw ? JSON.parse(raw) : null
      } catch {
        return null
      }
    })()
  )

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const res = await authAPI.login(username, password)
    token.value = res.token
    user.value = res.user
    localStorage.setItem(TOKEN_KEY, res.token)
    localStorage.setItem(USER_KEY, JSON.stringify(res.user))
    return res
  }

  async function register(username: string, password: string) {
    return await authAPI.register(username, password)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, isLoggedIn, login, register, logout }
})
