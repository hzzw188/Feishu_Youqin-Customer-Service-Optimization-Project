import api from './index'

export interface AuthUser {
  id: number
  username: string
  created_at?: string
}

export interface LoginResult {
  success: boolean
  message: string
  token: string
  user: AuthUser
}

export const authAPI = {
  login(username: string, password: string) {
    return api.post('/auth/login', { username, password }) as Promise<LoginResult>
  },
  register(username: string, password: string) {
    return api.post('/auth/register', { username, password }) as Promise<{
      success: boolean
      message: string
      user: AuthUser
    }>
  },
}
