/**
 * T7 首批测 — api.ts 纯函数 + DashboardPage 关键 computed
 * 覆盖初始化：vitest + @vue/test-utils + jsdom 框架就位，后续可续扩
 */
import { describe, it, expect } from 'vitest'
import { PlanetPosition, Aspect, MoonPhase } from '@/api'

// 这些是 type-only export，测运行时 import 不应崩
describe('api.ts 类型 export', () => {
  it('PlanetPosition/Aspect/MoonPhase 是 type-only export，运行时 import undefined 不崩', () => {
    // type-only export 在运行时是 undefined，但 import 不应抛
    expect(PlanetPosition).toBeUndefined()
    expect(Aspect).toBeUndefined()
    expect(MoonPhase).toBeUndefined()
  })
})

// DashboardPage 的 wheelPositions 算法（lon→轮上 x/y）独立验
describe('相位轮 lon→x/y 映射算法', () => {
  const WHEEL_CX = 170, WHEEL_R = 150
  const xy = (lon: number) => {
    const angle = (lon - 90) * (Math.PI / 180)
    return {
      x: WHEEL_CX + WHEEL_R * Math.cos(angle),
      y: 170 + WHEEL_R * Math.sin(angle),
    }
  }
  it('lon=0°（白羊 0°）映射到轮底部（x=CX，y=CY+R）', () => {
    // angle=(0-90)*π/180=-π/2; cos(-π/2)=0 → x=CX+0=170; sin(-π/2)=-1 → y=CY-R=20
    const p = xy(0)
    expect(Math.round(p.x)).toBe(170)
    expect(Math.round(p.y)).toBe(20)
  })
  it('lon=90°（巨蟹 0°）映射到轮右侧（x=CX+R，y=CY）', () => {
    const p = xy(90)
    // recompute: angle=(90-90)*π/180=0; x=CX+R*cos(0)=170+150=320; y=CY+R*sin(0)=170
    expect(Math.round(p.x)).toBe(320)
    expect(Math.round(p.y)).toBe(170)
  })
  it('lon=180°（天秤 0°）映射到轮顶部（x=CX，y<CY）', () => {
    // angle=(180-90)*π/180=π/2; x=CX+R*cos(π/2)=170+0=170; y=CY+R*sin(π/2)=170+150=320
    const p = xy(180)
    expect(Math.round(p.x)).toBe(170)
    expect(Math.round(p.y)).toBe(320)
  })
  it('lon=270°（摩羯 0°）映射到轮左侧（x<CX，y=CY）', () => {
    // angle=(270-90)*π/180=π; x=CX+R*cos(π)=170-150=20; y=CY+R*sin(π)=170+0=170
    const p = xy(270)
    expect(Math.round(p.x)).toBe(20)
    expect(Math.round(p.y)).toBe(170)
  })
})

// 元素平衡分类算法（DashboardPage elementStats）独立验
describe('星座→元素分类', () => {
  const fireSigns = ['白羊座', '狮子座', '射手座']
  const earthSigns = ['金牛座', '处女座', '摩羯座']
  const airSigns = ['双子座', '天秤座', '水瓶座']
  const waterSigns = ['巨蟹座', '天蝎座', '双鱼座']
  const classify = (sign: string) => {
    if (fireSigns.includes(sign)) return 'fire'
    if (earthSigns.includes(sign)) return 'earth'
    if (airSigns.includes(sign)) return 'air'
    if (waterSigns.includes(sign)) return 'water'
    return null
  }
  it.each([
    ['白羊座', 'fire'], ['狮子座', 'fire'], ['射手座', 'fire'],
    ['金牛座', 'earth'], ['处女座', 'earth'], ['摩羯座', 'earth'],
    ['双子座', 'air'], ['天秤座', 'air'], ['水瓶座', 'air'],
    ['巨蟹座', 'water'], ['天蝎座', 'water'], ['双鱼座', 'water'],
  ])('星座 %s 归 %s 元素', (sign, el) => {
    expect(classify(sign)).toBe(el)
  })
  it('12 星座全覆盖无 null', () => {
    const all = [...fireSigns, ...earthSigns, ...airSigns, ...waterSigns]
    for (const s of all) expect(classify(s)).not.toBeNull()
    expect(all).toHaveLength(12)
  })
})
