import yagmail


def sendmail(subject, body, user_file, logfile=None):
    sender = ''
    password = ''
    res = ''

    yag = yagmail.SMTP(user=sender, password=password, host='smtp.qq.com', smtp_ssl=True)
    return yag.send(to=res, subject=subject, contents=[body, user_file, logfile])


def send_mail(self):
    user_file = f"database/{self.username}.json"
    return sendmail(subject=f"用户{self.username}的数据备份", body="请注意查看附件", user_file=user_file)
