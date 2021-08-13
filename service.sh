function compileService() {
  docker-compose build
}

function runService() {
  docker-compose up -d
}

function stopService() {
  docker-compose down
}

function backup() {
  echo "Zip SmartTodo Data"
  zip -r SmartTodo.zip config/ data/database data/log data/notebase > /dev/null
  echo "Done."
}

function update() {
  git pull
}

if [ "$1"x == "start"x ]; then
  compileService
  runService
elif [ "$1"x == "compile"x ]; then
  compileService
elif [ "$1"x == "run"x ]; then
  runService
elif [ "$1"x == "stop"x ]; then
  stopService
elif [ "$1"x == "restart"x ]; then
  compileService
  stopService
  runService
elif [ "$1"x == "backup"x ]; then
  backup
elif [ "$1"x == "update"x ]; then
  update
else
  echo "无效的参数: $1"
  echo ""
  echo "用法: ./service [参数]"
  echo "参数可以选择以下值:"
  echo "start     编译并启动项目"
  echo "stop      停止项目"
  echo "restart   重启项目"
  echo "compile   只编译项目"
  echo "run       直接运行项目"
  echo "backup    备份数据文件"
  echo ""
fi
