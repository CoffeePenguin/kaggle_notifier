# KaggleNotifier

KaggleNotifierは、Kaggleのコンペティションに関する情報をSlackに通知するBotです。

KaggleAPIを用いて情報を取得し、slackに通知します。
また、Herokuでのデプロイを前提としています。

大学研究室のslackで常駐するために個人的に作成したプログラムです。
## 機能

このBOTを利用することで、Kaggleのコンペティションを配信登録し、リーダーボードの自動配信スケジュールを設定することができます。さらに、KaggleNotifierにメンションすることで、さまざまなコマンドを利用できます。

## コマンド一覧

- `/startc [コンペ名]` : 指定されたコンペの配信登録をします。
- `/endc` : コンペの配信登録を解除します。
- `/checkc` : 配信登録中のコンペを確認します。
- `/checklb` : 配信登録中のコンペのリーダーボードを確認します。
- `/setdl [YYYY-MM-DD]` : 配信登録中のコンペの終了日を設定します。
- `/checkj` : 配信登録中のコンペの配信ジョブを確認します。
- `/delj` : 配信登録中のコンペの配信ジョブを削除します。
- `/help` : コマンド一覧を表示します。
- `/neko` : ランダムな猫の写真で癒やされます。

## インストール

1. このリポジトリをクローンします。
2. 必要な環境変数を設定します（`SLACK_TOKEN`, `DATABASE_URL2`など）。
3. KaggleAPIなどの依存関係をインストールします。

```bash
pip install -r requirements.txt
```

## デプロイ
このプログラムはHerokuにてデプロイするために設計されています。

(参考)Heroku CLIを使用してデプロイできます。
```
heroku create [アプリ名]
git push heroku master
```
