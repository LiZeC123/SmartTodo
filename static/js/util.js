/**
 * 替换所有匹配exp的字符串为指定字符串
 * @param exp 被替换部分的正则
 * @param newStr 替换成的字符串
 */
String.prototype.replaceAll = function (exp, newStr) {
    return this.replace(new RegExp(exp, "gm"), newStr);
};

/**
 * 原型：字符串格式化
 * @param args 格式化参数值
 */
String.prototype.format = function (args) {
    let result = this;
    if (arguments.length < 1) {
        return result;
    }

    let data = arguments; // 如果模板参数是数组
    if (arguments.length === 1 && typeof (args) == "object") {
        // 如果模板参数是对象
        data = args;
    }
    for (const key in data) {
        const value = data[key];
        if (undefined !== value) {
            result = result.replaceAll("\\{" + key + "\\}", value);
        }
    }
    return result;
};


function selectFile() {
    document.getElementById("file_selector").click();
}

function uploadFile() {
    // http://www.feingto.com/?p=14158
    const file_obj = document.getElementById("file_selector").files[0];
    if (file_obj) {
        const url = "/smart-todo/file/doUpload";
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
    window.open("/smart-todo/backup");
}

function updateLogs() {
    window.open("/smart-todo/log.txt");
}

function downCenter() {
    window.open("/smart-todo/file");
}