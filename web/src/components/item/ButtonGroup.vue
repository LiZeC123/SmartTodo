<template>
    <a v-for="(btn, idxBtn) in btnCfg" :key="btn.name" :class="['function', 'function-' + idxBtn]"
        @click="btn.f(index, item.id)" :title="btn.desc">
        <font-awesome-icon :icon="['fas', btn.name]" />
    </a>
</template>

<script setup lang="ts">
import type { ButtonConfig, Item } from './types'

defineProps<{
    btnCfg?: Array<ButtonConfig>
    index: number
    item: Item
}>()
</script>


<style scoped>
.function {
    position: absolute;
    display: inline-block;
    width: 14px;
    height: 12px;
    line-height: 14px;
    text-align: center;
    color: #888;
    font-weight: bold;
    font-size: 20px;
    cursor: pointer;
}

.function-0 {
    top: 6px;
    right: 10px;
}

.function-1 {
    top: 6px;
    right: 44px;
}

.function-2 {
    top: 6px;
    right: 78px;
}

.function-3 {
    top: 6px;
    right: 112px;
}
</style>