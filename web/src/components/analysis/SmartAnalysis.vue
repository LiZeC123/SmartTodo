<template>
    <h2>智能分析</h2>
    <p>今日共完成 {{ report.count }} 项任务, 各类任务占比情况如下: </p>
    <li v-for="g in report.groups">[{{ ratio(g.items.length) }}%] 完成{{ counter(g.items.length) }}项任务 : {{ g.name }}</li>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { SmartAnalysisReport } from './types';

const props = defineProps<{
    report: SmartAnalysisReport
}>()

const tC = computed(() => {
    let sum = 0
    props.report.groups.forEach(v => sum += v.items.length)
    return sum
})

function ratio(v: number) {
    return Math.floor((v / tC.value) * 100).toString().padStart(2, ' ')
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