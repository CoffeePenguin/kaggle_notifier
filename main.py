import io
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED


def send_slack_message(client, channel_id, text):
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=text
        )
    except SlackApiError as e:
        print(f"Error posting message: {e}")


def start_of_competition(competition):
    result = subprocess.run(
        ["kaggle", "competitions", "files", competition],
        stdout=subprocess.PIPE,
        text=True
    )

    print(result.stdout)

    if "403 - Forbidden" in result.stdout or "404 - Not Found" in result.stdout:
        return False
    else:
        return True


def get_leaderboard(competition):
    result = subprocess.run(
        ["kaggle", "competitions", "leaderboard",competition, "-v", "-s"],
        stdout=subprocess.PIPE,
        text=True
    )
    print(result.stdout)
    
    output = result.stdout
    df = pd.read_csv(StringIO(output))
    print(df)
    df['rank'] = range(1, len(df) + 1)
    df = df[['rank', 'teamName', 'score']]
    return df


def send_slack_leaderboard(client, channel_id, competition, day_alert):
    df = get_leaderboard(competition)
    df = df.to_csv(index=False)
    slack_df = "```"+df+"```"
    text = "🤖*KaggleコンペのLBのお知らせ*\n\n 配信登録中のKaggleコンペ\n`"+competition+"`\n"+day_alert+"\n\n👑*順位表*👑\n"+slack_df
    send_slack_message(client, channel_id, text)


def handle_start_competition(event_data, channel_id):
    registered_competition = Competition.query.first()

    if registered_competition is None: 
        compe = event_data.get('text', '').split("startc ")[1]

        if start_of_competition(compe):
            new_compe = Competition(compe)
            db.session.add(new_compe)
            db.session.commit()
            text = "kaggleコンペ:\n`" + compe + "`\nが配信設定されました.\n\nコンペの終了日を設定してください.\n/setdl [YYYY-MM-DD]"
            send_slack_message(client, channel_id, text)
        else:
            send_slack_message(client, channel_id, compe + "は存在しません.")     
    else:
        text = "既にkaggleコンペ\n`" + registered_competition.name + "`\nが配信登録されています。"
        send_slack_message(client, channel_id, text)

        
def handle_end_competition(channel_id):
    registered_competition = Competition.query.first()

    if registered_competition is None: 
        text = "現在、kaggleコンペは配信登録されていません. \n /startc で配信登録してください."
        send_slack_message(client, channel_id, text)
    else:
        text = "kaggleコンペ:\n`" + registered_competition.name + "`\nの配信登録を解除します。\nお疲れ様でした!"
        send_slack_message(client, channel_id, text)
        with app.app_context():  
            registered_competition = Competition.query.first()
            if registered_competition is not None:
                db.session.delete(registered_competition)
                db.session.commit()
            
            
def schedule_reminder(due_date, days_before):
    trigger_date = due_date - timedelta(days_before)
    return trigger_date

def check_due_date(due_date,days):
    before_due_date = due_date - timedelta(days)  
    return datetime.now() <= before_due_date 


def three_week_before(client, channel_id, competition):
    day_alert = "\n📅*終了まであと3週間!*📅\n\n現在の順位(LB)をお知らせします."
    send_slack_leaderboard(client, channel_id, competition, day_alert)


def two_week_before(client, channel_id, competition):
    day_alert = "\n📅*終了まであと2週間!*📅\n\n現在の順位(LB)をお知らせします."
    send_slack_leaderboard(client, channel_id, competition, day_alert)


def one_week_before(client, channel_id, competition):
    day_alert = "\n📅*終了まであと7日!*📅\n\n現在の順位(LB)をお知らせします."
    send_slack_leaderboard(client, channel_id, competition, day_alert)


def one_day_before(client, channel_id, competition):
    day_alert = "\n📅*終了まであと1日!*📅\n\n現在の順位(LB)をお知らせします."
    send_slack_leaderboard(client, channel_id, competition, day_alert)
    
    
def result(client, channel_id,competition):
    text = "\n☕*"+competition+"コンペが終了しました*☕\n皆さんお疲れ様でした!\n最終結果をコンペサイトで確認してください。\n入賞者の皆さんおめでとう！🎉"
    send_slack_message(client, channel_id, text)


