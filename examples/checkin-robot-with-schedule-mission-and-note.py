#!/usr/bin/env python3
import itchat, datetime, schedule, time, threading, re
from itchat.content import *
from peewee import *

db = MySQLDatabase('xxxxxx', user='xxxxxx', password='xxxxxx', charset='utf8mb4')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    username = CharField(unique=True,max_length=100)
    openid = CharField(null=True,max_length=100)
    count = IntegerField(default=1)
    updated_date = DateTimeField(default=datetime.datetime.now)
    created_date = DateTimeField(default=datetime.datetime.now)

class Note(BaseModel):
    user = ForeignKeyField(User, related_name='notes')
    message = TextField()
    created_date = DateTimeField(default=datetime.datetime.now)

@itchat.msg_register(TEXT, isFriendChat=True, isGroupChat=True, isMpChat=True)
def simple_reply(msg):
    if not 'helper' in msg['Text']: return
    friend = itchat.search_friends(nickName=msg['ActualNickName'])
    if friend:
        print(friend)
    print(msg)
    response = response_handler(msg)
    print(response)
    return response

def response_handler(msg):
    response = ''
    if '签到' in msg['Text'] and 'helper' in msg['Text']:
        response = check_in(msg) + '\n用户: %s' % msg['ActualNickName']
        print(re.split('\s+',msg['Text'].replace('\u2005',' '),2))
        if len(re.split('\s+',msg['Text'].replace('\u2005',' '),2)) > 2:            
            response += '\n' + add_note(msg)
    elif '日志' in msg['Text'] and 'helper' in msg['Text'] and len(re.split('\s+',msg['Text'].replace('\u2005',' '),2)) > 2:
        response = add_note(msg) + '\n用户: %s' % msg['ActualNickName']
    elif '检查' in msg['Text'] and 'helper' in msg['Text']:
        response = print_unchecked_username(get_unchecked_member())
    elif '清理' in msg['Text'] and 'helper' in msg['Text']:
        #response = delete_unchecked_member(get_unchecked_member())
        response = '每日23：59清理未签到成员！'
    elif '排行' in msg['Text'] and 'helper' in msg['Text']:
        #response = print_top_members()
        response = '每日23：00公布签到排行榜！'
    elif '计划任务' in msg['Text'] and 'helper' in msg['Text'] and 'xxxxxx' in msg['ActualUserName']:
        run_threaded(daily_job)
        response = '开始自动执行每日计划任务！'
    else:
        response = '未定义操作！'
    return response

def check_in(msg):
    if User.select().where(User.openid == msg['ActualUserName']).count() < 1:
        User.create(username=msg['ActualNickName'], openid=msg['ActualUserName'])
        return '开始你的100天挑战吧！中断1天就会被踢出袄~'
    if User.get(User.openid == msg['ActualUserName']).updated_date.date().strftime("%Y-%m-%d") < datetime.datetime.now().strftime("%Y-%m-%d"):
        User.update(updated_date = datetime.datetime.now(),count=User.count + 1).where(User.openid == msg['ActualUserName']).execute()
        return '签到成功！' + '\n时间: %s' % User.get(User.openid == msg['ActualUserName']).updated_date
    return '您今日已签到！'

def add_note(msg):
    if User.select().where(User.openid == msg['ActualUserName']).count() > 0:
        this_user = User.get(User.openid == msg['ActualUserName'])
        Note.create(user=this_user, message=re.split('\s+',msg['Text'].replace('\u2005',' '),2)[2])
        return '日志记录成功！\n内容: %s' % re.split('\s+',msg['Text'].replace('\u2005',' '),2)[2]
    return '记录日志时发生错误，您还没有签到过吗？'

def get_unchecked_member():
    itchat.get_chatrooms(update=True)
    chatroom = itchat.search_chatrooms('100days')[0]
    #print(chatroom)
    itchat.update_chatroom(chatroom['UserName'],detailedMember=True)
    memberList = []
    print(datetime.datetime.now().strftime("%Y-%m-%d"))
    unchecked_users = User.select().where(User.updated_date < datetime.datetime.now().strftime("%Y-%m-%d"))
    for user in unchecked_users:
        print(user.username)
        print([m for m in chatroom['MemberList'] if m['UserName'] == user.openid])
        if [m for m in chatroom['MemberList'] if m['UserName'] == user.openid]:
            memberList.append([m for m in chatroom['MemberList'] if m['UserName'] == user.openid]
[0])
    return memberList

def print_top_members():
    memberList = []
    top_members = User.select().order_by(User.count.desc()).limit(10)
    content = '签到排行：\n'
    for member in top_members:
        content += member.username + ':' + str(member.count) + '\n'
    return content

def auto_print_top_members():
    auto_reply_result(print_top_members())

def auto_remove_members():
    auto_reply_result(delete_unchecked_member(get_unchecked_member()))

def auto_reply_result(method):
    response = method
    chatroom = itchat.search_chatrooms('100days')[0]
    print(chatroom['UserName'])
    itchat.send(response, toUserName=chatroom['UserName'])

def record_schedule():
    print('Schedule running...')

def print_unchecked_username(memberList):
    print(memberList)
    if not memberList:
        return '所有成员均已签到！'
    content = '未签到用户：\n'
    for member in memberList:
        content += member['NickName'] + '\n'
    print(content)
    return content

def delete_unchecked_member(memberList):
    if datetime.datetime.now().hour < 23: return '请在23时以后清理未签到成员！'
    itchat.get_chatrooms(update=True)
    chatroom = itchat.search_chatrooms('100days')[0]
    print(chatroom)
    itchat.update_chatroom(chatroom['UserName'],detailedMember=True)
    itchat.delete_member_from_chatroom(chatroom['UserName'], memberList)
    return '未签到成员清除完毕！'

def daily_job():
    schedule.every(10).seconds.do(run_threaded,record_schedule)
    schedule.every().day.at("23:00").do(run_threaded,auto_print_top_members)
    schedule.every().day.at("23:50").do(run_threaded,auto_remove_members)
    while True:
        schedule.run_pending()
        time.sleep(10)

def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()

itchat.auto_login(enableCmdQR=2,hotReload=True)

run_threaded(itchat.run)
