echo "杀死当前的Python进程"
pid=$(pgrep -f "python3.8 app.py")
kill "$pid"

echo "更新数据结构"
python3 ./tool4convert.py -c


echo "重启Python进程"
nohup python3.8 app.py > log.txt 2>&1 &