<template>
  <div>
    <div class="header">
      <div class="box">
        <div id="form" @keyup.enter="commitTodo">
          <label for="title">ToDoList</label>
          <div style="float: right;width: 60%;">
            <label for="itemType"></label>
            <select id="itemType" v-model="todoType">
              <option value="single">创建待办</option>
              <option value="file">下载文件</option>
              <option value="note">创建便签</option>
            </select>
            <input type="text" id="title" placeholder="添加ToDo" autocomplete="off" v-model="todoContent"/>
          </div>
        </div>
      </div>
    </div>

    <router-view class="container" :updateTodo="updateTodo"></router-view>

    <!-- 脚部：印记和功能按钮 -->
    <div class="footer" id="footerContainer">
      Copyright &copy; {{ year }} LiZeC
    </div>
    <div class="footer" id="footerFunctionContainer">
      <a @click="selectFile">上传文件</a>
      <a @click="downCenter">文件中心</a>
      <!--      <a v-if="isAdmin" href="javascript:backUpData()">备份数据</a>-->
      <!--      <a v-if="isAdmin" href="javascript:updateLogs()">查看日志</a>-->
      <!--      <a v-if="isAdmin" href="javascript:downCenter()">下载中心</a>-->
      <a @click="doLogout">退出登录</a>
    </div>

    <!-- 上传文件的控件 -->
    <input type="file" id="file_selector" style="display: none;" @change="uploadFile"/>
  </div>
</template>

<script>
import router from "@/router";

export default {
  name: "Main",
  data: function () {
    return {
      todoContent: "",
      todoType: "single",
      updateTodo: 0,
      year: new Date().getFullYear(),
      isAdmin: false
    }
  },
  created() {
  },
  methods: {
    commitTodo: function () {
      if (this.todoContent.trim() === "") {
        alert("TODO不能为空");
      } else if (/set (.+)/.test(this.todoContent) || /fun (.+)/.test(this.todoContent)) {
        // TODO: Operation Or Function
      } else {
        this.$axios({
          method: "post",
          url: "/item/create",
          data: parseTitleToData(this.todoContent, this.todoType, this.$route.params.id)
        }).then(res => {
          if (res.data.success) {
            this.updateTodo += 1    // 通过此变量触发子组件的Todo部分更新操作
            this.todoContent = ""
          }
        })
      }
    },
    doLogout: function () {
      this.$store.commit('del_token')
      router.push({path: '/login'}).then(() => {
      });
    },
    selectFile: function () {
      document.getElementById("file_selector").click();

    },
    uploadFile: function () {
      // http://www.feingto.com/?p=14158
      const file_obj = document.getElementById("file_selector").files[0];
      if (file_obj) {
        const url = "/file/upload";
        const form = new FormData();
        form.append("myFile", file_obj);
        let config = {
          headers:{'Content-Type':'multipart/form-data'}
        };
        this.$axios.post(url, form, config).then(()=> {this.updateTodo += 1;console.log("Do Reload")})
      } else {
        alert("请先选择文件后再上传")
      }
    },
    downCenter: function () {
      window.location = 'file';
    }
  }
}


function parseTitleToData(todoContent, todoType, parent) {
  const values = todoContent.split(" ");

  let data = {
    "itemType": todoType,
  };
  if (values.length === 1) {
    data.name = todoContent;
  } else {
    data.name = values[0];
  }
  if (parent !== undefined) {
    data.parent = parent;
  }

  for (let i = 1; i < values.length; i++) {
    if (values[i].charAt(0) !== "-") {
      data.name += " " + values[i];
    } else if (values[i] === "-dl" && i + 1 < values.length) {
      data.deadline = values[i + 1];
      i++;
    } else if (values[i] === "-wk") {
      data.work = true;
    } else if (values[i] === "-re") {
      data.repeatable = true;
    } else if (values[i] === "-sp" && i + 1 < values.length) {
      data.specific = values[i + 1];
      i++;
    }
  }

  console.log(["Commit Data", data]);
  return data;
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