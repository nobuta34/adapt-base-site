# adapt-base 公的情報ポータル 基本設計書

**文書番号** AB-PIP-DESIGN-001  
**版** v0.1（基本設計ベース／未承認）  
**作成日** 2026年11月23日  
**関連文書** `adapt-base_公的情報ポータル_プロジェクト計画書_v0.1_20261123.md`  
**対象範囲** 国・地方自治体・公的機関の公表情報の収集、正規化、検索、一次情報への誘導

> 本設計は構成候補とインターフェースの叩き台であり、既存RSSのWorker/D1/Cronが稼働済みであるという意味ではない。実環境棚卸しとPoCで確定する。

## 1. 設計前提と非機能原則

### 1.1 確認済みと未確認の境界

- **確認済み**：GitHub `nobuta34/adapt-base-site` はHugo構成で、`hugo.toml`、`content/`、`layouts/`、`docs/`を持つ。`hugo.toml`のbaseURLは `https://adapt-base.com/`、テーマはPaperMod。
- **別途調査**：Cloudflareアカウントの最新のPages・Worker・Cron・D1・R2配置、既存RSS収集コード、Secrets、実トラフィック、メトリクス、カスタムドメイン設定。
- **原則**：公開Hugoサイトは既存機能を保持し、収集機能を別レイヤーとして追加する。現行のGitHub mainに無断デプロイしない。

### 1.2 目標アーキテクチャ

```text
[国・省庁API]  [RSS/Atom]  [自治体HTML]  [許可済メルマガ]
      |            |             |             |
      +------------+-------------+-------------+
                           |
                 [Source Registry / 利用条件]
                           |
                 [収集アダプター・スケジューラ]
                           |
            [入力検証・正規化・重複排除]
                           |
                      [Cloudflare D1]
                  /          |          \
            [公開API]   [監視・管理]   [エクスポート]
                |
       [Hugo / Cloudflare Pages]
                |
          [閲覧者・検索利用]
```

推奨：公開サイト＝Hugo/Pages、取得・公開API＝Workers、定期実行＝Cron、主データ＝D1。HTML/PDF処理が重い場合は外部の低頻度ジョブに切り出す。

## 2. 機能分割とデータ流通

| 構成要素 | 責任 | 入力 | 出力 |
|---|---|---|---|
| Source Registry | 情報源・許諾・設定の正本 | 運用者の承認した設定 | 有効な収集対象 |
| Scheduler | 対象ごとの取得周期を判定 | Cron、最終実行日時 | fetch対象ID |
| API Adapter | 公開APIの条件付き取得 | URL、クエリ、認証設定 | JSONレコード |
| Feed Adapter | RSS/Atomパース | XML、ETag | 記事レコード |
| HTML Adapter | 合意済ページの差分取得 | HTML、セレクタ | 抽出レコード |
| Normalizer | 共通スキーマ化・分類 | 生レコード | 正規化候補 |
| Deduplicator | 安定した識別と更新処理 | 発信元ID、URL、ハッシュ | itemとversion |
| Publication Gate | 規約・品質・レビュー状態の判定 | source/item状態 | 公開/保留 |
| Public API | 公開可能レコードの検索 | 地域、分類、日付、ページング | JSONレスポンス |
| Site UI | 検索・一覧・詳細・出典表示 | API結果 | 公開画面 |
| Monitor | 異常検知・レポート | 実行ログ、更新統計 | 運用通知・判断材料 |

### 2.1 標準収集フロー

1. `sources.enabled = 1` かつ `collection_policy = allowed` の候補を収集周期順に選択。
2. 取得URLは運用で承認したHTTPSホストだけを許可。DNS再解決・リダイレクト先も検証し、SSRFを防止。
3. ETag／Last-Modifiedを保持し、`If-None-Match`／`If-Modified-Since`を付与。304は正常・更新なしとして記録。
4. 429／5xxはリトライ可能に分類し、上限付き指数バックオフ＋ジッターを適用。1件の障害は他件に波及させない。
5. レスポンスサイズ、コンテンツタイプ、XML外部実体・危険なHTMLを検証。HTMLをそのまま公開しない。
6. 文字コード・日時（内部UTC・表示JST）・地域・カテゴリを共通形式へ変換。
7. 安定ID/公式URLを優先しUPSERT。内容変更時のみversionを追加し、再実行で増殖しない。
8. 利用条件・記事検証・公開状態を評価。未確認のものは公開対象にしない。
9. `fetch_runs`に件数、HTTP、duration、エラー分類を記録。利用量と異常値を集計。

