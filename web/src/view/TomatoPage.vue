<template>
  <div class="container">
    <!-- 番茄钟模块 -->
    <TomatoClock :item="tomatoItem" @done-task="doneTomatoTask"></TomatoClock>
    <ItemList title="今日任务" :btnCfg="tCfg" :data="tTask" @done="doneItem"></ItemList>
    <Footer :is-admin="false" :config="footerConfig"></Footer>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { type Ref, ref, onMounted } from 'vue'
import router from '@/router'

import TomatoClock from '@/components/tomato/TomatoClock.vue'
import ItemList from '@/components/item/ItemList.vue'
import Footer from '@/components/footer/TodoFooter.vue'

import { playNotifacationAudio } from '@/components/tomato/tools'
import type { TomatoItem, TomatoEventType, TomatoParam } from '@/components/tomato/types'
import type { Item } from '@/components/item/types'
import type { FooterConfig } from '@/components/footer/types'

onMounted(() => {
  loadTomato()
  loadTomatoItems()
  document.title = '番茄任务'
  window.onfocus = loadTomatoItems
})

// ========================================================== TomatoClock 相关配置 ==========================================================
let tomatoItem: Ref<TomatoItem | undefined> = ref()

function loadTomato() {
  axios.get<TomatoItem>('/tomato/getTask').then((res) => { tomatoItem.value = res.data })
}

function doneTomatoTask(type: TomatoEventType, param: TomatoParam) {
  if (type === 'undo') {
    const reason = prompt("请输入取消原因")
    if (reason) {
      param.reason = reason
    }

    axios.post('/tomato/undoTask', param).then(() => tomatoItem.value = undefined)
  } else if (type === 'done') {
    axios.post<boolean>('/tomato/finishTask', param).then(res => {
      if (res.data) {
        playNotifacationAudio()
        tomatoItem.value = undefined
        loadTomatoItems()
      }
    })
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
  axios.post<Item[]>('/item/getTomato').then((res) => { tTask.value = res.data })
}

function doneItem(index: number, id: string) {
  axios.post('/item/incUsedTime', { id }).then(() => (tTask.value[index].used_tomato += 1))
}



// ========================================================== Footer 相关配置 ==========================================================
let footerConfig: FooterConfig[] = [
  { name: '待办列表', needAdmin: false, f: () => router.push({ path: '/todo' }) },
  { name: '总结列表', needAdmin: false, f: () => router.push({ path: '/summary' }) },
]

</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>
