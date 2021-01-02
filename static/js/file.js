function updateTodo(data) {
    const tStr = "<li class='{type}' id='li-active'><input type='checkbox' onchange='update({id})' />" +
        "<p id='p-{id}' onclick='edit(\"{url}\")'>{showName}</p>" +
        "<a onclick='toRemote({id})'>↑</a></li>";
    const dictFunc = function (item) {
        return {
            "type": item.itemType, "id": item.id,
            "url": item.url, "showName": item.showName,
        }
    };
    updateTemplate(data, document.getElementById("todoCount"),
        document.getElementById("todoList"), tStr, dictFunc);
}

function updateHTML(data) {
    updateTodo(fillShowName(data.todo));
    updateDone(fillShowName(data.done));
}

function fetchData(callBack) {
    $.post("/file/list", callBack);
}