### 2.2 再実行・バッチ設計

MVPでは1起動あたり少数の情報源・最大件数に制限し、次のCronで続きを処理する。`lease_until`で同時収集を防止し、lease期限切れは再取得可能とする。1レコードの失敗はDead Letter相当のエラー記録に残し、全件ロールバックしない。Worker FreeのCPU時間が厳しい場合は有料化または外部バッチ移動の判断を行う。

## 3. 情報源レジストリ設計

### 3.1 推奨プロパティ

| 項目 | 型の例 | 内容 |
|---|---|---|
| `source_id` | TEXT PK | 永続ID（機関名の変更に依存しない） |
| `organization_name` | TEXT | 発行・運営主体 |
| `source_level` | TEXT | national/prefecture/municipal/agency/other |
| `region_scope` | TEXT | 全国/都県/市区町村コード等 |
| `source_type` | TEXT | api/rss/atom/html/email |
| `source_url` | TEXT | 公式の入口URL（個人情報なし） |
| `poll_minutes` | INTEGER | 最小収集間隔 |
| `collection_policy` | TEXT | allowed/restricted/pending/denied |
| `publication_policy` | TEXT | link_only/metadata/snippet/summary/denied/pending |
| `notification_policy` | TEXT | allowed/denied/pending |
| `terms_url` | TEXT | 利用条件の確認先 |
| `terms_checked_at` | TEXT | 確認日時 |
| `terms_evidence` | TEXT | 判断根拠・申請番号（秘匿情報は置かない） |
| `etag` / `last_modified` | TEXT | 条件付き取得用 |
| `last_attempt_at` / `last_success_at` | TEXT | 実行状況 |
| `enabled` | INTEGER | 収集有効フラグ |
| `public_enabled` | INTEGER | 公開可否の最終フラグ。既定0 |

**重要**：`collection_policy`と`publication_policy`は別々に判定する。利用規約に基づきリンクのみ公開できるケースと、派生サイト自体が禁止されるケースを混同しない。禁止/不明な情報源は自動公開不可とする。

## 4. データモデル（論理設計）

| テーブル | 主キー | 主な項目・関連 |
|---|---|---|
| `sources` | source_id | 情報源メタデータ、許諾、周期、状態 |
| `fetch_runs` | run_id | source_id、開始/終了、status、HTTP、件数、エラー分類 |
| `items` | item_id | source_id、external_id、canonical_url、title、publisher、published/updated/seen_at、expires_at、status、hash |
| `item_versions` | version_id | item_id、content_hash、検出日時、変更フィールド、承認状態 |
| `item_categories` | (item_id, category_code) | 多対多カテゴリ |
| `item_regions` | (item_id, region_code) | 多対多対象地域 |
| `source_checks` | check_id | 規約確認者、確認日、確認条件、参考URL、判断結果 |
| `publication_reviews` | review_id | item_id、処理理由、承認者、公開状態・変更日時 |
| `schema_migrations` | version | DBマイグレーション版 |

### 4.1 主な設計制約

- `UNIQUE(source_id, external_id)`：external_idがある場合の同一性判定。
- `UNIQUE(source_id, canonical_url)`：規格化URLが確実な場合の代替キー。両者が欠ける場合はソース内限定の安定ハッシュ。
- 同一補助金でも回次や年度が異なる場合は別募集として保持し、機械的に上書きしない。
- `first_seen_at`と`last_seen_at`は分離し、掲載の最終確認日時と更新日時を取り違えない。
- `published_at`・`updated_at`は元情報の日時がある場合のみ設定し、無い場合はNULLとする。
- `deadline_at`はJST等のタイムゾーンと精度を元資料から明示できる場合のみ確定。曖昧な「月末まで」は文字列と確度を別管理する。
- 記事タイトルや全文の保存・公開は規約に応じて制御し、保存可否の判定前に大量蓄積しない。
- ユーザーの個人情報はPhase 1では保持しない。

### 4.2 記事ステータス

`discovered`（検出）→ `normalized`（正規化）→ `review_pending`（公開条件確認）→ `published`（公開）を基本とする。異常時は `quarantined`（隔離）へ、取消・条件変更時は `withdrawn`（非公開）へ移行。自動復旧で `withdrawn` を公開へ戻さない。

