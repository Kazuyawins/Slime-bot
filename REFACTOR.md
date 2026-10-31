# 機能別ファイル構成

起動方法は従来どおり `python bot.py` です。Python依存関係は `requirements.txt` のままです。

| ファイル | 担当 |
| --- | --- |
| `bot.py` | 機能の読み込みと起動 |
| `slime/runtime.py` | Discord BotインスタンスとIntents |
| `slime/config.py` | 全設定の読み書き、共有状態 |
| `slime/links.py` | 10種類のSNS変換、リンク削除・更新ボタン |
| `slime/administration.py` | チャンネル/ログ/入退室設定、バックアップ、代理送信、既存testコマンド |
| `slime/moderation.py` | スパム設定と処分 |
| `slime/responses.py` | 完全一致返信の登録・削除・照合 |
| `slime/general.py` | help/ping/avatar/history、日英ヘルプ |
| `slime/roles.py` | 絵文字ロール取得パネル |
| `slime/captcha.py` | CAPTCHA画像・モーダル・パネル |
| `slime/logging_events.py` | メッセージ/チャンネル/スレッド/エラーのログ |
| `slime/members.py` | 入退室イベント |
| `slime/notifications.py` | 日付変更通知タスク |
| `slime/messages.py` | スパム → 完全一致返信 → SNS変換のイベント制御 |
| `slime/lifecycle.py` | 接続後の永続View登録・コマンド同期・タスク開始、共通コマンドエラー処理 |
| `slime/web_server.py` | 稼働確認用HTTPエンドポイント |

設定ファイル名・JSON形式・環境変数・相対保存先は変更していません。従来と同じ作業ディレクトリで実行してください。
`config`をモジュールとして参照するため、`/importconfig`で辞書が再代入されても各機能に反映されます。
実際のBot起動やDiscordへの送信はオフラインテストでは実行していません。

## テスト

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```
