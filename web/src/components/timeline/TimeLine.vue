<template>
    <p>已完成 {{ props.count.tomatoCounts }} 个番茄钟, 累计专注 {{ focusHour }} 小时 {{ focusMinute }} 分钟</p>
    <li v-for="item in props.items">{{ item.start }} - {{ item.finish }}  {{ item.title }}</li>
</template>


<script setup lang="ts">
import { computed } from "vue";
import type { TimeLineItem, CountInfo } from "./types"

const props = defineProps<{
    items: TimeLineItem[]
    count: CountInfo
}>()

const focusHour = computed(() => Math.floor(props.count.totalMinutes / 60))

const focusMinute = computed(() => Math.floor(props.count.totalMinutes % 60))

</script>