import { createRouter, createWebHistory } from 'vue-router'
import Workbench from '../views/Workbench.vue'
import Cockpit from '../views/Cockpit.vue'
import Login from '../views/Login.vue'
import Server from '../views/Server.vue'

const routes = [
  { path: '/login', name: 'Login', component: Login, meta: { public: true } },
  { path: '/', redirect: '/workbench' },
  { path: '/workbench', name: 'Workbench', component: Workbench },
  { path: '/cockpit', name: 'Cockpit', component: Cockpit },
  { path: '/server', name: 'Server', component: Server, meta: { public: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录时跳转到登录页
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('youqin_token')
  if (!to.meta.public && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/workbench')
  } else {
    next()
  }
})

export default router
