import { defineStore } from 'pinia'

export type ThemeKey = 'dark' | 'dawn' | 'ocean' | 'golden'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    current: (localStorage.getItem('astro-theme') as ThemeKey) || 'dark',
  }),
  actions: {
    apply(next: ThemeKey) {
      this.current = next
      document.documentElement.setAttribute('data-theme', next)
      localStorage.setItem('astro-theme', next)
    },
    init() {
      this.apply(this.current)
    },
  },
})
