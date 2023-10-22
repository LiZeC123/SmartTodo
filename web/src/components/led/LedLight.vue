<template>
    <canvas id="ledCanvas" width="250" height="100"></canvas>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { updateLedValue } from './draw'

const props = defineProps<{
  msg: string
}>()

onMounted(()=> {
    updateLedValue(document.querySelector('#ledCanvas') as HTMLCanvasElement, { values: props.msg })
})

watch(
  () => props.msg,
  () => {
    updateLedValue(document.querySelector('#ledCanvas') as HTMLCanvasElement, { values: props.msg })
  }
)
</script>

<style scoped>
canvas {
  transform: skewX(-10deg);
  display: block;
  margin: auto;
}
</style>
