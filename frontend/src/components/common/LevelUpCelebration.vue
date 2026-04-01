<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import LevelBadge from '@/components/common/LevelBadge.vue'

type CelebrationEvent = {
  id: number
  fromLevel: number
  toLevel: number
  spent: number
  createdAt: number
}

type Particle = {
  id: string
  left: string
  size: string
  delay: string
  duration: string
  drift: string
  hue: string
  opacity: string
}

type Comet = {
  id: string
  top: string
  delay: string
  duration: string
  length: string
  rotate: string
}

const userStore = useUserStore()
const { levelUpEvents } = storeToRefs(userStore)

const activeEvent = ref<CelebrationEvent | null>(null)
const visible = ref(false)
const particles = ref<Particle[]>([])
const rays = ref<number[]>([])
const comets = ref<Comet[]>([])

let autoCloseTimer: number | undefined
let nextPlaybackTimer: number | undefined

const effectTier = computed(() => {
  const level = activeEvent.value?.toLevel ?? 0
  if (level >= 60) return 4
  if (level >= 35) return 3
  if (level >= 15) return 2
  return 1
})

const celebrationText = computed(() => {
  if (effectTier.value >= 4) return '传奇晋升解锁'
  if (effectTier.value >= 3) return '华丽升级'
  if (effectTier.value >= 2) return '继续冲刺'
  return '升级成功'
})

const displaySpent = computed(() => Number(activeEvent.value?.spent || 0).toLocaleString())

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

function createParticles(level: number): Particle[] {
  const tier = level >= 60 ? 4 : level >= 35 ? 3 : level >= 15 ? 2 : 1
  const count = tier === 4 ? 120 : tier === 3 ? 86 : tier === 2 ? 58 : 36
  return Array.from({ length: count }).map((_, index) => ({
    id: `${Date.now()}-${index}`,
    left: `${rand(-5, 105)}%`,
    size: `${rand(4, 13)}px`,
    delay: `${rand(0, 0.65)}s`,
    duration: `${rand(2.3, 4.8)}s`,
    drift: `${rand(-55, 55)}px`,
    hue: `${Math.random() > 0.55 ? rand(22, 58) : rand(316, 346)}`,
    opacity: `${rand(0.45, 0.96)}`,
  }))
}

function createRays(level: number): number[] {
  const tier = level >= 60 ? 4 : level >= 35 ? 3 : level >= 15 ? 2 : 1
  const count = tier === 4 ? 24 : tier === 3 ? 18 : tier === 2 ? 12 : 8
  return Array.from({ length: count }, (_, i) => i)
}

function createComets(level: number): Comet[] {
  if (level < 60) return []
  return Array.from({ length: 9 }).map((_, index) => ({
    id: `${Date.now()}-${index}`,
    top: `${rand(6, 46)}%`,
    delay: `${rand(0.1, 1.4)}s`,
    duration: `${rand(1.2, 2)}s`,
    length: `${rand(70, 130)}px`,
    rotate: `${rand(10, 23)}deg`,
  }))
}

function resetTimers(): void {
  if (autoCloseTimer) {
    window.clearTimeout(autoCloseTimer)
    autoCloseTimer = undefined
  }
  if (nextPlaybackTimer) {
    window.clearTimeout(nextPlaybackTimer)
    nextPlaybackTimer = undefined
  }
}

function prepareEffect(event: CelebrationEvent): void {
  particles.value = createParticles(event.toLevel)
  rays.value = createRays(event.toLevel)
  comets.value = createComets(event.toLevel)
}

function playNext(): void {
  if (visible.value || activeEvent.value) return
  const next = userStore.consumeNextLevelUpEvent() as CelebrationEvent | null
  if (!next) return

  activeEvent.value = next
  prepareEffect(next)
  visible.value = true

  resetTimers()
  autoCloseTimer = window.setTimeout(() => {
    closeNow()
  }, 4400)
}

function closeNow(): void {
  if (!visible.value) return
  if (activeEvent.value) {
    userStore.acknowledgeLevel(activeEvent.value.toLevel)
  }
  visible.value = false
  resetTimers()
  nextPlaybackTimer = window.setTimeout(() => {
    activeEvent.value = null
    particles.value = []
    rays.value = []
    comets.value = []
    playNext()
  }, 360)
}

