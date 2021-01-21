echo "杀死当前的Python进程"
pid=$(ps x | grep "python3.8 app.py" | grep -v grep | awk '{print $1}')
kill "$pid"

echo "更新数据结构"
python3 ./tool4convert.py -c


echo "重启Python进程"
nohup python3.8 app.py > log.txt 2>&1 &