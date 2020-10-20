# -*- coding: UTF-8 -*-
import getopt
import sys



def print_help():
    print("tool4convert: 数据转换工具. 安全的初始化和转换项目的数据")
    print("--convert/-c  数据初始化和数据转换")
    print("--backup/-b   数据邮件备份")
    print("--help/-h     显示此帮助信息")


if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], '-h-c-b-i', ['help', 'convert', 'backup', 'init'])
    for opt_name, opt_value in opts:
        if opt_name in ('-h', '--help'):
            print_help()
            exit()
        if opt_name in ("-i", '--init'):
            # create_init_database()
            exit()
        if opt_name in ('-c', '--convert'):
            update_date_structure()
            exit()
        if opt_name in ('-b', '--backup'):
            # backup()
            exit()
    # 如果没有执行以上的任何一个分支, 则输入帮助信息
    print_help()
