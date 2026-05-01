# Samples

このディレクトリには、手動確認や回帰テストで利用するサンプルファイルを配置します。

## 推奨サンプル

- OCR 用の請求書画像
- OCR 用の領収書画像
- OCR 用の見積書画像
- OCR 用の非定型メモ / 指示書画像
- 可視化用 CSV
- 可視化用 Excel
- メール解析用 EML / TXT
- Web 抽出結果の保存先確認用テキスト

## 命名例

- `invoice_sample.jpg`
- `receipt_sample.jpg`
- `quote_sample.jpg`
- `memo_sample.jpg`
- `sales_sample.csv`
- `dashboard_sample.xlsx`

## 注意メモ

- 個人情報や機密業務情報を含むファイルは配置しない
- README やテストで使う場合は、匿名化済みのデータのみを使う
- 画像や CSV を増やした場合は、どの機能向けなのか分かる名前を付ける
- 実帳票サンプルを追加したら、OCR の手動回帰確認にも利用する
