<template>
  <div v-if="data.length > 0">
    <h2>{{ title }}<span id="todoCount"> {{ data.length }}</span></h2>
    <ol id="todoList" class="demo-box">
      <li v-for="(item, index) in data" :key="item.id" :class="[done ? 'done' : '', mapTypeToClass(item)]"
          id="li-active">
        <label><input type='checkbox' @change='change(index)' :checked="done"/></label>
        <p @click='jumpTo(item.url)'>{{ mapName(item) }}</p>
        <a @click='click(index)'>{{ btnName }}</a>
      </li>
    </ol>
  </div>

</template>

<script>
export default {
  name: "ItemList",
  props: {
    title: String,
    btnName: String,
    done: Boolean,
    data: Array,
  },
  methods: {
    change: function (index) {
      this.$emit('checkbox-change', index)
    },
    jumpTo: function (url) {
      if (url !== null) {
        if (url.indexOf("http")) {
          window.open(url);
        } else {
          this.$router.push({path: '/home/' + url})
        }
      }
    },
    click: function (index) {
      this.$emit('btn-click', index);
    },
    mapTypeToClass: function (item) {
      if (item.repeatable) {
        return "repeatable"
      }

      if (item.specific) {
        return "specific";
      }

      // 如果是紧急任务, 则改变样式, 变成更醒目的红色
      if (item.urgent > 0 && item.urgent <= 4) {
        return "specific-" + item.urgent
      }

      return 'single';

    },
    mapName: function (item) {
      let showName = item.name

      if (item.item_type === "note") {
        showName = "【便签】" + item.name;
      } else if (item.item_type === "file") {
        showName = "【文件】" + item.name;
      } else if (item.url !== null) {
        showName = "【链接】" + item.name;
      }

      // 如果有截止时间, 加入截止日期标记
      if (item.deadline !== null) {
        // 截止日期只展示日期部分
        showName = "【" + item.deadline.split(" ")[0] + "】" + showName
      }

      // 如果是工作时间段, 加入工作时间段的标记
      if (item.work) {
        showName = "【工作】" + showName;
      }

      if (item.specific) {
        showName = "【" + getWeekByDay(item.specific) + "】" + showName
      }

      return showName;
    }
  }
}

function getWeekByDay(dayValue) {
  const today = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]; //创建星期数组
  return today[dayValue - 1];  //返一周中的某一天，其中1为周一
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

span {
  position: absolute;
  top: 2px;
  right: 5px;
  /*设置行内块 有宽高*/
  display: inline-block;
  padding: 0 5px;
  height: 20px;
  border-radius: 20px;
  background: #E6E6FA;
  line-height: 22px;
  text-align: center;
  color: #666;
  font-size: 14px;
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

/*清除ol和ul标签的默认样式*/
ol, ul {
  padding: 0;
  list-style: none;
}

#li-normal {
  line-height: 32px;
  background: #fff;
  position: relative;
  margin-bottom: 10px;
  padding: 0 45px;
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.07);
}

#li-active {
  line-height: 32px;
  background: #fff;
  position: relative;
  margin-bottom: 10px;
  padding: 0 45px;
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.07);
}

.done {
  border-left: 5px solid #999;
  /*不透明度 0完全透明~1完全不透明*/
  opacity: 0.5;
}

.single {
  border-left: 5px solid #006666;
}

.repeatable {
  border-left: 5px solid #08bf02;
}

.specific-4 {
  border-left: 5px solid #0020ee;
}

.specific-3 {
  border-left: 5px solid #fff400;
}

.specific-2 {
  border-left: 5px solid #ee8a00;
}

.specific-1 {
  border-left: 5px solid #EE0000;
}

.specific {
  border-left: 5px solid #EE0000;
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


/*勾选按钮*/
li a {
  position: absolute;
  top: 4px;
  right: 5px;
  display: inline-block;
  width: 14px;
  height: 12px;
  border-radius: 14px;
  border: 6px double #FFF;
  background: #CCC;
  line-height: 14px;
  text-align: center;
  color: #FFF;
  font-weight: bold;
  font-size: 14px;
  cursor: pointer;
}
</style>