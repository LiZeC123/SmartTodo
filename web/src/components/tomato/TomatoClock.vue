<template>
  <div v-show="props.item">
    <h2>当前任务</h2>
    <ol>
      <audio ref="baseAudioRef" id="notificationAudioBase" :src="MusicBase"></audio>
      <audio ref="shortAudioRef" id="notificationAudioShort" :src="MusicShort"></audio>
      <li class="FOCUS">
        <span v-if="isResting">【休息中】</span>【{{ displayTimeStr }}】{{ item?.taskName }}
        <a class="function function-1" title="取消任务" @click="finishTask('undo')">
          <font-awesome-icon :icon="['fas', 'undo']" />
        </a>
        <a class="function function-0" title="完成任务" @click="finishTask('done')">
          <font-awesome-icon :icon="['fas', 'check']" />
        </a>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import MusicBase from './M01.mp3'
import MusicShort from './S01.mp3'
import { computed, onUnmounted, ref, watch } from 'vue'
import type { TomatoEventType, TomatoItem, TomatoParam } from './types'

const WORK_MINUTES = 25
const REST_MINUTES = 5
const WORK_SECONDS = WORK_MINUTES * 60
const CYCLE_SECONDS = (WORK_MINUTES + REST_MINUTES) * 60

const props = defineProps<{
  item?: TomatoItem
}>()

const emit = defineEmits<{
  (e: 'done-task', type: TomatoEventType, param: TomatoParam): void
  (e: 'rest-finished', param: { id: number }): void
}>()

// 当前倒计时显示的剩余秒数
const currentRemainingSeconds = ref(0)
// 是否处于休息状态
const isResting = ref(false)
// 定时器句柄
let timer: number | undefined = undefined

// 避免重复触发事件
const hasWorkFinished = ref(false)
const hasRestFinished = ref(false)

// 音频元素引用
const baseAudioRef = ref<HTMLAudioElement | null>(null)
const shortAudioRef = ref<HTMLAudioElement | null>(null)
let fadeInterval: number

// 监听新任务
watch(
  () => props.item,
  () => {
    clearInterval(timer)
    if (props.item !== undefined) {
      // 重置状态
      hasWorkFinished.value = false
      hasRestFinished.value = false
      isResting.value = false
      currentRemainingSeconds.value = 0
      timer = setInterval(updateTomato, 500)
    }
  }
)

function updateTomato() {
  if (!props.item) return

  const startTime = new Date(props.item.startTime).getTime()
  const totalSeconds = (Date.now() - startTime) / 1000

  if (totalSeconds < WORK_SECONDS) {
    // 工作阶段
    isResting.value = false
    currentRemainingSeconds.value = WORK_SECONDS - totalSeconds
    hasWorkFinished.value = false
  } else if (totalSeconds >= WORK_SECONDS && totalSeconds < CYCLE_SECONDS) {
    // 休息阶段
    isResting.value = true
    currentRemainingSeconds.value = CYCLE_SECONDS - totalSeconds

    // 首次进入休息时触发工作完成事件并播放音乐
    if (!hasWorkFinished.value) {
      hasWorkFinished.value = true
      emit('done-task', 'auto', { id: props.item.itemId })
      playNotifacationAudio()
    }
  } else {
    // 休息结束或异常（≥30分钟）
    if (!hasRestFinished.value) {
      hasRestFinished.value = true
      
      // 休息结束短提示音
      playNotifacationAudioShort()
      emit('rest-finished', { id: props.item.itemId })
      
      // 清空所有状态，停止定时器
      clearInterval(timer)
      timer = undefined
      isResting.value = false
      currentRemainingSeconds.value = 0
    } else {
      // 已处理过，确保定时器清除
      clearInterval(timer)
      timer = undefined
    }
  }
}

function finishTask(type: TomatoEventType) {
  clearInterval(timer)
  if (props.item === undefined) return
  
  if (type == 'done') {
    playNotifacationAudioShort()
  }

  emit('done-task', type, { id: props.item.itemId })
}

const displayTimeStr = computed(() => {
  const seconds = Math.max(0, Math.floor(currentRemainingSeconds.value))
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m.toString().padStart(2, '0') + ':' + s.toString().padStart(2, '0')
})


function playNotifacationAudio() {
  const audio = baseAudioRef?.value
  if (audio) {
    doFadeIn(audio)
    audio.play()
    setTimeout(() => audio.pause(), 90 * 1000)
  }
}

function playNotifacationAudioShort() {
  const audio = shortAudioRef?.value
  if (audio) {
    doFadeIn(audio)
    audio.play()
  }
}

function doFadeIn(audio: HTMLAudioElement) {
  const MAX_VOLUME = 0.65
  audio.volume = 0.25
  // 设置淡入效果
  if (fadeInterval) clearInterval(fadeInterval)
  fadeInterval = setInterval(() => {
    if (audio.volume < MAX_VOLUME) {
      audio.volume += 0.01
    } else {
      audio.volume = MAX_VOLUME
      clearInterval(fadeInterval)
    }
  }, 100)
}

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<style scoped>
ol,
ul {
  padding: 0;
  list-style: none;
}

.FOCUS {
  border-left: 5px solid #ee0000;
  line-height: 32px;
  background: #fff;
  position: relative;
  margin-bottom: 10px;
  padding: 0 88px 0 8px;
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.07);
}

.function {
  position: absolute;
  display: inline-block;
  width: 14px;
  height: 12px;
  line-height: 14px;
  text-align: center;
  color: #888;
  font-weight: bold;
  font-size: 20px;
  cursor: pointer;
}

.function-0 {
  top: 6px;
  right: 14px;
}

.function-1 {
  top: 6px;
  right: 44px;
}
</style>