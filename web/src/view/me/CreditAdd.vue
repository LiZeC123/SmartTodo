<template>
    <div class="form-container">
      <h1 class="form-title">积分录入</h1>
      <form @submit.prevent="handleSubmit" class="form-content">
        <!-- 项目类型选择 -->
        <div class="form-item">
          <label for="project-type" class="form-label">项目类型</label>
          <select
            id="project-type"
            v-model="selectedProject"
            class="form-select"
            required
          >
            <option
              v-for="project in projects"
              :key="project.value"
              :value="project.value"
            >
              {{ project.label }}
            </option>
          </select>
        </div>
  
        <!-- 分数输入 -->
        <div class="form-item">
          <label for="score" class="form-label">积分分数</label>
          <input
            id="score"
            v-model.number="score"
            type="number"
            min="0"
            step="1"
            placeholder="请输入分数"
            class="form-input"
            required
          />
          <div v-if="!isScoreValid" class="error-msg">请输入有效的正整数值</div>
        </div>
  
        <button type="submit" class="submit-btn">提交</button>
      </form>
    </div>
  </template>
  
  <script setup lang="ts">
  import router from '@/router'
import axios from 'axios'
import { ref, computed } from 'vue'
  
  interface Project {
    value: string
    label: string
  }
  
  // 响应式数据
  const selectedProject = ref('sports')
  const score = ref<number | null>(null)
  
  // 项目选项（便于后续扩展）
  const projects: Project[] = [
    { value: 'sports', label: '运动积分' }
  ]
  
  // 分数验证
  const isScoreValid = computed(() => {
    return score.value !== null && Number.isInteger(score.value) && score.value >= 0
  })
  
  // 表单提交处理
  const handleSubmit = () => {
    if (!isScoreValid.value) return
    
    // 提交成功跳转至积分兑换页面
    axios.post('/credit/add', {"type": selectedProject.value, 'score': score.value}).then(() => router.push('/me/credits'))
  }
  </script>
  
  <style scoped>
  .form-container {
    max-width: 600px;
    margin: 2rem auto;
    padding: 1.5rem;
    background-color: #f8f9fa;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
  
  .form-title {
    text-align: center;
    color: #2c3e50;
    margin-bottom: 1.5rem;
    font-size: 1.8rem;
  }
  
  .form-content {
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
  }
  
  .form-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .form-label {
    font-weight: 500;
    color: #4a5568;
    font-size: 0.95rem;
  }
  
  .form-input,
  .form-select {
    padding: 0.8rem;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 1rem;
    transition: border-color 0.3s ease;
  }
  
  .form-input:focus,
  .form-select:focus {
    outline: none;
    border-color: #4299e1;
    box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.2);
  }
  
  .error-msg {
    color: #e53e3e;
    font-size: 0.85rem;
    margin-top: 0.3rem;
  }
  
  .submit-btn {
    background-color: #4299e1;
    color: white;
    padding: 0.8rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.3s ease;
    align-self: flex-end;
  }
  
  .submit-btn:hover {
    background-color: #3182ce;
  }
  
  /* 移动端适配 */
  @media (max-width: 480px) {
    .form-container {
      margin: 1rem;
      padding: 1rem;
    }
  
    .form-title {
      font-size: 1.5rem;
    }
  
    .form-input,
    .form-select {
      padding: 0.7rem;
    }
  }
  </style>