<template>
  <div>
    <div v-if="showList">
      <h2 @mousedown.left="$emit('header-jump')">{{ title }}</h2>
      <ol id="todoList" class="demo-box" @contextmenu.prevent>
        <li v-for="(item, index) in sortedData" :key="item.id" id="li-active"
          :class="[{ done: doneItem(item) }, mapTypeToClass(item)]">
          <label><input type="checkbox" @change="$emit('done', index, item.id)" :checked="doneItem(item)"
              :disabled="doneItem(item)" /></label>
          <p @mousedown.left="jumpTo($event, item.name, item.url)">{{ mapName(item) }}</p>

          <a v-for="(btn, idxBtn) in btnCfg" :key="btn.name" :class="['function', 'function-' + idxBtn]"
            @click="btn.f(index, item.id)" :title="btn.desc">
            <font-awesome-icon :icon="['fas', btn.name]" />
          </a>
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { ButtonConfig, Item } from './types'
import { compareItem } from './sort';

const props = defineProps<{
  title?: string
  btnCfg?: Array<ButtonConfig>
  data?: Array<Item>
}>()

const emit = defineEmits<{
  (e: 'done', idx: number, id: string): void
  (e: 'jump-to', name: string, url: string): void
  (e: 'header-jump'): void
}>()

let showList = computed(() => {
  return props.data && props.data.length > 0
})

let sortedData = computed(() => {
  return props.data?.sort(compareItem)
})

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

  if (item.specific) {
    return 'specific'
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

// TODO: 鼠标事件可明确区分左右键,
async function jumpTo(event: MouseEvent, name: string, url?: string) {
  if (url) {
    emit('jump-to', name, url)
  }
}

function mapName(item: Item) {
  let showName = item.name

  if (item.item_type === 'note') {
    showName = '【便签】' + item.name
  } else if (item.item_type === 'file') {
    showName = '【文件】' + item.name
  } else if (item.url) {
    showName = '【链接】' + item.name
  }

  // 如果有截止时间, 加入截止日期标记
  if (item.deadline) {
    // 截止日期只展示日期部分
    showName = '【' + item.deadline.split(' ')[0] + '】' + showName
    const dd = new Date(item.deadline).getTime() - new Date().getTime()
    const hour = parseFloat((dd / (1000 * 60 * 60)).toFixed(1))

    // 非常接近的任务则显示具体的剩余时间
    if (hour < 100) {
      showName = '【剩余' + hour + '小时】' + showName
    }
  }

  if (item.specific) {
    showName = '【' + getWeekByDay(item.specific) + '】' + showName
  }

  if (item.expected_tomato && item.expected_tomato !== 1) {
    showName = '【' + item.used_tomato + '/' + item.expected_tomato + '】' + showName
  }

  return showName
}

function getWeekByDay(dayValue: number): string {
  const today = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] //创建星期数组
  return today[dayValue - 1] //返一周中的某一天，其中1为周一
}
</script>

<style scoped>
/*父相子绝*/
h2 {
  position: relative;
}

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

#li-active {
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

.subTask {
  margin-left: 40px;
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
./types
