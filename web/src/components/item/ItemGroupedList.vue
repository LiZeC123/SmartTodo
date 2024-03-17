<template>
  <div>
    <div v-if="showList">
      <h2>{{ title }}</h2>
      <ol @contextmenu.prevent v-for="(gItem, index) in data" :key="gItem.self.id">
        <ItemLine :item="gItem.self" :index="index"></ItemLine>
        <ItemLine class="subTask" v-for="(item, subIdx) in sortedData(gItem.children)" :item="item" :index="subIdx" @done="(idx, id) => $emit('done', idx, id)"></ItemLine>
      </ol>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { ButtonConfig, GroupedItem, Item } from './types'
import { compareItem } from './sort';

import ItemLine from './ItemLine.vue';

const props = defineProps<{
  title?: string
  btnCfg?: Array<ButtonConfig>
  data?: Array<GroupedItem>
}>()

const emit = defineEmits<{
  (e: 'done', idx: number, id: string): void
  (e: 'jump-to', name: string, url: string): void
}>()

let showList = computed(() => {
  return props.data && props.data.length > 0
})


function sortedData(items: Item[]): Item[] {
  return items?.sort(compareItem)
}
</script>



<style scoped>
/*清除ol和ul标签的默认样式*/
ol,
ul {
  padding: 0;
  list-style: none;
}


.subTask {
  margin-left: 40px;
}
</style>