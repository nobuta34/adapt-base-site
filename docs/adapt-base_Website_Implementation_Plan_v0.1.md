# adapt-base Website Implementation Plan

> For agentic workers: Use superpowers:executing-plans to implement this plan task-by-task. Native execution in this session; no subagents.

**Goal:** 既存のHugoサイトから、２つの対象別入口を持つ事業サイトの初版を制作し、画面を見て修正を検討できる状態にする。

**Architecture:** Hugoを継続し、ルート側のテンプレートと共通CSSで事業サイトのデザインを構築する。既存URLは維持する。制作・確認用成果物を作り、本番mainは更新しない。

**Tech Stack:** Hugo 0.154.5、Markdown、HTML、CSS、最小限のJavaScript、Cloudflare Pages、GitHub。

**Spec:** adapt-base_Website_Design_v0.1.md（承認済み）。

## Global Constraints

- GitHub: nobuta34/adapt-base-site、既存本番mainは変更しない。
- ビルド: hugo --gc --minify、出力public、HUGO_VERSION=0.154.5。
- １サイトに事業者向けとIT部門・開発会社向けを同等に配置。
- 公開連絡先候補contact@、privacy@は新規作成・送受信確認待ち。
- 未確定価格、返信時間、実績、受注能力を確定情報として掲載しない。
- 素材の商用利用とPublicリポジトリ再配布条件を記録。初版は独自SVGを優先。

## Review Focus

1. 未作成メールアドレスが有効な受付窓口と誤認されないこと。
2. スマホで２つの入口が同等に認識でき、横にはみ出さないこと。
3. JavaScript無効やコピー失敗時でもアドレスが読めること。
4. 既存URLと新規ページのリンクが切れないこと。
5. 料金・実績・個人情報・素材条件の未確認項目が本番公開に混入しないこと。

## Task 1: 制作環境・基準の確保

Files: docs/superpowers/specs/2026-10-12-website-design.md、docs/superpowers/plans/2026-10-12-website-implementation.md、既存hugo.tomlとcontent/、themes/。

- [ ] GitHubの現行ツリーとAGENTS.mdの有無を確認し、ソースを取得する。
- [ ] 改善用ブランチfeature/business-site-v1を専用チェックアウトに用意する。仕様と本計画を同梱する。
- [ ] Hugo 0.154.5が利用できる経路を確認し、現行ビルドを実行する。
- [ ] 実行環境が利用できない場合は、成功したと扱わず、初版のHTML確認用出力と未検証のHugoソースを明確に区別する。

## Task 2: 共通デザイン・ホーム

Files: layouts/_default/baseof.html、layouts/index.html、layouts/partials/site-header.html、layouts/partials/site-footer.html、assets/css/site.css、hugo.toml。

Interfaces: 全ページはbaseofのmainブロックを使用。header/footerは同じナビと相談URLを共有。ホームはbusiness/technicalへの同等のカードを提供。

- [ ] 大見出し、独自の抽象SVG、２つの入口、支援分野、強み、工程、相談導線を実装する。
- [ ] 日本語ナビ、白・濃紺・青緑、本文16px以上、読みやすい行間、モバイル１列を適用する。
- [ ] 375px/768px/1440pxで横はみ出し、文字重なり、操作対象、入口の同等性を確認する。
- [ ] キーボード移動、可視フォーカス、見出し階層、文字コントラストを確認する。

## Task 3: 本文ページ・相談導線

Files: content/business/_index.md、content/technical/_index.md、content/about/_index.md、content/privacy/_index.md、content/services/_index.md、content/how-we-work/_index.md、content/pricing/_index.md、content/contact/_index.md、layouts/_default/list.html、layouts/_default/single.html、assets/js/site.js。

Interfaces: サービス本文は相談例・実施内容・成果物・前提条件・対象外・相談入口を持つ。問い合わせは表示テキストを必ず残し、コピー機能は補助に限定。

- [ ] 承認済み設計の文章を初稿として全ページへ展開する。
- [ ] 料金は個別見積方針を示し、未承認の現行金額と48時間返信保証を掲載しない。
- [ ] 未作成アドレスと個人情報方針は初版レビュー用であることを明示し、本番公開判定を保留する。
- [ ] ダミーフォームを置かず、アドレスコピー失敗時は手動コピーできる案内を出す。
- [ ] JavaScript無効でも本文とナビが利用可能であることを確認する。
- [ ] 未完成のCases/Insightsは主ナビから外し、既存URLは維持する。

## Task 4: 品質確認・レビュー用納品

Files: layouts/404.html、static/の採用素材、docs/assets/ASSET_LICENSES.md、docs/REVIEW_CHECKLIST.md、docs/DEPLOYMENT.md。

- [ ] 採用素材とライセンスを記録する。独自SVGはその旨を記録する。
- [ ] Hugoビルド、全内部リンク、画像、ページタイトル・description・canonical・OGPを確認する。
- [ ] プレビュー環境ではnoindexを適用し、未公開情報のアクセス制限とは区別する。
- [ ] Cloudflareプレビューブランチと環境変数の設定を確認し、利用できれば改善ブランチを送信してプレビュー生成結果を確認する。
- [ ] プレビューが利用できない場合は、ローカルで開ける確認用ページとソースZIPを提供し、環境の制約を明記する。
- [ ] 本番未反映、確認済み項目、未確認項目、公開前必須項目を納品時に示す。

## 公開前の別工程

メール送受信、個人情報の取扱い、掲載プロフィール、サービス範囲、料金条件を確定し、ユーザーが初版を見て修正指示を出す。明示的な本番反映の指示後にmainへの反映と本番確認を行う。本計画では本番公開を実施しない。

## 自己レビュー

承認済み設計の対象別導線、文章、サービス、素材、メール、保守、公開手順をタスクへ割り当て済み。フォーム・検索・決済は初版対象外。検証不能な事項を成功と扱わない。ユーザー向け操作コマンドはPowerShell形式とする。
