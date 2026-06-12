<template>
  <div class="card-page-container">
    <!-- 页面标题 -->
    <h1 class="page-title">功能导航</h1>

    <!-- 卡片容器 -->
    <div class="cards-wrapper">
      <!-- 循环渲染卡片 -->
      <router-link v-for="(card, index) in cardList" :key="index" :to="card.path" class="card-item"
        :target="card.isExternal ? '_blank' : '_self'">
        <h3 class="card-title">{{ card.title }}</h3>
        <span class="card-path">{{ card.path }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios';
import { computed, onMounted, ref, type Ref } from 'vue';

// 定义卡片数据类型
interface CardConfig {
  title: string;       // 卡片标题
  path: string;        // 路由路径
  isExternal?: boolean;// 是否新标签页打开（默认false，内部路由）
}

// 路由列表
const head: CardConfig[] = [
  { title: '待办事项', path: '/todo' },
  { title: '番茄时钟', path: '/tomato' },
  { title: '私人助理', path: '/assistant' },
  { title: '打卡记录', path: '/checkin' },

];

const dyNote: Ref<CardConfig[]> = ref([
  { title: '加载中', path: '/' },
  { title: '加载中', path: '/' },
  { title: '加载中', path: '/' },
  { title: '加载中', path: '/' },
])

const tail: CardConfig[] = [
  { title: '数据汇总', path: '/summary' },
  { title: '体重记录', path: '/me/weight' },
  { title: '积分管理', path: '/me/credits' },
  { title: '番茄计时', path: '/me/tomato' },
  { title: '福利中心', path: '/me/welfare' },
  { title: '添加积分', path: '/me/credit/add' }
]


onMounted(() => {
  // 动态加载最近访问的note, 可以更快的达到目标页面
  axios.post<CardConfig[]>('/item/recentNote').then((res) => {
    dyNote.value = res.data
  })
})

const cardList = computed(() => {
  return head.concat(dyNote.value, tail)
})

</script>

<style scoped>
/* 页面容器 */
.card-page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
  font-family: Arial, sans-serif;
}

/* 页面标题 */
.page-title {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 40px;
  font-size: 28px;
  font-weight: 600;
}

/* 卡片网格布局 */
.cards-wrapper {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

/* 单个卡片样式（router-link 本身是a标签） */
.card-item {
  display: block;
  /* 让链接占满整个卡片区域 */
  background: #ffffff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  border: 1px solid #f5f5f5;
  text-decoration: none;
  /* 去掉链接默认下划线 */
  cursor: pointer;
  /* 鼠标悬浮显示手型 */
}

/* 卡片悬浮效果 */
.card-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  border-color: #e8f4ff;
  background-color: #f8fbff;
}

/* 卡片标题 */
.card-title {
  margin: 0 0 8px 0;
  color: #2c3e50;
  font-size: 18px;
  font-weight: 600;
}

/* 路由路径文本 */
.card-path {
  color: #666666;
  font-size: 14px;
  opacity: 0.8;
  font-family: 'Courier New', monospace;
  /* 路径用等宽字体更易读 */
}

/* ========== 移动端紧凑布局（PC端效果完全不变） ========== */
@media (max-width: 768px) {

  /* 容器内边距缩小，增加可视区域 */
  .card-page-container {
    padding: 16px 12px;
  }

  /* 标题缩小，减少上下边距 */
  .page-title {
    font-size: 22px;
    margin-bottom: 20px;
  }

  /* 改用两列等宽布局，大幅提升卡片密度 */
  .cards-wrapper {
    grid-template-columns: repeat(2, minmax(130px, 1fr));
    gap: 12px;
  }

  /* 缩小卡片内边距，降低单个卡片高度 */
  .card-item {
    padding: 12px;
  }

  /* 标题字体缩小，行距紧凑 */
  .card-title {
    font-size: 15px;
    margin-bottom: 4px;
  }

  /* 路径字体缩小，更节省空间 */
  .card-path {
    font-size: 11px;
  }
}

/* 针对超小屏（如宽度 ≤ 400px）进一步微调，保持两列且不牺牲可读性 */
@media (max-width: 400px) {
  .cards-wrapper {
    gap: 10px;
  }

  .card-item {
    padding: 10px;
  }

  .card-title {
    font-size: 14px;
  }

  .card-path {
    font-size: 10px;
  }
}
</style>