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
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
  router.push(redirect || '/dashboard')
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-bg" />
    <div class="auth-card">
      <div class="auth-hero">
        <div class="hero-icon">🌌</div>
        <h1 class="hero-title">AstroStock</h1>
        <p class="hero-subtitle">占星股市预测系统 — 以天象推演市场趋势</p>
      </div>
      <div class="auth-form-wrap">
        <div class="toggle">
          <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
          <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        </div>
        <form @submit.prevent="submit">
          <div class="field">
            <label>邮箱</label>
            <input v-model="email" type="email" placeholder="demo@astro.com" required>
          </div>
          <div v-if="mode === 'register'" class="field">
            <label>昵称</label>
            <input v-model="name" placeholder="你的昵称" required>
          </div>
          <div class="field">
            <label>密码</label>
            <input v-model="password" type="password" placeholder="输入密码" required>
          </div>
          <button type="submit" class="submit-btn">{{ mode === 'login' ? '登录' : '注册' }}</button>
        </form>
        <p v-if="error" class="error">❌ {{ error }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #0b0e1a 0%, #1a1040 40%, #0f1a3a 70%, #0b0e1a 100%);
}
.auth-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,0.3) 0%, transparent 100%),
    radial-gradient(2px 2px at 40% 70%, rgba(255,255,255,0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 60% 20%, rgba(255,255,255,0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 80% 60%, rgba(255,255,255,0.2) 0%, transparent 100%),
    radial-gradient(2px 2px at 10% 80%, rgba(255,255,255,0.15) 0%, transparent 100%),
    radial-gradient(1px 1px at 70% 40%, rgba(255,255,255,0.25) 0%, transparent 100%),
    radial-gradient(1px 1px at 90% 10%, rgba(255,255,255,0.15) 0%, transparent 100%),
    radial-gradient(1px 1px at 30% 50%, rgba(255,255,255,0.2) 0%, transparent 100%);
  pointer-events: none;
}

.auth-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
  padding: 40px 36px;
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  box-shadow: 0 8px 48px rgba(0, 0, 0, 0.4);
}

.auth-hero {
  text-align: center;
  margin-bottom: 32px;
}
.hero-icon {
  font-size: 48px;
  margin-bottom: 12px;
  filter: drop-shadow(0 0 20px rgba(168, 139, 250, 0.4));
}
.hero-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, #a78bfa, #fde68a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-subtitle {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.5px;
}

.auth-form-wrap {
  max-width: 320px;
  margin: 0 auto;
}

.toggle {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  padding: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 10px;
}
.toggle button {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
}
.toggle button.active {
  background: rgba(167, 139, 250, 0.2);
  color: #a78bfa;
  font-weight: 600;
}

form { display: flex; flex-direction: column; gap: 18px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 12px; color: rgba(255, 255, 255, 0.4); letter-spacing: 0.5px; }
input {
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s;
}
input:focus { border-color: #a78bfa; }
input::placeholder { color: rgba(255, 255, 255, 0.2); }

.submit-btn {
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #a78bfa, #7c3aed);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.3s, transform 0.2s;
}
.submit-btn:hover { opacity: 0.9; transform: translateY(-1px); }
.submit-btn:active { transform: translateY(0); }

.error { color: #f87171; margin-top: 16px; text-align: center; font-size: 13px; }
</style>