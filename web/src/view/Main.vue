<template>
  <div>
    <div class="header">
      <div class="box">
        <div id="form" @keyup.enter="commitTodo">
          <label for="title" @click="gotoHome">SmartTodo</label>
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

    <router-view class="container" :updateTodo="updateTodo" :createPlaceHold="createPlaceHold" parent="0"></router-view>

    <!-- 脚部：印记和功能按钮 -->
    <div class=" footer
    " id="footerContainer">
      Copyright &copy; {{ year }} LiZeC
    </div>
    <div class="footer" id="footerFunctionContainer">
      <a @click="selectFile">上传文件</a>
      <a v-if="isAdmin" @click="backUpData">备份数据</a>
      <a v-if="isAdmin && isMainPage" @click="updateLogs">查看日志</a>
      <a v-if="isAdmin" @click="gc">垃圾回收</a>
      <a v-if="isMainPage" @click="gotoTodaySummary">任务汇总</a>
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
      createPlaceHold: 0,
      year: new Date().getFullYear(),
      isAdmin: false
    }
  },
  created() {
    this.axios.get('/meta/isAdmin').then(rep => this.isAdmin = rep.data);
  },
  computed: {
    isMainPage: function () {
      return this.$route.fullPath === "/home/todo"
    }
  },
  methods: {
    gotoHome: function () {
      router.push({path: '/home/todo'})
      document.title = "待办事项列表"
    },
    commitTodo: function () {
      this.todoContent = this.todoContent.trim();
      if (this.todoContent === "") {
        alert("TODO不能为空")
        return
      }

      let match = /func (\S+) (.+)/.exec(this.todoContent)
      if (match !== null) {
        const data = {
          "cmd": match[1],
          "data": match[2],
          "parent": this.$route.params.id
        }
        this.axios.post("/admin/func", data).then(() => this.updateTodo += 1)
      } else {
        const data = parseTitleToData(this.todoContent, this.todoType, this.$route.params.id)
        // 通过修改updateTodo变量触发子组件的Todo部分更新操作
        this.axios.post("/item/create", data).then(() => this.updateTodo += 1)
        //根据需要判断是否需要先创建一个占位Item
        if (data.itemType === 'file') {
          this.createPlaceHold += 1
        }
      }

      // 提交请求后直接清空内容, 而不必等待请求返回, 提高响应速度, 避免重复提交
      this.todoContent = ""
      this.todoType = "single"
    },
    doLogout: function () {
      this.$store.commit('del_token')
      router.push({path: '/login'});
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

        let parent = '0'
        if (this.$route.params.id) {
          parent = this.$route.params.id
        }
        form.append("parent", parent)
        console.log(parent)


        let config = {
          headers: {'Content-Type': 'multipart/form-data'}
        };
        this.axios.post(url, form, config).then(() => {
          this.updateTodo += 1;
          console.log("Do Reload")
        })
      } else {
        alert("请先选择文件后再上传")
      }
    },
    backUpData: function () {
      this.axios.post("/admin/func", {"cmd": "backup", "data": "now", "parent": this.$route.params.id})
          .then(() => {
            this.updateTodo += 1
            alert("备份成功")
          })
    },
    updateLogs: function () {
      this.$router.push("/home/log/log");
    },
    gc: function () {
      this.axios.post("/admin/gc").then(() => {
        this.updateTodo += 1
        alert("垃圾回收完毕")
      })
    },
    gotoTodaySummary: function () {
      this.$router.push("/home/summary")
    }
  }
}


function parseTitleToData(todoContent, todoType, parent) {
  const values = todoContent.split(" ");

  // 分析类型
  let data = {
    "itemType": todoType,
  };


  // 分析任务名称
  if (values.length === 1) {
    data.name = todoContent;
  } else {
    data.name = values[0];
  }

  // 更新任务名称重新分析任务类型
  data.itemType = inferType(data.name, data.itemType);
  data.repeatable = inferRepeatable(data.name)

  // 分析参数
  if (parent !== undefined) {
    data.parent = parent;
  }
  for (let i = 1; i < values.length; i++) {
    if (values[i].charAt(0) !== "-") {
      data.name += " " + values[i];
    } else if (values[i] === "-dl" && i + 1 < values.length) {
      data.deadline = parseDeadline(values[i + 1]);
      i++;
    } else if (values[i] === "-re") {
      data.repeatable = true;
    } else if (values[i] === "-sp" && i + 1 < values.length) {
      data.specific = values[i + 1];
      i++;
    } else if (values[i] === "-td") {
      data.today = true;
    }
  }

  return data;
}

function inferType(name, itemType) {
  if (itemType !== "single") {
    return itemType;
  }

  if (inferFileType(name)) {
    return "file";
  } else if (inferNoteType(name)) {
    return 'note'
  } else {
    return "single"
  }
}

function inferFileType(name) {
  const dot = name.lastIndexOf(".");
  const fileType = name.substring(dot + 1);

  const knowTypes = ["zip", "jpg", "png", "exe", "rar"];

  if (knowTypes.indexOf(fileType) !== -1 && name.indexOf("http") !== -1) {
    return confirm("检测到链接类型为文件, 是否按照文件类型进行下载?");
  }

  return false;
}

function inferNoteType(name) {
  const knowType = ['计划', '规划', '事项', '分析', '笔记'];

  for (const type of knowType) {
    if (name.indexOf(type) !== -1) {
      return confirm("检测到代办类型包含关键词, 是否按照便签类型进行创建?")
    }
  }

  return false;
}

function inferRepeatable(name) {
  const knowType = ['每日', '今日'];

  for (const type of knowType) {
    if (name.indexOf(type) !== -1) {
      return confirm("检测到关键词, 是否添加可重复属性?")
    }
  }

  return false;
}

function parseDeadline(deadline) {
  let data = /(\d+)\.(\d+)(:(\d+))?/.exec(deadline)
  if (data) {
    let month = data[1]
    let day = data[2]
    let hour = data[4] === undefined ? 10 : data[4]
    return parseDate(month, day, hour, 0, 0);
  } else {
    data = /[Ww](\d+)/.exec(deadline)
    return parseWeek(data[1])
  }
}

function parseDate(tMonth, tDay, tHour, tMin, tSec) {
  let nowTime = new Date();
  let nowYear = nowTime.getFullYear();
  let ans = new Date(nowYear + "-" + tMonth + "-" + tDay + " " + tHour + ":" + tMin + ":" + tSec);
  if (ans < nowTime) {
    let nextYear = nowYear + 1;
    ans = new Date(nextYear + "-" + tMonth + "-" + tDay + " " + tHour + ":" + tMin + ":" + tSec);
  }
  return ans.getTime();
}

function parseWeek(weekDay) {
  const dayMillisecond = 24 * 60 * 60 * 1000;
  let time = new Date();
  let today = time.getDay();
  weekDay = weekDay % 7;
  let diffDay = weekDay - today;
  if (diffDay <= 0) {
    diffDay = 7 + diffDay;
  }
  let diffTime = diffDay * dayMillisecond;
  let curTime = time.getTime();
  return curTime + diffTime;
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
