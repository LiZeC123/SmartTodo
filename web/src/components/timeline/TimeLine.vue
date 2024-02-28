<template>
    <h2>任务时间轴</h2>
    <p>已完成 {{ props.count.tomatoCounts }} 个番茄钟, 累计专注 {{ focusHour }} 小时 {{ focusMinute }} 分钟</p>
    <li v-for="item in fullItems" :class="mapClass(item)" >{{ item.start }} - {{ item.finish }} ({{ elapsedTime(item) }}分钟) {{ item.title }}</li>
</template>


<script setup lang="ts">
import { computed } from "vue";
import type { TimeLineItem, CountInfo } from "./types"
import { fullTimeLine, timeStrToMinutes } from "./convert";

const props = defineProps<{
    items: TimeLineItem[]
    count: CountInfo
}>()

const focusHour = computed(() => Math.floor(props.count.totalMinutes / 60))
const focusMinute = computed(() => Math.floor(props.count.totalMinutes % 60))
const fullItems = computed(() => fullTimeLine(props.items))

function mapClass(item: TimeLineItem): string {
    if (item.title.includes("===")) {
        return "empty"
    } else {
        return "tomato"
    }
}

function elapsedTime(item: TimeLineItem): string {
    const v = timeStrToMinutes(item.finish) - timeStrToMinutes(item.start)
    return v.toString().padStart(2, '0')
}

</script>

<style scoped>
li {
    font-family: monospace;
}

.tomato {
    margin-top: 4px;
}

.empty {
    opacity: 0.4;
    margin-top: 8px;
    margin-bottom: 8px;
}
</style>