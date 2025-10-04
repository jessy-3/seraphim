import logging
import asyncio
import redis
import smtplib, ssl
from email.mime.text import MIMEText
from email.utils import formataddr
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("listen_for_commands")
logger.setLevel(logging.INFO)
main_logger = logging.getLogger('main')

REDIS_HOST = "redis"  # Use your Redis host
REDIS_PORT = 6379  # Use your Redis port

def semail(info):
    ret = True

    port = 465  # For SSL
    smtp_server = "mail.gmx.com"
    sender_email = "jessywang@gmx.com"  # Enter your address
    receiver_email = "xjwang@gmail.com"  # Enter receiver address
# my_user = ['xjwang@gmail.com','Eileen.wangxg@gmail.com']
    password = "my18mail"

    # logger = logging.getLogger('main')
#https://zhuanlan.zhihu.com/p/360322610

    ret = True
    try:
        mail_content = '''Hello, <br>
            The requested price info is: <br>
              <p>     {}</p>
          <br>
          Thank You
        '''.format(info)

        #msg = MIMEText(info, 'plain', 'utf-8')  # 填写邮件内容
        msg = MIMEText(mail_content, 'html', 'utf-8')  # 填写邮件内容
        msg['From'] = formataddr(["Vanilla System", sender_email])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
        msg['To'] = formataddr(["Jessy Wang",receiver_email])  # 括号里的对应收件人邮箱昵称、收件人邮箱账号
        msg['Subject'] = "Message from Vanilla"  # 邮件的主题，也可以说是标题

        server = smtplib.SMTP_SSL(smtp_server, port)  # 发件人邮箱中的SMTP服务器
        #server = smtplib.SMTP_SSL("imap.mya1mortgage.com", 143)  # 发件人邮箱中的SMTP服务器
        server.login(sender_email, password)  # 括号中对应的是发件人邮箱账号、邮箱授权码
        # print(sender_email, receiver_email, msg.as_string())
        server.sendmail(sender_email, receiver_email, msg.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 关闭连接
    except Exception as e:  # 如果 try 中的语句没有执行，则会执行下面的 ret=False
        print(e)
        logger.info(e)
        ret = False
    return ret


async def RedisTrigger():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    previous_btc_usd_data = None

    while True:
        btc_usd_data = r.hgetall("BTC/USD")
        btc_usd_data = {key.decode(): value.decode() for key, value in btc_usd_data.items()}
        
        if btc_usd_data != previous_btc_usd_data:
            print("BTC/USD data has changed:", btc_usd_data)
            previous_btc_usd_data = btc_usd_data

        time.sleep(5)  # Check every 5 seconds


async def send_command_to_bot(command: str):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    r.publish("bot_commands", command)

async def send_command_to_go(command: str):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    r.publish("go_commands", command)

async def listen_for_commands():
    print("Listening for web commands...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe("web_commands")

    while True:
        message = await asyncio.to_thread(pubsub.get_message)
        if message and message["type"] == "message":
            received_message = message["data"].decode("utf-8")
            if "|" in received_message:
                command, payload = received_message.split("|", 1)
                print(f"Bot received command: {command} and payload: {payload}")
                # Handle the command and payload
            else:
                command = received_message
                print(f"Bot received command / message: {received_message}")
            logger.info(f"Received: {received_message}")
        await asyncio.sleep(1)  # Add a sleep to avoid high CPU usage


if __name__ == '__main__':
    main_logger.info("Utils main is running")
    asyncio.run(listen_for_commands())
    # semail(minfo)
