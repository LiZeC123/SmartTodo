function commitGlobalTodo() {
    commitNewTodo(undefined)
}

function commitNoteTodo() {
    const nid = /note\/(\d+)/.exec(document.URL)[1];
    commitNewTodo(nid);
}

function commitNewTodo(nid) {
    const title = document.getElementById("title");
    const select = document.getElementById("itemType");
    if (title.value.trim() === "") {
        alert("内容不能为空");
    } else if (/set (.+)/.test(title.value) || /fun (.+)/.test(title.value)) {
        //$.post("/op", {"cmd": title.value}, load)
    } else {
        let data = parseTitleToData(title, select);
        if (nid !== undefined) {
            data.parent = nid;
        }

        axios.post("/item/add", data).then(reload)

        const form = document.getElementById("form");
        form.reset();
    }
}

function parseTitleToData(title, select) {
    const values = title.value.split(" ");

    let data = {
        "itemType": select.options[select.selectedIndex].value,
    };
    if (values.length === 1) {
        data.name = title.value;
    } else {
        data.name = values[0];
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

    return data;
}

function fillShowName(data) {
    for (let i = 0; i < data.length; i++) {
        data[i].showName = data[i].name;

        // 只要包含URL, 先设置为连接类型
        if (data[i].url !== null) {
            data[i].showName = "【链接】" + data[i].name;
        }

        // 如果是便签, 加入便签标记
        if (data[i].itemType === "note") {
            data[i].itemType = "single";
            data[i].showName = "【便签】" + data[i].name;
        }

        // 如果是文件, 展示文件原始连接和现在链接的标记
        if (data[i].itemType === "file") {
            data[i].itemType = "single";
            data[i].showName = "【文件】" + data[i].name;
        }

        // ---------- 以下为附加属性 ----------------------
        // 在showName的基础上加入属性, 注意先后顺序

        // 如果有截止时间, 加入截止日期标记
        if (data[i].deadline !== null) {
            // 截止日期只展示日期部分
            data[i].showName = "【" + data[i].deadline.split(" ")[0] + "】" + data[i].showName
        }

        // 如果是工作时间段, 加入工作时间段的标记
        if (data[i].work) {
            data[i].showName = "【工作】" + data[i].showName;
        }

        if (data[i].repeatable) {
            data[i].itemType = "repeatable"
        }

        if (data[i].specific) {
            data[i].itemType = "specific";
            data[i].showName = "【" + getWeekByDay(data[i].specific) + "】" + data[i].showName
        }

        // 如果是紧急任务, 则改变样式, 变成更醒目的红色
        if (data[i].urgent >= 0 && data[i].urgent <= 3) {
            data[i].itemType = "specific-" + data[i].urgent;
        }
    }
    return data;
}

function getWeekByDay(dayValue) {
    const today = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]; //创建星期数组
    return today[dayValue - 1];  //返一周中的某一天，其中1为周一
}

function reload(nid) {
    axios.post("/items/todo").then(response => {
        vm.todo = fillShowName(response.data.todo)
        vm.done = fillShowName(response.data.done)
        vm.old = fillShowName(response.data.old)
    })
}


function selectFile() {
    document.getElementById("file_selector").click();
}

function uploadFile() {
    // http://www.feingto.com/?p=14158
    const file_obj = document.getElementById("file_selector").files[0];
    if (file_obj) {
        const url = "/file/doUpload";
        const form = new FormData();
        form.append("myFile", file_obj);
        const xhr = new XMLHttpRequest();
        xhr.onload = load; // 上传成功后的回调函数
        xhr.onerror = load;// 上传失败后的回调函数
        xhr.open("POST", url, true);
        xhr.send(form);
    } else {
        alert("请先选择文件后再上传")
    }
}

function backUpData() {
    window.open("/backup");
}

function updateLogs() {
    window.open("/log.txt");
}

function downCenter() {
    window.open("/file");
}

function doLogout() {
    window.location.href = '/logout'
}


new Vue({
    el: "#footerContainer",
    data: {
        year: 2021,
        version: "2.1.0"
    }
})

new Vue({
    el: "#footerFunctionContainer",
    data: {
        isAdmin: true
    }
})