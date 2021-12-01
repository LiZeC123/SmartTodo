
function backup() {
  echo "Zip SmartTodo Data"
  zip -r SmartTodo.zip config/ data/database data/log data/notebase > /dev/null
  echo "Done."
}

function update() {
  git pull
  docker-compose down
  docker pull ghcr.io/lizec123/smart-todo
  docker-compose up -d
}

if [ "$1"x == "backup"x ]; then
  backup
elif [ "$1"x == "update"x ]; then
  update
else
  echo "无效的参数: $1"
  echo ""
  echo "用法: ./service [参数]"
  echo "参数可以选择以下值:"
  echo "backup    备份数据文件"
  echo "update    更新项目代码并重启"
  echo ""
fi