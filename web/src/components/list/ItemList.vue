<template>
  <div v-if="data.length > 0">
    <h2>{{ title }}<span id="todoCount"> {{ data.length }}</span></h2>
    <ol id="todoList" class="demo-box">
      <li v-for="(item, index) in data" :key="item.id" :class="[done ? 'done' : '', mapTypeToClass(item)]"
          id="li-active">
        <label><input type='checkbox' @change='change(index)' :checked="done"/></label>
        <p @click='jumpTo(item.url)'>{{ mapName(item) }}</p>
        <a class="function function-2" @click="resetTomatoTimer(index)">R</a>
        <a class="function function-1" @click='click(index)'>{{ btnName }}</a>
      </li>
    </ol>
  </div>

</template>

<script>
const resetTime = 5 * 60;
const tomatoTime = 25 * 60;

export default {
  name: "ItemList",
  props: {
    title: String,
    btnName: String,
    done: Boolean,
    data: Array,
  },
  mounted() {
    setInterval(() => this.data.forEach(timeHandler), 1000);
  },
  methods: {
    change: function (index) {
      this.$emit('checkbox-change', index)
    },
    jumpTo: function (url) {
      if (url !== null) {
        window.open(url);
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

      // 如果指定了deadline, 则计算距离deadline的时间并设置不同的颜色
      if (item.deadline) {
        let delta = new Date(item.deadline) - new Date()
        const dayMs = 24 * 60 * 60 * 1000
        let urgent = Math.ceil(delta / dayMs)
        if (urgent > 0 && urgent <= 4) {
          return "specific-" + urgent
        }
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

      if (item.stage === "FOCUS" || item.stage === "REST") {
        showName = "【" + timeWithMin(item.timeSeconds) + "】" + showName
      }
      return showName;
    },
    resetTomatoTimer: function (index) {
      let item = this.data[index]
      item.stage = "FOCUS"
      item.timeSeconds = tomatoTime
    },
  }
}

function timeHandler(item) {
  // 注意: 每一秒钟此函数都会触发一次, 注意妥善处理后续情况
  if (item.stage === "FOCUS") {
    if (item.timeSeconds > 0) {
      item.timeSeconds -= 1
    } else {
      item.stage = "REST"
      item.timeSeconds = resetTime;
      new Notification("专注时间结束", {body: "完成一个番茄钟了, 休息一下吧~"})
    }
  } else if (item.stage === "REST") {
    if (item.timeSeconds > 0) {
      item.timeSeconds -= 1;
    } else {
      item.stage = "DONE"
      new Notification("休息结束", {body: ""})
    }
  }
}


function getWeekByDay(dayValue) {
  const today = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]; //创建星期数组
  return today[dayValue - 1];  //返一周中的某一天，其中1为周一
}


function timeWithMin(timeSeconds) {
  if (timeSeconds < 0) {
    return "00:00"
  }

  let m = Math.floor(timeSeconds / 60);
  let s = Math.floor(timeSeconds % 60);
  if (m < 10) {
    m = "0" + m;
  }
  if (s < 10) {
    s = "0" + s;
  }
  return m + ":" + s;

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
  border-left: 5px solid rgba(0, 32, 238, 0.94);
}

.specific-3 {
  border-left: 5px solid #eee916;
}

.specific-2 {
  border-left: 5px solid #ff7700;
}

.specific-1 {
  border-left: 5px solid #EE0000;
}

.specific {
  border-left: 5px solid #EE0000;
}

.subTask-1 {
  margin-left: 20px;
}

.subTask-2 {
  margin-left: 40px;
}

.subTask-3 {
  margin-left: 60px;
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

.function-1 {
  top: 4px;
  right: 5px;
}

.function-2 {
  top: 4px;
  right: 34px;
}

</style>