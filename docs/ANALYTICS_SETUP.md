# adapt-base解析運用

管理アカウント: adaptbasejp@gmail.com。サイト計測はGA4、検索分析はSearch Console。測定ID G-ZMGS0R556P、プロパティID 558518317。2026-10-12、本番のページビューとsupport_navigation受信を確認。Search ConsoleはHTMLタグでhttps://adapt-base.com/の所有権確認完了。

## Google側の登録
1. 指定アカウントでGA4のアカウント・プロパティを作成。ウェブストリームのURLはhttps://adapt-base.com/。タイムゾーンはAsia/Tokyo、通貨はJPYを事業の基準案とする。規約は所有者が確認する。
2. 測定IDをhugo.tomlのparams.analytics.ga4MeasurementIDへ設定する。数値のプロパティIDはAPI集計用に別途記録する。
3. 拡張計測のフォーム操作・ページ履歴・外部リンクなどは当初オフ。サイト独自イベントと通常のページビューだけで開始し、重複や個人情報を含むURLの送信を避ける。Googleシグナル・広告目的の機能は利用しない。
4. Search Consoleはadapt-base.comのドメインプロパティを推奨。発行されるTXTレコードをCloudflare DNSに追加して所有権確認。サイトマップはhttps://adapt-base.com/sitemap.xml。DNS操作は検証値取得後に行う。URLプレフィックス方式ならHTMLタグの検証値をparams.analytics.searchConsoleVerificationへ設定できる。
5. GA4のリアルタイムでページ閲覧、support_navigation、contact_email_clickを確認。許可前・拒否時・プレビューではGA4が読み込まれないことも確認する。

## 計測仕様
本番ブランチmainかつホストadapt-base.com/www.adapt-base.comだけを対象。許可したブラウザのみGoogleタグを読み込む。クエリ文字列・フラグメント・参照元URLは送信しない。メール本文・送信者情報は取得しない。拒否時は同意を停止しGA Cookie削除を試みる。ブラウザ設定によってCookie削除に制約がある。メールクリックは実送信・成約と区別する。

## 外部取得
GA4 Data APIとSearch Console APIの集計データをPowerShellまたはAWSのジョブから取得する。Google CloudプロジェクトでAPI有効化と認証設定が必要だが、GCP上の計算サービスやBigQueryは必須ではない。

初期はPowerShellで日付・ページ・流入元・イベント数と検索のクリック/表示/CTR/順位を取得し、CSV/JSONへ出力。定期実行はEventBridge Scheduler→Lambda→S3を候補にする。AWS未設定につき自動処理は未稼働。秘密情報はリポジトリに保存せずAWS Secrets Managerなどで管理。顧客ごとに権限と保存先を分離。Search Console APIはすべての行を保証しない。

Cloudflare Web Analyticsは補助。Pages自動挿入を含む既存設定・プレビュー除外を確認してから有効化し、二重設置しない。

## 公式資料
- https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart
- https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- https://developers.google.com/analytics/devguides/collection/ga4/views

## 2026-10-12 未完了事項
サイトマップはGoogleライブテストで正常XMLの取得を確認し再送信。Search Consoleの処理結果待ち。外部取得コードはtooling/analytics/を参照。API認証未登録・AWS未配置につき、実API取得と定期運用は未稼働。Google Cloud ConsoleはこのブラウザではSite Unavailableのため設定できない。Cloudflare内部デプロイエラーはユーザーの再実行で解消。
