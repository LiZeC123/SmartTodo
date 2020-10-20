function postAction(nid) {
    if (title.value.trim() === "") {
        alert("内容不能为空");
    } else if (/set (.+)/.test(title.value)) {
        $.post("/smart-todo/op", {"cmd": title.value}, load)
    } else {
        const title = document.getElementById("title");
        const select = document.getElementById("itemType");
        let data = parseTitleToData(title, select);
        if (nid !== undefined) {
            data.parent = nid;
        }

        $.post("/smart-todo/item/add", data, function () {
            load();
        });

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

function remove(id) {
    $.post("/smart-todo/item/delete", {"id": id}, load);
}

function update(id) {
    $.post("/smart-todo/item/update", {"id": id}, load);
}

function sticky(id) {
    $.post("/smart-todo/item/old", {"id": id}, load);
}

function edit(name) {
    if (name !== "null") {
        // 不指定任何参数才是正常的打开新标签页
        window.open(name);
    }
}

function toRemote(id) {
    $.post("/smart-todo/file/toRemote", {"id": id}, load);
}

function load() {
    const callBack = function (collection) {
        const data = fillShowName(JSON.parse(collection));
        console.log(data);
        updateHTML(data);
    };

    fetchData(callBack);
}


function updateDone(data) {
    const tStr = "<li id='li-normal'><input type='checkbox' onchange='update({id})' checked='checked' />" +
        "<p id='p-{id}' onclick='edit(\"{url}\")'>{showName}</p>" +
        "<a href='javascript:remove({id})'>-</a></li>";
    const dictFunc = function (item) {
        return {
            "type": item.itemType, "id": item.id,
            "url": item.url, "showName": item.showName,
        }
    };
    updateTemplate(data, document.getElementById("doneCount"),
        document.getElementById("doneList"), tStr, dictFunc);
}

function updateTemplate(data, dCount, dList, tStr, dictFunc) {
    if (data !== null) {
        let tCount = 0;
        let todoString = "";
        for (let i = 0; i < data.length; i++) {
            const dict = dictFunc(data[i]);
            todoString += tStr.format(dict);
            tCount++;
        }

        dCount.innerHTML = tCount.toString();
        dList.innerHTML = todoString;
    } else {
        dCount.innerHTML = "0";
        dList.innerHTML = "";
    }
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


$(function () {
    load();
});