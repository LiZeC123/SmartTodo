<template>
  <div class="container">
    <!-- 番茄钟模块 -->
    <TomatoClock :item="tomatoItem" @done-task="doneTomatoTask"></TomatoClock>
    <ItemList title="今日任务" :btnCfg="tCfg" :data="tTask"></ItemList>
  </div>
</template>

<script setup lang="ts">
import { playNotifacationAudio } from '@/components/tomato/tools'
import type { TomatoItem, TomatoEventType, TomatoParam } from '@/components/tomato/types'
import axios from 'axios'
import { type Ref, ref, onMounted } from 'vue'

import TomatoClock from '@/components/tomato/TomatoClock.vue'
import ItemList from '@/components/item/ItemList.vue'
import type { Item } from '@/components/item/types'

// ========================================================== TomatoClock 相关配置 ==========================================================
let tomatoItem: Ref<TomatoItem | undefined> = ref()

onMounted(()=> {
  loadTomato()
  loadTomatoItems()
  document.title = '番茄任务'
})

async function loadTomato() {
  let res = await axios.get<TomatoItem>('/tomato/getTask')
  tomatoItem.value = res.data
}

async function doneTomatoTask(type: TomatoEventType, param: TomatoParam) {
  if (type === 'undo') {
    await axios.post('/tomato/undoTask', param)
  } else if (type === 'done') {
    let res = await axios.post<boolean>('/tomato/finishTaskManually', param)
    if (res.data) {
      playNotifacationAudio()
      tomatoItem.value = undefined
      loadTomatoItems()
    }
  }
}

// ========================================================== ItemList 相关配置 ==========================================================
let tTask: Ref<Item[]> = ref([])

const tCfg = [
  {
    name: 'clock',
    desc: '启动番茄钟',
    f: (_: number, id: string) => {
      axios.post('/tomato/setTask', { id }).then(() => {
        loadTomato()
      })
    }
  },
  // {
  //   name: 'calculator',
  //   desc: '增加预计时间',
  //   f: (index: number, id: string) => {
  //     axios.post('/item/incExpTime', { id }).then(() => (tTask.value[index].expected_tomato += 1))
  //   }
  // }
]

function loadTomatoItems() {
  axios.post<Item[]>('/item/getTomato').then((res) => {
    tTask.value = res.data
  })
}


</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>