## 5. 分類・地域・重複判定

### 5.1 カテゴリ体系（初期案）

`grant`（補助金・助成金）、`seminar`（研修・イベント）、`startup`（創業）、`management`（経営・資金繰り）、`digital`（DX・IT・AI）、`security`（セキュリティ）、`regulation`（制度・法改正）、`other`（その他）。カテゴリは複数付与可、未分類を許す。

### 5.2 地域体系

`ALL_JP`／JIS都道府県コード／JIS市区町村コードを使い、**実施主体の所在地**と**制度の対象地域**を分離する。対象地域不明を全国扱いしない。利用者向け表示は「全国・東京都・江戸川区」等の日本語に整形する。

### 5.3 重複判定優先順位

1. ソース側の安定記事IDまたはJグランツの補助金ID（募集回ごとの別識別に注意）。
2. 機関公式サイトの正規URL（追跡パラメータ除去は認めたキーに限定）。
3. ソース内の正規化タイトル＋発行日＋発行主体を用いた補助判定。
4. ソース横断の類似記事は「関連候補」として扱い、初期段階では自動マージしない。

## 6. 収集アダプターとデータ品質

### 6.1 API

Jグランツでは公開APIの一覧・詳細・詳細v2の存在を確認済み。受け取る項目はAPIのバージョン・仕様変更を含めて記録し、レート制限と必要パラメータをPoCで確認する。APIから取得した外部PDF等を無断で再配信しない。

### 6.2 RSS/Atom

RSS/Atomの更新日時・タイトル・URL・IDを最小単位として解析。フィードの著作権・利用規約がサイトでの再表示を許可するとは限らない。`publication_policy`が適切でない場合、公式URLの登録や公開を保留する。

### 6.3 HTML監視・メール

HTML監視はPhase 2以降に限定し、robots、利用規約、アクセス負荷、HTML変更への耐性を確認する。メール収集は専用アドレス、同意・契約・転載条件を検証してから利用し、届いたメール本文や宛先情報を公開データベースへ保存しない。

### 6.4 品質フラグ

`source_verified`、`publication_rights_verified`、`date_verified`、`deadline_verified`、`region_verified`、`manual_review_required`を記録。UIは「募集終了の可能性あり」などの根拠がない推定表示を避け、確定日時がない場合は「公式サイトで確認」とする。

## 7. 公開APIインターフェース（案）

APIを既存ドメインのパスに載せるか、別サブドメインとするかはCloudflare route/DNSの実態調査後に決定する。以下は論理APIであり実装済みではない。

| メソッド・パス | 目的 | 公開範囲 |
|---|---|---|
| `GET /api/v1/public-info/items` | 一覧検索 | 公開許諾を満たすレコードのみ |
| `GET /api/v1/public-info/items/{id}` | 記事詳細 | 公開許諾を満たすレコードのみ |
| `GET /api/v1/public-info/categories` | 分類マスタ | 公開 |
| `GET /api/v1/public-info/regions` | 地域マスタ | 公開 |
| `GET /api/v1/public-info/status` | 最終更新概要 | 個別情報源の内部エラー詳細は含めない |

### 7.1 主要クエリ

`q`（検索語）、`region`（地域コード）、`category`（分類）、`status`（募集中等）、`from`（公開日以降）、`sort`（newest/deadline）、`cursor`、`limit`（上限固定）。曖昧な検索語は長さ・文字種を検証し、D1にはバインド変数で問い合わせる。

### 7.2 レスポンス例（設計例・実データではない）

```json
{
  "items": [
    {
      "id": "sample-001",
      "title": "（表示許可済みの情報タイトル）",
      "publisher": "発信元の公的機関",
      "category_codes": ["grant", "digital"],
      "region_codes": ["13"],
      "published_at": null,
      "updated_at": null,
      "last_verified_at": "2026-11-23T00:00:00Z",
      "deadline_at": null,
      "original_url": "https://example.org/official-notice",
      "rights_mode": "metadata"
    }
  ],
  "next_cursor": null
}
```

上記URLと内容はダミー。キャッシュは短時間（仮15分）から開始し、訂正・非公開は早期に反映できるよう失効手段を設ける。CORSは本番の公開サイトのみを基本許可し、認証のない管理APIを作らない。

## 8. 公開画面・UX

### 8.1 ページ候補

