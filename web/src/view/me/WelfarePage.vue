<template>
  <TodoSubmit></TodoSubmit>
  <div class="welfare-management">
    <!-- 添加兑换项目的表单 -->
    <div class="form-card">
      <h2>添加兑换项目</h2>
      <form @submit.prevent="addItem">
        <div class="form-group">
          <label for="name">项目名称</label>
          <input type="text" id="name" v-model="newItem.name" placeholder="请输入项目名称" required />
        </div>
        <div class="form-group">
          <label for="basePrice">基础价格</label>
          <input type="number" id="basePrice" v-model.number="newItem.price" placeholder="请输入基础价格" min="0" required />
        </div>
        <div class="form-group">
          <label for="cycle">周期</label>
          <input type="number" id="cycle" v-model.number="newItem.cycle" placeholder="请输入周期" min="1" required />
        </div>
        <div class="form-group">
          <label for="priceFactor">价格因子</label>
          <input type="number" id="priceFactor" v-model.number="newItem.factor" placeholder="请输入价格因子" min="0" required />
        </div>
        <button type="submit" class="add-button">添加项目</button>
      </form>
    </div>

    <!-- 兑换项目列表 -->
    <div class="list-card">
      <h2>兑换项目列表</h2>
      <table class="item-table">
        <thead>
        <tr>
          <th>项目名称</th>
          <th>基础价格</th>
          <th>周期</th>
          <th>价格因子</th>
          <th>操作</th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>{{ item.name }}</td>
          <td>{{ item.price }}</td>
          <td>{{ item.cycle }}</td>
          <td>{{ item.factor }}</td>
          <td><button class="delete-button" @click="deleteItem(item)">删除</button></td>
        </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>



<script setup lang="ts">
import { reactive, ref } from 'vue';
import TodoSubmit from '@/components/submit/TodoSubmit.vue'

interface WelfareItem {
  id: number;
  name: string;
  price: number;
  cycle: number;
  factor: number;
}

// 定义新项目的初始状态，使用 reactive 创建响应式对象
const newItem = reactive<WelfareItem>({
  id: 0,
  name: '',
  price: 150,
  cycle: 7,
  factor: 1,
});

// 定义项目列表，使用 ref 创建响应式数组
const items = ref<WelfareItem[]>([]);

// 自增的 ID，用于为每个新项目生成唯一 ID
let nextId = 1;

// 添加项目的方法
const addItem = () => {
  // 校验表单输入是否有效
  if (!newItem.name || newItem.price <= 0 || newItem.cycle <= 0 || newItem.factor < 0) {
    alert('请填写所有字段并确保数值有效');
    return;
  }

  // 将新项目添加到列表中
  items.value.push({
    id: nextId++,
    name: newItem.name,
    price: newItem.price,
    cycle: newItem.cycle,
    factor: newItem.factor,
  });

  // 清空表单
  newItem.name = '';
  newItem.price = 0;
  newItem.cycle = 1;
  newItem.factor = 0;
};

// 删除项目的方法
const deleteItem = (item: WelfareItem) => {
  // 使用 filter 方法从列表中移除指定项目
  items.value = items.value.filter((i) => i.id !== item.id);
};
</script>


<style scoped>
/* 基本样式 */
.welfare-management {
  padding: 20px;
  font-family: Arial, sans-serif;
}

.form-card, .list-card {
  margin-bottom: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

h2 {
  margin-top: 0;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}

.add-button {
  background-color: #4caf50;
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 4px;
  cursor: pointer;
}

.add-button:hover {
  background-color: #45a049;
}

.item-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.item-table th, .item-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: center;
}

.item-table th {
  background-color: #f2f2f2;
}

.delete-button {
  background-color: #f44336;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
}

.delete-button:hover {
  background-color: #d32f2f;
}

/* 移动端样式调整 */
@media (max-width: 768px) {
  .form-group {
    flex-direction: column;
  }

  .item-table th, .item-table td {
    font-size: 14px;
  }
}
</style>