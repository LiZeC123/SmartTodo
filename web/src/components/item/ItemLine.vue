<template>
    <li :class="['active', { done: doneItem(item) }, mapTypeToClass(item)]">
        <label><input type="checkbox" @change="$emit('done', index, item.id)" :checked="doneItem(item)"
                :disabled="doneItem(item)" /></label>
        <p @mousedown="clickItem(item, $event)">{{ mapName(item) }}</p>

        <ButtonGroup :btn-cfg="btnCfg" :index="index" :item="item"></ButtonGroup>
    </li>
</template>

<script setup lang="ts">
import type { ButtonConfig, Item } from './types'
import { mapName } from './mapper'

import ButtonGroup from "./ButtonGroup.vue";
import router from '@/router'

const props = defineProps<{
    item: Item
    index: number
    btnCfg?: Array<ButtonConfig>
}>()

const emit = defineEmits<{
    (e: 'done', idx: number, id: string): void
    (e: 'click', event: MouseEvent, item: Item): void
}>()


function doneItem(item: Item): boolean {
    if (item.used_tomato && item.expected_tomato) {
        return item.used_tomato === item.expected_tomato
    } else {
        return false
    }
}

function mapTypeToClass(item: Item): string {
    if (item.repeatable) {
        return 'repeatable'
    }

    // 如果指定了deadline, 则计算距离deadline的时间并设置不同的颜色
    if (item.deadline) {
        let delta = new Date(item.deadline).getTime() - new Date().getTime()
        const dayMs = 24 * 60 * 60 * 1000
        let urgent = Math.ceil(delta / dayMs)

        if (urgent <= 1) {
            return 'specific-1'
        } else if (urgent <= 4) {
            return 'specific-' + urgent
        }
    }

    return 'single'
}

function clickItem(item: Item, event: MouseEvent): void {
  // 执行组件默认行为
  if (event.button === 0) {
    jumpTo(item)
  } else if (event.button === 2) {
    copyMarkdown(item)
  }

  // 向上传递事件, 上层组件可执行其他操作
  emit('click', event, item)
}


function jumpTo(item: Item) {
  if (!item.url) {
    return;
  }

  let path = item.url;
  if (path.startsWith('note')) {
    // note对应的路径, 路由跳转
    path = "/" + path
    router.push({ path })
  } else {
    // 外部URL, 文件URL等直接打开
    window.open(path)
  }

}

function copyMarkdown(item: Item) {
  if (!item.url) {
    return;
  }

  let text = `[${item.name}](${item.url})`
  console.log(["Do Copy", text])
  navigator.clipboard.writeText(text)
}


</script>

<style scoped>
/*选中输入框  轮廓的宽度为0*/
input:focus {
    outline-width: 0;
}

label {
    float: left;
    width: 100px;
    line-height: 50px;
    color: #ddd;
    font-size: 24px;
    /*鼠标悬停样式 一只手*/
    cursor: pointer;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

/*清除ol和ul标签的默认样式*/
ol,
ul {
    padding: 0;
    list-style: none;
}

.active {
    line-height: 32px;
    background: #fff;
    position: relative;
    margin-bottom: 10px;
    padding: 0 88px 0 42px;
    border-radius: 3px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.07);
}

.done {
    border-left: 5px solid #999;
    /*不透明度 0完全透明~1完全不透明*/
    opacity: 0.5;
    /*删除线效果*/
    text-decoration: line-through;
}

.single {
    border-left: 5px solid #006666;
}

.repeatable {
    border-left: 5px solid #08bf02;
}

.specific-4 {
    border-left: 5px solid rgba(0, 32, 238, 0.94);
}

.specific-3 {
    border-left: 5px solid #eee916;
}

.specific-2 {
    border-left: 5px solid #ff7700;
}

.specific-1 {
    border-left: 5px solid #ee0000;
}

.specific {
    border-left: 5px solid #ee0000;
}

/*任务单选框*/
li input {
    position: absolute;
    top: 2px;
    left: 10px;
    width: 22px;
    height: 22px;
    cursor: pointer;
}

p {
    margin: 0;
}
</style>