watch(
  () => levelUpEvents.value.length,
  () => {
    playNext()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  resetTimers()
})
</script>

<template>
  <Transition name="level-up-screen">
    <section
      v-if="visible && activeEvent"
      class="level-up"
      :class="`level-up--tier-${effectTier}`"
      @click="closeNow"
    >
      <div class="level-up__backdrop" />
      <div v-if="effectTier >= 3" class="level-up__aurora" />

      <div class="level-up__rays">
        <span
          v-for="ray in rays"
          :key="`ray-${ray}`"
          class="level-up__ray"
          :style="{
            transform: `translate(-50%, -50%) rotate(${(ray * 360) / rays.length}deg)`,
            animationDelay: `${ray * 0.04}s`,
          }"
        />
      </div>

      <div class="level-up__particle-layer" aria-hidden="true">
        <span
          v-for="particle in particles"
          :key="particle.id"
          class="level-up__particle"
          :style="{
            left: particle.left,
            width: particle.size,
            height: particle.size,
            animationDelay: particle.delay,
            animationDuration: particle.duration,
            '--drift': particle.drift,
            '--hue': particle.hue,
            '--opacity': particle.opacity,
          }"
        />
      </div>

      <div v-if="comets.length" class="level-up__comet-layer" aria-hidden="true">
        <span
          v-for="comet in comets"
          :key="comet.id"
          class="level-up__comet"
          :style="{
            top: comet.top,
            width: comet.length,
            animationDelay: comet.delay,
            animationDuration: comet.duration,
            '--angle': comet.rotate,
          }"
        />
      </div>

      <div class="level-up__pulse level-up__pulse--outer" />
      <div class="level-up__pulse level-up__pulse--inner" />

      <article class="level-up__content" @click.stop>
        <p class="level-up__tag">{{ celebrationText }}</p>
        <h2 class="level-up__title">恭喜升级到 Lv.{{ activeEvent.toLevel }}</h2>
        <LevelBadge :level="activeEvent.toLevel" size="md" />
        <p class="level-up__meta">从 Lv.{{ activeEvent.fromLevel }} 晋升</p>
        <p class="level-up__meta">累计消费 {{ displaySpent }} 钻石</p>
        <button type="button" class="level-up__btn" @click="closeNow">
          收下祝贺
        </button>
      </article>
    </section>
  </Transition>
</template>

<style lang="scss" scoped>
.level-up {
  position: fixed;
  inset: 0;
  z-index: 1300;
  overflow: hidden;
  display: grid;
  place-items: center;
  isolation: isolate;
}

.level-up__backdrop {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 16% 20%, rgba(255, 205, 232, 0.34), transparent 42%),
    radial-gradient(circle at 82% 24%, rgba(166, 225, 255, 0.24), transparent 38%),
    radial-gradient(circle at 50% 88%, rgba(255, 164, 198, 0.26), transparent 42%),
    rgba(9, 10, 21, 0.87);
  backdrop-filter: blur(4px);
  animation: backdropPulse 3s ease-in-out infinite;
}

.level-up__aurora {
  position: absolute;
  width: min(160vw, 1400px);
  height: min(95vw, 760px);
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    rgba(247, 147, 196, 0.32),
    rgba(159, 207, 255, 0.26),
    rgba(255, 218, 169, 0.32),
    rgba(247, 147, 196, 0.32)
  );
  filter: blur(36px);
  animation: auroraSpin 8s linear infinite;
}

.level-up__rays {
  position: absolute;
  inset: 0;
}

.level-up__ray {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(72vw, 860px);
  height: 2px;
  transform-origin: left center;
  background: linear-gradient(90deg, rgba(255, 220, 241, 0.72), rgba(255, 220, 241, 0));
  opacity: 0.22;
  animation: rayFlash 2s ease-in-out infinite;
}

.level-up__particle-layer,
.level-up__comet-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.level-up__particle {
  position: absolute;
  bottom: -8vh;
  border-radius: 999px;
  background: hsla(var(--hue), 92%, 72%, var(--opacity));
  filter: drop-shadow(0 0 12px rgba(255, 176, 223, 0.65));
  animation-name: particleFloat;
  animation-timing-function: ease-out;
  animation-iteration-count: infinite;
}

