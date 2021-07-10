# -*- coding: UTF-8 -*-
import getopt
import os
import sys


def update_web_files():
    import shutil
    shutil.rmtree('static')
    shutil.copytree("web/dist", "static")


def commit_web_file():
    os.system('git add static/')
    os.system('git commit -m "更新前端文件"')


def static_file_updated():
    try:
        # 1. 遍历源代码, 找到最近更新的文件时间
        st = 0.0
        for root, dirs, files in os.walk("web/src"):
            for file in files:
                full_path = os.path.join(root, file)
                st = max(os.path.getmtime(full_path), st)

        # 2. 比对目标目录的修改时间
        dt = os.path.getmtime("static")
        return dt > st
    except FileNotFoundError as e:
        print(f"Check Static File Update Time Error: {e}")
        # 文件不存在时都重新生成文件
        # 如果出现没有考虑到的异常, 则应该使程序崩溃
        return False


def print_help():
    print("tool4convert: 数据转换工具. 安全的初始化和转换项目的数据")
    print("-u   更新前端文件")


if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], 'hcur:', ["test", ])
    for opt_name, opt_value in opts:
        if opt_name in ('-h',):
            print_help()
            exit()
        if opt_name in ('-u',):
            if static_file_updated():
                update_web_files()
                commit_web_file()
            else:
                print("Error: web file is not updated.")
            exit()
        if opt_name in ("--test",):
            print(static_file_updated())
            exit()
    # 如果没有执行以上的任何一个分支, 则输入帮助信息
    print_help()
