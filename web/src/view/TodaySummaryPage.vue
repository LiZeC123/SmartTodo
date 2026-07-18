<template>
  <TodoSubmit></TodoSubmit>
  <div class="container">
    <ItemGroupedList title="临期任务汇总" :data="dlTask" :disable="true"></ItemGroupedList>
    <Footer :is-admin="false" :config="footerConfig"></Footer>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref, type Ref } from 'vue'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import ItemGroupedList from '@/components/item/ItemGroupedList.vue'
import Footer from '@/components/footer/TodoFooter.vue'

import type { FooterConfig } from '@/components/footer/types'
import type { GroupedItem } from '@/components/item/types'


onMounted(() => {
  loadDLItem()
  document.title = '总结列表'
})


// ========================================================== ItemList 相关配置 ==========================================================
let dlTask: Ref<GroupedItem[]> = ref([])

function loadDLItem() {
  axios.post<GroupedItem[]>('/item/getDeadlineItem').then((res) => { dlTask.value = res.data })
}





// ========================================================== Footer 相关配置 ==========================================================
let footerConfig: FooterConfig[] = []

</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>