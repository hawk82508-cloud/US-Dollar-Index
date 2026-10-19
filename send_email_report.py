import os
import sys
import smtplib
import datetime
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header

def send_daily_email(html_path='index.html'):
    sender_email = os.environ.get('GMAIL_USER')
    sender_password = os.environ.get('GMAIL_APP_PASSWORD')

    if not sender_email or not sender_password:
        print("Notice: GMAIL_USER or GMAIL_APP_PASSWORD not set in GitHub Secrets. Skipping email delivery.")
        return

    recipients = ['hawk82508@gmail.com', 'skfg7381@skl.com.tw']
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    today_num = today_str.replace('-', '')

    daily_csv = 'raw_daily.csv'
    close_text = ""
    p1_text = ""
    p2_text = ""
    if os.path.exists(daily_csv):
        try:
            df = pd.read_csv(daily_csv)
            last_row = df.iloc[-1]
            close_text = f"{float(last_row['收盤價']):,.2f}"
            today_str = str(last_row['時間'])
            today_num = today_str.replace('-', '')
            last_11 = df.tail(11)
            h11 = float(last_11['最高價'].max())
            l11 = float(last_11['最低價'].min())
            p1_text = f"{((2*h11 + l11)/3.0):,.2f}"
            p2_text = f"{((h11 + 2*l11)/3.0):,.2f}"
        except Exception as e:
            print(f"Error reading daily csv: {e}")

    subject = f"【DXY 美元指數盤後通道分析】{today_str} 多週期與次期前瞻雙軌線"

    body_text = f"""您好：

這是 {today_str} 美元指數 (US Dollar Index, DXY) 的每日盤後技術分析自動推播。

【今日盤後重點速報】
* 基準交易日：{today_str}
* 美元指數收盤：{close_text}
* 次日 11 期前瞻第 1 點 (上軌)：{p1_text}
* 次日 11 期前瞻第 2 點 (下軌)：{p2_text}

【附件檔案說明】
隨信附上獨立離線網頁檔案：DXY_{today_num}_Report.html
下載後檔案副檔名即為標準 .html，在 Windows / Mac / 手機上直接點擊即可使用 Google Chrome 開啟完整互動式走勢圖！

本郵件由 GitHub Actions 自動化系統排程發送。
"""

    msg = MIMEMultipart('mixed')
    msg['From'] = f"DXY Channel Auto System <{sender_email}>"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = Header(subject, 'utf-8').encode()

    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

    if os.path.exists(html_path):
        clean_filename = f"DXY_{today_num}_Report.html"
        with open(html_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Type', 'application/octet-stream', name=clean_filename)
        part.add_header('Content-Disposition', 'attachment', filename=clean_filename)
        msg.attach(part)
        print(f"Attached clean HTML file: {clean_filename}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
        print(f"Successfully sent daily email report to {recipients}")
    except Exception as e:
        print(f"Notice: Failed to send email: {e}")

if __name__ == '__main__':
    try:
        send_daily_email()
    except Exception as e:
        print(f"Error in send_daily_email: {e}")
