# AWS Transit Gateway Terraform Importer

既存のAWS Transit Gatewayリソースを検出し、Terraformコードとインポートコマンドを自動生成します。さらに、ベストプラクティスに則ったモジュール構造への変換も自動化します。

## 対応リソース

- Transit Gateway
- Transit Gateway Route Table
- Transit Gateway VPC Attachment
- Transit Gateway Route (静的ルート)
- Route Table Association/Propagation
- VPC Route (TGW宛て)

## 必要な環境

- AWS CLI v2
- Python 3.8+
- jq
- Terraform 1.5+

## クイックスタート

```bash
# AWS認証設定
aws configure

# 全自動実行
./scripts/run_all.sh --region ap-northeast-1
```

**注意**: `output/`、`terraform/`、`terraform-modules/`内のファイルは実行時に自動生成・上書きされます。手動削除は不要です。

実行内容:
1. AWSリソース取得
2. フラットなTerraformコード生成
3. Terraform初期化
4. インポートスクリプト生成・実行
5. **モジュール構造への変換**
6. モジュールの検証

## 手動実行

```bash
# 1. リソース取得
AWS_REGION=ap-northeast-1 ./scripts/fetch_aws_resources.sh

# 2. フラットなTerraformコード生成
python3 scripts/generate_terraform.py --region ap-northeast-1

# 3. 初期化とインポート
cd terraform && terraform init && cd ..
python3 scripts/generate_import_commands.py
./scripts/import.sh

# 4. モジュール構造生成
python3 scripts/generate_modules.py

# 5. モジュール検証
cd terraform-modules && terraform init && terraform validate && terraform plan
```

## オプション

```bash
# インポートをスキップ
./scripts/run_all.sh --skip-import

# モジュール化をスキップ
./scripts/run_all.sh --skip-modules

# 両方スキップ（コード生成のみ）
./scripts/run_all.sh --skip-import --skip-modules

# リージョン指定
./scripts/run_all.sh --region us-east-1

# ヘルプ
./scripts/run_all.sh --help
```

## 必要なIAM権限

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeTransitGateways",
      "ec2:DescribeTransitGatewayRouteTables",
      "ec2:DescribeTransitGatewayAttachments",
      "ec2:GetTransitGatewayRouteTableAssociations",
      "ec2:GetTransitGatewayRouteTablePropagations",
      "ec2:SearchTransitGatewayRoutes",
      "ec2:DescribeRouteTables"
    ],
    "Resource": "*"
  }]
}
```

## 生成ファイル

実行時に以下のファイルが自動生成されます（既存ファイルは上書き）:

```
output/                              # AWSリソースJSON
terraform/*.tf                       # フラットなTerraformコード
scripts/import.sh                    # インポートコマンド
terraform-modules/                   # モジュール構造
├── main.tf                          # ルートモジュール
├── variables.tf                     # ルート変数
├── outputs.tf                       # ルート出力
├── versions.tf                      # プロバイダー設定
└── modules/transit-gateway/         # TGWモジュール
    ├── main.tf                      # リソース定義
    ├── variables.tf                 # モジュール変数
    ├── outputs.tf                   # モジュール出力
    └── README.md                    # モジュール説明
```

## トラブルシューティング

**AWS認証エラー**:
```bash
aws sts get-caller-identity
```

**依存パッケージのインストール**:
```bash
# Ubuntu/Debian
sudo apt-get install jq awscli terraform

# macOS
brew install jq awscli terraform
```