.level-up__comet {
  position: absolute;
  right: -12%;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(255, 244, 251, 0.9), rgba(255, 244, 251, 0));
  box-shadow: 0 0 14px rgba(255, 244, 251, 0.55);
  animation: cometFly linear infinite;
}

.level-up__pulse {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(255, 224, 246, 0.45);
  animation: pulseRing 2.8s ease-out infinite;
}

.level-up__pulse--outer {
  width: min(86vw, 800px);
  height: min(86vw, 800px);
}

.level-up__pulse--inner {
  width: min(62vw, 560px);
  height: min(62vw, 560px);
  animation-delay: 0.28s;
}

.level-up__content {
  position: relative;
  z-index: 2;
  width: min(92vw, 500px);
  text-align: center;
  color: #fff7fb;
  background: linear-gradient(160deg, rgba(50, 24, 44, 0.8), rgba(30, 36, 66, 0.72));
  border: 1px solid rgba(255, 238, 249, 0.34);
  border-radius: 28px;
  padding: 32px 24px 28px;
  box-shadow:
    0 24px 64px rgba(6, 10, 28, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.06) inset;
  backdrop-filter: blur(8px);
  animation: cardRise 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.level-up__tag {
  margin: 0;
  font-size: 0.82rem;
  letter-spacing: 0.17em;
  text-transform: uppercase;
  color: rgba(255, 219, 243, 0.95);
}

.level-up__title {
  margin: 10px 0 16px;
  font-size: clamp(1.35rem, 2.6vw, 1.9rem);
  line-height: 1.2;
  font-weight: 700;
}

.level-up__meta {
  margin: 8px 0 0;
  color: rgba(248, 233, 245, 0.92);
  font-size: 0.95rem;
}

.level-up__btn {
  margin-top: 20px;
  border: 0;
  border-radius: 999px;
  padding: 10px 18px;
  color: #402139;
  font-weight: 700;
  background: linear-gradient(135deg, #ffd9ef, #ffe8c0);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.level-up__btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(255, 196, 229, 0.35);
}

.level-up--tier-1 {
  .level-up__ray {
    opacity: 0.12;
  }
}

.level-up--tier-2 {
  .level-up__ray {
    opacity: 0.2;
  }
}

.level-up--tier-3 {
  .level-up__ray {
    opacity: 0.26;
  }
}

.level-up--tier-4 {
  .level-up__ray {
    opacity: 0.32;
  }
}

.level-up-screen-enter-active,
.level-up-screen-leave-active {
  transition: opacity 0.32s ease;
}

.level-up-screen-enter-from,
.level-up-screen-leave-to {
  opacity: 0;
}

@keyframes cardRise {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes backdropPulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.92;
  }
}

@keyframes rayFlash {
  0%,
  100% {
    opacity: 0.06;
  }
  45% {
    opacity: 0.34;
  }
}

@keyframes auroraSpin {
  from {
    transform: rotate(0deg) scale(0.94);
  }
  to {
    transform: rotate(360deg) scale(0.98);
  }
}

@keyframes particleFloat {
  0% {
    transform: translate3d(0, 0, 0) scale(0.35);
    opacity: 0;
  }
  12% {
    opacity: 1;
  }
  100% {
    transform: translate3d(var(--drift), -112vh, 0) scale(1.08);
    opacity: 0;
  }
}

@keyframes pulseRing {
  0% {
    opacity: 0.32;
    transform: translate(-50%, -50%) scale(0.88);
  }
  100% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(1.16);
  }
}

@keyframes cometFly {
  0% {
    transform: translate3d(0, 0, 0) rotate(var(--angle, 12deg));
    opacity: 0;
  }
  12% {
    opacity: 1;
  }
  100% {
    transform: translate3d(-130vw, 38vh, 0) rotate(var(--angle, 12deg));
    opacity: 0;
  }
}

@media (max-width: 768px) {
  .level-up__content {
    padding: 28px 20px 24px;
    border-radius: 22px;
  }

  .level-up__btn {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .level-up *,
  .level-up *::before,
  .level-up *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
}
</style>
