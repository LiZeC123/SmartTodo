<template>
  <div v-show="props.item">
    <h2>当前任务</h2>
    <ol>
      <audio id="notificationAudio" :src="OceanWaves"></audio>
      <li class="FOCUS">
        【{{ displayTimeStr }}】{{ item?.taskName }}
        <a class="function function-1" title="取消任务" @click="finishTask('undo')">
          <font-awesome-icon :icon="['fas', 'undo']" />
        </a>
        <a class="function function-0" title="完成任务" @click="finishTask('done')">
          <font-awesome-icon :icon="['fas', 'check']" />
        </a>
      </li>
    </ol>
    <!-- <LedLight :msg="displayTimeStr"></LedLight> -->
  </div>
</template>

<script setup lang="ts">
import OceanWaves from './OceanWaves.mp3'
import { computed, ref, watch } from 'vue'
import type { TomatoEventType, TomatoItem, TomatoParam } from './types'
import { OneMinuteMS } from './types'

// import LedLight from '@/components/led/LedLight.vue'

const props = defineProps<{
  item?: TomatoItem
}>()

const emit = defineEmits<{
  (e: 'done-task', type: TomatoEventType, param: TomatoParam): void
}>()

// RemainingSeconds 当前番茄钟剩余时间
let rs = ref(0)
// 当前计时器
let timer: number | undefined = undefined

// 监听item重置行为
watch(
  () => props.item,
  () => {
    if (props.item !== undefined) {
      timer = setInterval(updateTomato, 500)
    }
  },
)


// 核心刷新函数, 每0.5秒刷新一次状态
function updateTomato() {
  if (!props.item) {
    return
  }

  // 更新剩余时间, 驱动页面刷新
  rs.value = calcRS(props.item)

  // 倒计时结束, 清除计时器
  if (rs.value < 0) {
    finishTask('done')
  }
}

function finishTask(type: TomatoEventType) {
  clearInterval(timer)
  if (props.item === undefined) {
    return
  }

  emit('done-task', type, {taskId: props.item.taskId, id: props.item.itemId})
}

const displayTimeStr = computed(() => {
  if (rs.value < 0) {
    return '00:00'
  }

  const m = Math.floor(rs.value / 60)
  const s = Math.floor(rs.value % 60)

  return m.toString().padStart(2, '0') + ':' + s.toString().padStart(2, '0')
})

function calcRS(item: TomatoItem) {
  const tomatoTimeMS = 25 * OneMinuteMS
  const finishedSecond = item.startTime + tomatoTimeMS
  const tsNow = new Date().getTime()

  return (finishedSecond - tsNow) / 1000
}
</script>

<style scoped>
/*清除ol和ul标签的默认样式*/
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
