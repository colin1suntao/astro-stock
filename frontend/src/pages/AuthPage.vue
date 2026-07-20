<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/api'

const email = ref('demo@astro.com')
const password = ref('secret123')
const name = ref('Demo')
const mode = ref<'login' | 'register'>('login')
const error = ref('')
const router = useRouter()
const route = useRoute()

async function submit() {
  error.value = ''
  const url = mode.value === 'login' ? '/api/auth/login' : '/api/auth/register'
  const body = mode.value === 'login'
    ? { email: email.value, password: password.value }
    : { email: email.value, password: password.value, name: name.value }
  const r = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) { error.value = `${r.status} ${await r.text()}`; return }
  const d = await r.json()
  localStorage.setItem('astro-token', d.access_token)
  localStorage.setItem('astro-user', JSON.stringify(d.user))
  // P5-4: 登录/注册成功后跳仪表盘；若有 redirect query 优先（守卫拦下时）
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
  router.push(redirect || '/dashboard')
}
</script>

<template>
  <section class="auth">
    <h1>🔐 {{ mode === 'login' ? '登录' : '注册' }}</h1>
    <div class="toggle">
      <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
      <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
    </div>
    <form @submit.prevent="submit">
      <input v-model="email" type="email" placeholder="email" required>
      <input v-if="mode === 'register'" v-model="name" placeholder="昵称" required>
      <input v-model="password" type="password" placeholder="密码" required>
      <button type="submit">{{ mode === 'login' ? '登录' : '注册' }}</button>
    </form>
    <p v-if="error" class="error">❌ {{ error }}</p>
  </section>
</template>

<style scoped>
.auth { max-width: 360px; margin: 60px auto; padding: 24px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); }
h1 { margin: 0 0 16px; }
.toggle { display: flex; gap: 8px; margin-bottom: 16px; }
.toggle button { flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface2); color: var(--text); cursor: pointer; }
.toggle button.active { background: var(--accent); color: #fff; }
form { display: flex; flex-direction: column; gap: 12px; }
input { padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); }
button[type="submit"] { padding: 10px; border: none; border-radius: 6px; background: var(--accent); color: #fff; cursor: pointer; }
.error { color: var(--danger); margin-top: 12px; }
</style>
