<template>
    <p></p>
    <li v-for="item in items">{{ item.time }}  {{ item.content }}</li>
</template>

<script setup lang="ts">
import type { EventItem } from './types';


const props = defineProps<{
    items: EventItem[]
}>()
</script>


<style scoped>
li {
    font-family:monospace;
}
</style>