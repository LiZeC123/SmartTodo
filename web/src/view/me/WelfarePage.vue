<template>
    <div id="app">
      <div class="container">
        <h1>福利兑换项目管理</h1>
        <!-- 创建项目表单 -->
        <form @submit.prevent="createProject" class="form">
          <input
            type="text"
            v-model="newProject.name"
            placeholder="项目名称"
            required
            class="input-field"
          />
          <input
            type="number"
            v-model="newProject.basePrice"
            placeholder="基础价格"
            required
            class="input-field"
          />
          <input
            type="text"
            v-model="newProject.cycle"
            placeholder="周期"
            required
            class="input-field"
          />
          <input
            type="number"
            v-model="newProject.priceFactor"
            placeholder="价格因子"
            required
            class="input-field"
          />
          <button type="submit" class="submit-button">创建项目</button>
        </form>
        <!-- 项目列表 -->
        <ul class="project-list">
          <li v-for="(project, index) in projects" :key="index" class="project-item">
            <div class="project-info">
              <span class="project-name">{{ project.name }}</span>
              <span class="project-detail">基础价格: {{ project.basePrice }}</span>
              <span class="project-detail">周期: {{ project.cycle }}</span>
              <span class="project-detail">价格因子: {{ project.priceFactor }}</span>
            </div>
            <button @click="deleteProject(index)" class="delete-button">删除</button>
          </li>
        </ul>
      </div>
    </div>
  </template>
  
  <script lang="ts" setup>
  import { ref } from 'vue';
  
  // 定义项目类型
  interface WelfareProject {
    name: string;
    basePrice: number;
    cycle: string;
    priceFactor: number;
  }
  
  // 存储所有项目
  const projects = ref<WelfareProject[]>([]);
  
  // 新创建项目的临时对象
  const newProject = ref<WelfareProject>({
    name: '',
    basePrice: 0,
    cycle: '',
    priceFactor: 0
  });
  
  // 创建项目的方法
  const createProject = () => {
    projects.value.push({ ...newProject.value });
    // 清空表单
    newProject.value = {
      name: '',
      basePrice: 0,
      cycle: '',
      priceFactor: 0
    };
  };
  
  // 删除项目的方法
  const deleteProject = (index: number) => {
    projects.value.splice(index, 1);
  };
  </script>
  
  <style scoped>
  /* 全局样式 */
  body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f4f4f9;
    margin: 0;
    padding: 0;
  }
  
  .container {
    max-width: 600px;
    margin: 30px auto;
    padding: 20px;
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  }
  
  h1 {
    text-align: center;
    color: #333;
    margin-bottom: 20px;
  }
  
  /* 表单样式 */
  .form {
    display: flex;
    flex-direction: column;
  }
  
  .input-field {
    padding: 10px;
    margin-bottom: 15px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 16px;
  }
  
  .submit-button {
    padding: 10px;
    background-color: #007bff;
    color: #fff;
    border: none;
    border-radius: 4px;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.3s ease;
  }
  
  .submit-button:hover {
    background-color: #0056b3;
  }
  
  /* 项目列表样式 */
  .project-list {
    list-style-type: none;
    padding: 0;
  }
  
  .project-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px;
    margin-bottom: 10px;
    border: 1px solid #eee;
    border-radius: 4px;
    background-color: #f9f9f9;
  }
  
  .project-info {
    display: flex;
    flex-direction: column;
  }
  
  .project-name {
    font-weight: bold;
    color: #333;
    margin-bottom: 5px;
  }
  
  .project-detail {
    color: #666;
    font-size: 14px;
  }
  
  .delete-button {
    padding: 8px 12px;
    background-color: #dc3545;
    color: #fff;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    transition: background-color 0.3s ease;
  }
  
  .delete-button:hover {
    background-color: #c82333;
  }
  
  /* 移动端兼容性样式 */
  @media (max-width: 768px) {
    .container {
      margin: 20px;
    }
  
    .input-field,
    .submit-button {
      width: 100%;
    }
  }
  </style>