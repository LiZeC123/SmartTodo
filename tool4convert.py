# -*- coding: UTF-8 -*-
import getopt
import sys


def update_web_files():
    import shutil
    shutil.rmtree('static')
    shutil.copytree("web/dist", "static")


def print_help():
    print("tool4convert: 数据转换工具. 安全的初始化和转换项目的数据")
    print("-u   更新前端文件")


if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], 'hcur:')
    for opt_name, opt_value in opts:
        if opt_name in ('-h',):
            print_help()
            exit()
        if opt_name in ('-u',):
            update_web_files()
            exit()
    # 如果没有执行以上的任何一个分支, 则输入帮助信息
    print_help()