| 仮パス | 役割 |
|---|---|
| `/public-info/` | 導入文、カテゴリ別入口、最新記事、公式確認の注意 |
| `/public-info/search/` | 検索、地域・分類・期間・募集中フィルター |
| `/public-info/item/{id}/` | 発信元、出典、日付、地域、公式ページ誘導 |
| `/public-info/about/` | 収集対象、公開基準、免責、訂正依頼窓口 |

Hugoの静的ページとJavaScriptによるAPI呼出しを基本とする。検索条件はURLパラメータで再現可能とし、ブラウザ更新・戻る操作で状態を保持。JavaScript無効時の説明、取得失敗時の代替リンク、一覧ゼロ件時の適切な表示を用意する。

### 8.2 記事表示の注意

公開日・更新日・取得日・確認日を明確に区別し、元情報が存在する場合はその公式リンクを主導線にする。締切の出典がない情報は締切順の対象外。タグの意味（募集中・終了・不明）を説明し、AI生成要約には「自動要約」を表示する（AI導入後）。

### 8.3 アクセシビリティとSEO

スマートフォンの1列レイアウト、見出し構造、キーボード操作、フォーカス表示、適切なコントラスト、リンク先の意味あるラベルを必須とする。公開データだけを検索インデックス対象にし、管理画面・プレビュー・未許諾の記事はindex対象外。重複ページのcanonicalとサイトマップはHugo側の既存機構と整合させる。

## 9. 公開制御・法務・セキュリティ

### 9.1 権利判定ゲート

公開対象となるには、情報源が明示的に有効、取得許可あり、表示形態が利用条件に合致、内部品質チェック合格、公開停止フラグOFFのすべてが必要。根拠情報を残し、利用条件が変更された場合は該当情報源の公開を即時停止できるようにする。管理者の手動公開操作にもゲートを適用する。

**東京都RSSの注意**：RSSを使用した新着情報の再配布、メルマガ作成、サイト構築には事前申請を求める案内がある。許諾のないRSS一覧の再掲を前提とせず、必ず対象ページの最新利用規約を確認する。

### 9.2 防御策

- 外部ソースは非信頼データとし、XML外部実体無効、HTMLタグ無害化、レスポンスサイズ制限、タイムアウト、URL許可リスト、SSRF防止を実施。
- DB書込・検索にプレースホルダを使いSQLインジェクションを回避。HTML表示はテキストエスケープし、CSPを段階導入。
- 認証情報はCloudflare Secrets／Bitwarden等で管理し、GitHub・Drive・ログに値を残さない。
- 管理機能はCloudflare Access等でアクセス制御。公開APIは読み取り専用にする。
- 外部障害や規約変更時は該当sourceのみ無効化できるキルスイッチを用意。
- 収集ログはURL・HTTP結果等の最小情報にとどめ、個人情報やメール本文を残さない。

### 9.3 個人情報とメール配信

Phase 1では会員情報を収集しない。通知機能を追加する際は同意、配信停止、保存期間、漏えい時対応、差出人認証、メールアドレスの保管・削除を別設計とする。

## 10. ログ・監視・障害復旧

| 監視項目 | 記録対象 | 主な異常条件（仮） |
|---|---|---|
| Source状態 | 最終成功、最終試行、HTTPコード | 想定周期×3以上成功がない |
| 取得件数 | 取得・正規化・新規・更新・破棄 | 平常比大幅減少・急増 |
| データ品質 | 重複率、日付解析失敗、未分類 | 突然の品質低下 |
| 公開制御 | 公開候補・保留・却下数 | 未許諾公開はゼロ必須 |
| 性能 | CPU、実行時間、APIレイテンシ、D1使用量 | 無料枠への接近 |
| 安全性 | 許可外URL、解析例外、429/403急増 | 高頻度・権利問題・仕様変更を疑う |

「新規0件」は正常にも異常にもなり得るため、HTTP成功・304・件数の推移と合わせて判定する。失敗時は該当情報源を停止して原因を確認し、直近の正常データを保持。無許諾と分かった記事はキャッシュを含めて非公開化する。

### 10.1 保全と復旧

本番前にD1バックアップ/エクスポート手段、マイグレーションの前進・後退手順、デプロイロールバック、ソース設定のGit履歴を検証する。バックアップに収集元の転載禁止データを無制限に残さない。保持期間・削除タイミングは別途決定。

## 11. テスト方針

