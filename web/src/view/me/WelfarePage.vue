<template>
  <div class="welfare-management">
    <h1>福利兑换管理</h1>
    <!-- 添加兑换项目的表单 -->
    <div class="form-container">
      <h2>添加兑换项目</h2>
      <form @submit.prevent="addItem">
        <div class="form-group">
          <label for="name">项目名称</label>
          <input type="text" id="name" v-model.trim="newItem.name" required />
        </div>
        <div class="form-group">
          <label for="basePrice">基础价格</label>
          <input type="number" id="basePrice" v-model.number="newItem.basePrice" required />
        </div>
        <div class="form-group">
          <label for="period">周期（天）</label>
          <input type="number" id="period" v-model.number="newItem.period" required />
        </div>
        <div class="form-group">
          <label for="priceFactor">价格因子</label>
          <input type="number" id="priceFactor" v-model.number="newItem.priceFactor" required />
        </div>
        <button type="submit">添加项目</button>
      </form>
    </div>
    <!-- 展示已创建的项目列表 -->
    <div class="list-container">
      <h2>已创建的项目</h2>
      <div v-if="items.length === 0" class="empty-message">暂无项目，请添加！</div>
      <div class="item-list" v-else>
        <div v-for="(item, index) in items" :key="item.name" class="item-card">
          <div class="item-info">
            <div class="item-name">{{ item.name }}</div>
            <div class="item-details">
              <span>基础价格：{{ item.basePrice }}</span>
              <span>周期：{{ item.period }} 天</span>
              <span>价格因子：{{ item.priceFactor }}</span>
            </div>
          </div>
          <button class="delete-button" @click="deleteItem(index)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface WelfareItem {
  name: string;
  basePrice: number;
  period: number;
  priceFactor: number;
}

const newItem = ref<WelfareItem>({
  name: '',
  basePrice: 150,
  period: 7,
  priceFactor: 1,
});

const items = ref<WelfareItem[]>([]);

const addItem = () => {
  if (!newItem.value.name) return;
  items.value.push({ ...newItem.value });
  newItem.value = { name: '', basePrice: 0, period: 0, priceFactor: 0 };
};

const deleteItem = (index: number) => {
  items.value.splice(index, 1);
};
</script>

<style scoped>
.welfare-management {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

h1,
h2 {
  text-align: center;
  color: #333;
}

.form-container,
.list-container {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #555;
}

.form-group input {
  width: 98%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input:focus {
  border-color: #007bff;
  outline: none;
}

button {
  padding: 10px 15px;
  border: none;
  border-radius: 4px;
  background-color: #007bff;
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

button:hover {
  background-color: #0056b3;
}

.empty-message {
  text-align: center;
  color: #888;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background-color: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 6px;
  transition: box-shadow 0.3s ease;
}

.item-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.item-info {
  flex: 1;
}

.item-name {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.item-details {
  display: flex;
  gap: 15px;
  font-size: 14px;
  color: #666;
}

.delete-button {
  background-color: #dc3545;
  padding: 8px 12px;
  font-size: 12px;
}

.delete-button:hover {
  background-color: #c82333;
}

@media (max-width: 600px) {
  .welfare-management {
    padding: 10px;
  }

  .form-container,
  .list-container {
    padding: 15px;
  }

  .item-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .delete-button {
    width: 100%;
  }
}
</style>
