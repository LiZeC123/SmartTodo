<template>
  <div>
    <div v-if="showList">
      <h2 @mousedown.left="$emit('header-click')">{{ title }}</h2>
      <ol @contextmenu.prevent>
        <ItemLine v-for="(item, index) in sortedData" :key="item.id" :item="item" :index="index" :btn-cfg="btnCfg"
          @click="(e, i) => $emit('item-click', e, i)" @done="(idx, id) => $emit('done', idx, id)"></ItemLine>
      </ol>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { ButtonConfig, Item } from './types'
import { compareItem } from './sort';

import ItemLine from "./ItemLine.vue";

const props = defineProps<{
  title?: string
  btnCfg?: Array<ButtonConfig>
  data?: Array<Item>
}>()

const emit = defineEmits<{
  (e: 'done', idx: number, id: string): void
  (e: 'item-click', event: MouseEvent, item: Item): void
  (e: 'header-click'): void
}>()

let showList = computed(() => {
  return props.data && props.data.length > 0
})

let sortedData = computed(() => {
  return props.data?.sort(compareItem)
})

</script>

<style scoped>
/*清除ol和ul标签的默认样式*/
ol,
ul {
  padding: 0;
  list-style: none;
}
</style>