def handle_check_competition(event_data, channel_id):
    registered_competition = Competition.query.first()
        
    if registered_competition is None:
        text = "現在、kaggleコンペは配信登録されていません.\n/startc で配信登録してください."
        send_slack_message(client, channel_id, text)
    else:
        text = "配信登録されているkaggleコンペ\n`" + registered_competition.name + "`\n"
        send_slack_message(client, channel_id, text)


def handle_check_leaderboard(event_data, channel_id):
    registered_competition = Competition.query.first()
    
    if registered_competition is None:
        text = "現在、kaggleコンペは配信登録されていません. \n /startc で配信登録してください."
        send_slack_message(client, channel_id, text)
    else:
        send_slack_leaderboard(client, channel_id,registered_competition.name, "")


def handle_set_deadline(event_data, channel_id):  
    registered_competition = Competition.query.first()
    
    due_date_str = event_data.get('text', '').split("/setdl ")[1].strip()
    ok = True

    if len(due_date_str) != 10 or due_date_str[4] != "-" or due_date_str[7] != "-":
        text = "期日は'YYYY-MM-DD'形式で入力してください."
        send_slack_message(client, channel_id, text)
        ok = False

    if registered_competition is None:
        text = "現在、kaggleコンペは配信登録されていません. \n /startc で配信登録してください."
        send_slack_message(client, channel_id, text)
        ok = False

    if ok:
        setup_scheduler(due_date_str, channel_id)


def handle_check_jobs(event_data, channel_id):
    global scheduler
    
    jobs = scheduler.get_jobs()
    job_list = [str(job) for job in jobs]
    jobs_text = "\n".join(job_list)

    if jobs_text == "":
        text = "現在、スケジュールされている配信ジョブはありません."
        send_slack_message(client, channel_id, text)
    else:
        jobs_text = "```" + jobs_text + "```"
        send_slack_message(client, channel_id, jobs_text)


def handle_delete_job(event_data, channel_id):
    scheduler.remove_all_jobs()
    JobModel.query.delete()
    db.session.commit()
    send_slack_message(client, channel_id, "スケジュールされている配信ジョブを全て削除しました.")


def handle_cat_command(event_data, channel_id):
    response = requests.get('https://api.thecatapi.com/v1/images/search')
    data = response.json()
    cat_image_url = data[0]['url']
    image_response = requests.get(cat_image_url, stream=True)
    
    if image_response.status_code == 200:
        with open('cat_image.jpg', 'wb') as f:
            image_response.raw.decode_content = True
            shutil.copyfileobj(image_response.raw, f)
    else:
        text = "画像がダウンロードできませんでした."
        send_slack_message(client, channel_id, text)

    try:
        result = client.files_upload_v2(
            channel=channel_id,
            file="cat_image.jpg",
            title="ランダム猫",
            initial_comment="meow🐱"
        )
        assert result["file"]  
    except SlackApiError as e:
        print(f"Got an error: {e.response['error']}")


def save_job_to_db(job_id, func, run_date, args):
    job = JobModel(id=job_id, func=func, run_date=run_date, args=args)
    return job


def restore_jobs():
    with app.app_context():
        jobs = JobModel.query.all()
        for job in jobs:
            scheduler.add_job(eval(job.func), 'date', run_date=job.run_date, id=job.id, args=job.args)