| ID | テスト観点 | 基本期待結果 |
|---|---|---|
| T-01 | 同一フィードの2回取込 | 同一記事が重複しない |
| T-02 | 304 Not Modified | 成功・更新なしとなり異常扱いしない |
| T-03 | 429/500/タイムアウト | 再試行・隔離、他ソースは継続 |
| T-04 | XML不正・巨大レスポンス | 安全に拒否・エラー記録 |
| T-05 | HTML/文字列の危険な入力 | XSS/SSRF/SQLiにつながらない |
| T-06 | 無許諾・確認待ちsource | 公開API/検索に出ない |
| T-07 | 許諾取り消し | 記事が非公開化、キャッシュも失効 |
| T-08 | 地域と日付の境界 | 全国/都県/市区町村、JST日付が正しく扱われる |
| T-09 | 年度・募集回次違い | 別の応募募集として残る |
| T-10 | D1障害・再起動 | 重複せず再開、復旧手順が機能 |
| T-11 | スマホ・アクセシビリティ | 検索、リンク、エラー表示が利用可能 |
| T-12 | Free枠負荷 | 収集対象拡大時のCPU/リクエスト負荷を観測 |

## 12. 構成管理・リリース

### 12.1 推奨ディレクトリ案（既存構成を維持）

```text
adapt-base-site/
  docs/public-info/                  # 文書正本の追加先（既存 docs/ を維持）
  content/public-info/               # Hugoページ（後続の実装フェーズ）
  layouts/public-info/               # 既存テーマを直接変更しない
  assets/                             # 必要時に専用CSS/JS

# 収集Workerの配置は既存RSS基盤の棚卸し後に決定
# 既存 repo に含めるか ab-automation 等へ分割するか未確定
```

### 12.2 変更手順

1. GitHubで作業ブランチ、PR作成。設計差分・影響範囲・試験記録を添付。
2. 運用Secretsを含まない設定例とSQLマイグレーションをレビュー。
3. ステージング/プレビュー環境でデータ品質・許諾ゲート・負荷・ロールバック確認。
4. サービスオーナーが公開承認した後、`main`反映・本番反映。
5. 成果物の配布用Word版を `Google Drive/adapt-base/10_Documents` へ格納。正本と配布版のバージョンを一致させる。

## 13. 実装着手前の確認事項

| ID | 確認事項 | 未確認時の扱い |
|---|---|---|
| C-01 | 既存RSS Worker/Cron/D1の接続・命名・配置 | 新規作成や流用を確定しない |
| C-02 | 既存RSSのコード・台帳・ログ・エラー処理 | 共通化の重複開発を避ける |
| C-03 | 本番ドメイン・API route・CORS・DNS | APIの実URLを決めない |
| C-04 | 情報源別の利用条件・申請要否 | 公開可否は既定OFF |
| C-05 | JグランツAPIの利用条件・件数制限・戻り値 | PoCで低頻度に確認 |
| C-06 | D1プラン・容量・読み書き・バックアップ | 規模見積りを確定しない |
| C-07 | UIとHugoテーマの表示統合 | プレビューで確認 |
| C-08 | メール通知・AI APIの費用と取り扱い | MVPから除外 |

## 14. 設計レビュー判定基準

以下のすべてがYesになるまで本番公開を行わない：公開する元情報の利用条件が検証済み、一次情報URLを提示、日時・期限の意味が正しく区別されている、未許諾データがAPIに出ない、収集失敗を発見可能、秘密情報をPublic repoに保存していない、データの削除/非公開/復旧ができる、PoCの実測コストが許容範囲、既存サイトへの機能退行がない。

## 15. 参照資料（2026-11-23時点）

- JグランツAPI（一覧・詳細・詳細v2）： https://developers.digital.go.jp/documents/jgrants/api/
- Cloudflare Workers制限： https://developers.cloudflare.com/workers/platform/limits/
- Cloudflare D1制限： https://developers.cloudflare.com/d1/platform/limits/
- 東京都RSS利用案内： https://www.metro.tokyo.lg.jp/policy/rss
- 既存サイトGitHub： https://github.com/nobuta34/adapt-base-site
- 既存のHugoサイト設計： `docs/adapt-base_Website_Design_v0.1.md`

---

**改版履歴**：v0.1／2026-11-23／構成案、論理データモデル、API、権利・公開ゲート、運用監視、テスト方針を初版作成。実装内容ではない。