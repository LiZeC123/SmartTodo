<template>
  <div>
    <div class="header">
      <div class="box">
        <form action="javascript:commitGlobalTodo()" id="form">
          <label for="title">ToDoList</label>
          <div style="float: right;width: 60%;">
            <label for="itemType"></label>
            <select id="itemType">
              <option value="single">创建待办</option>
              <option value="file">下载文件</option>
              <option value="note">创建便签</option>
            </select>
            <input type="text" id="title" name="title" placeholder="添加ToDo" required="required" autocomplete="off"/>
          </div>
        </form>
      </div>
    </div>

    <router-view class="container"></router-view>

    <!-- 脚部：印记和功能按钮 -->
    <div class="footer" id="footerContainer">
      Version {{ version }} Copyright &copy; {{ year }} LiZeC
    </div>
    <div class="footer" id="footerFunctionContainer">
      <a href="javascript:selectFile()">上传文件</a>
      <a v-if="isAdmin" href="javascript:backUpData()">备份数据</a>
      <a v-if="isAdmin" href="javascript:updateLogs()">查看日志</a>
      <a v-if="isAdmin" href="javascript:downCenter()">下载中心</a>
      <a href="javascript:doLogout()">退出登录</a>
    </div>

    <!-- 上传文件的控件 -->
    <input type="file" id="file_selector" style="display: none;" onchange="uploadFile()"/>
  </div>
</template>

<script>
export default {
  name: "Main",
  data: function () {
    return {
      version: "2.0.0",
      year: 2021,
      isAdmin: false
    }
  }
}
</script>

<style scoped>
body {
  margin: 0;
  padding: 0;
  font-size: 16px;
  background: #CDCDCD;
}

.header {
  height: 50px;
  background: #333;
  /*background: rgba(47,47,47,0.98);*/
}

.header .box {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}

.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}


label {
  float: left;
  width: 100px;
  line-height: 50px;
  color: #DDD;
  font-size: 24px;
  /*鼠标悬停样式 一只手*/
  cursor: pointer;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
}

.header input {
  float: right;
  width: 73%;
  height: 24px;
  margin-top: 12px;
  /*首行缩进10px*/
  text-indent: 10px;
  /*圆角边框  好看不止一点点*/
  border-radius: 5px;
  /*盒子阴影 inset内阴影*/
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.24), 0 1px 6px rgba(0, 0, 0, 0.45) inset;
  border: none
}

.header select {
  margin-top: 12px;
  height: 26px;
  width: 25%;
  border-radius: 5px;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.24), 0 1px 6px rgba(0, 0, 0, 0.45) inset;
  border: none;
}

/*选中输入框  轮廓的宽度为0*/
input:focus {
  outline-width: 0;
}

.footer {
  color: #666;
  font-size: 14px;
  text-align: center;
}

.footer a {
  text-decoration: none;
  color: #999;
  margin-right: 5px;
}

</style>