def setup_scheduler(due_date_str, channel_id):
    global scheduler
    
    registered_competition = Competition.query.first()
    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
    due_date = due_date.replace(hour=12, minute=00,second=0)
    
    scheduler.remove_all_jobs()
    JobModel.query.delete()
    db.session.commit()  
    
    if check_due_date(due_date,21): 
        threeweek = schedule_reminder(due_date, 21)
        scheduler.add_job(three_week_before, 'date', run_date=threeweek,id='three_week',args=[client, channel_id, registered_competition.name])
        # ジョブをデータベースにも保存
        job1 = save_job_to_db('three_week', 'three_week_before', threeweek, [client, channel_id, registered_competition.name])
        db.session.add(job1)
    
    if check_due_date(due_date,14):
        twoweek = schedule_reminder(due_date, 14)
        scheduler.add_job(two_week_before, 'date', run_date=twoweek,id='two_week',args=[client, channel_id, registered_competition.name])
        job2 = save_job_to_db('two_week', 'two_week_before', twoweek, [client, channel_id, registered_competition.name])
        db.session.add(job2)
    
    if check_due_date(due_date,7):    
        aweek = schedule_reminder(due_date, 7)
        scheduler.add_job(one_week_before, 'date', run_date=aweek,id='a_week',args=[client, channel_id, registered_competition.name])
        job3 = save_job_to_db('a_week', 'one_week_before', aweek, [client, channel_id, registered_competition.name])
        db.session.add(job3)

    if check_due_date(due_date,1):
        aday = schedule_reminder(due_date, 1)
        scheduler.add_job(one_day_before, 'date', run_date=aday,id='a_day',args=[client, channel_id, registered_competition.name])
        job4 = save_job_to_db('a_day', 'one_day_before', aday, [client, channel_id, registered_competition.name])
        db.session.add(job4)

    if check_due_date(due_date,0):
        deadline = schedule_reminder(due_date, 0)
        scheduler.add_job(result, 'date', run_date=deadline,id='result',args=[client, channel_id, registered_competition.name])
        job5 = save_job_to_db('result', 'result', deadline, [client, channel_id, registered_competition.name])
        db.session.add(job5)
    
    db.session.commit()

    jobs = scheduler.get_jobs()
    job_list = [str(job) for job in jobs]
    jobs_text = "\n".join(job_list)
    due_date_str = due_date.strftime("%Y-%m-%d %H:%M:%S")
    
    if jobs_text == "":
        text = "期日が現在の日付より過去の日付になっていませんか？もう一度設定してください。"
        send_slack_message(client, channel_id, text)
    else:
        jobs_text = "```" + jobs_text + "```"
        text = "Kaggleコンペ:\n`" + registered_competition.name + "`\n終了日を" + due_date_str + "に設定しました.\n\nLBの配信スケジュールは以下の通りです.\n\n" + jobs_text + "\n 頑張りましょう！"
        send_slack_message(client, channel_id, text)

                
def job_executed_listener(event):
    job_id = event.job_id
    job = JobModel.query.get(job_id)
    if job:
        db.session.delete(job)
        db.session.commit()


load_dotenv()  
slack_token = os.getenv('SLACK_TOKEN') 
client = WebClient(token=slack_token)

class SingletonScheduler:
    _scheduler = None
    @staticmethod
    def get_scheduler():
        if SingletonScheduler._scheduler is None:
            SingletonScheduler._scheduler = BackgroundScheduler()
        return SingletonScheduler._scheduler

scheduler = SingletonScheduler.get_scheduler()
scheduler.start()
scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL2')
db = SQLAlchemy(app)
    
class Competition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    def __init__(self, name):
        self.name = name

class JobModel(db.Model):
    id = db.Column(db.String(), primary_key=True)
    func = db.Column(db.String())
    run_date = db.Column(db.DateTime())
    args = db.Column(db.PickleType())

with app.app_context():
    db.create_all()
    jobs = JobModel.query.all()
    for job in jobs:
        scheduler.add_job(eval(job.func), 'date', run_date=job.run_date, id=job.id, args=job.args)
        print(job.id, job.func, job.run_date, job.args)


@app.route('/slack/events', methods=['POST'])
def handle_event():
    data = request.json

    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    elif "event" in data:
        event_data = data["event"]
        if event_data["type"] == "app_mention":
            channel_id = event_data["channel"]

            if "/startc " in event_data.get('text', ''):
                handle_start_competition(event_data, channel_id)

            elif "/endc" in event_data.get('text', ''):
                handle_end_competition(channel_id)

            elif "/checkc" in event_data.get('text', ''):
                handle_check_competition(event_data, channel_id)

            elif "/checklb" in event_data.get('text', ''):
                handle_check_leaderboard(event_data, channel_id)

            elif "/setdl " in event_data.get('text', ''):
                handle_set_deadline(event_data, channel_id)

            elif "/checkj" in event_data.get('text', ''):
                handle_check_jobs(event_data, channel_id)
            
            elif "/delj" in event_data.get('text', ''):
                handle_delete_job(event_data, channel_id)
            
            elif "/help" in event_data.get('text', ''):
                with open('help.txt', 'r') as f:
                    help = f.read()
                text = "*KaggleNotifierのコマンド一覧*\n\n```"+help+"```"
                send_slack_message(client,channel_id,text)
                
            elif "/neko" in event_data.get('text', ''):
                handle_cat_command(event_data, channel_id)
                    
            else:
                send_slack_message(client, channel_id, "そのコマンドは存在しません.\n/helpでコマンド一覧を確認できます.")

    return Response(), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(port=port)