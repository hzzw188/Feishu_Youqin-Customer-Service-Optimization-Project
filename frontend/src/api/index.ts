import axios from 'axios'

const api = axios.create({
  // 本地开发用 vite proxy 转发 /api，云部署通过环境变量设绝对地址
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 10000,
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('API Error:', err)
    return Promise.reject(err)
  }
)

export default api