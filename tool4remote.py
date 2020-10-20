from concurrent.futures.thread import ThreadPoolExecutor

# 本模块操作远程网盘相关的内容
# - [在Debian/Ubuntu上使用rclone挂载OneDrive网盘](https://www.moerats.com/archives/491/)
# - [OneDrive 挂载为本地磁盘Ubuntu](https://blog.csdn.net/drowedfish/article/details/89276931)
# - [Rclone 进阶使用手册：常用命令参数](https://www.alenws.com/53661.html)
remote_exec = ThreadPoolExecutor(max_workers=2)


def __copy2remote(file: str):
    """使用rclone复制文件"""
    # remote_name = get_remote_info()['name']
    # cmd = f"rclone copy {file} {remote_name}"
    # logger.info(f"Do Remote Command: {cmd}")
    # os.system(cmd)


def copy2remote(file: str):
    remote_exec.submit(__copy2remote, file)


def __test():
    print("In Test")
    raise ValueError


if __name__ == '__main__':
    copy2remote("app.py")
