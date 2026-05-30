<template>
    <h2>智能分析</h2>
    <p>今日共完成 {{ report.count }} 项任务, 各类任务占比情况如下: </p>
    <li v-for="g in report.groups" :key="g.name">[{{ ratio(g.items) }}%] 完成{{ counter(g.items.length) }}项任务 : {{ g.name
        }}</li>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { SmartAnalysisReport } from './types';
import type { Item } from "@/components/item/types"

const props = defineProps<{
    report: SmartAnalysisReport
}>()

const tC = computed(() => {
    let sum = 0
    for (let i = 0; i < props.report.groups.length; i++) {
        const v = props.report.groups[i]
        for (let j = 0; j < v.items.length; j++) {
            const item = v.items[j]
            sum += item.used_tomato
        }
    }
    return sum
})

function ratio(items: Item[]) {
    let sum = 0
    for (const item of items) {
        sum += item.used_tomato
    }

    return Math.floor((sum / tC.value) * 100).toString().padStart(2, ' ')
}

function counter(v: number) {
    return v.toString().padStart(2, ' ')
}




</script>


<style scoped>
li {
    font-family: monospace;
}
</style>