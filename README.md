# AWS Transit Gateway Terraform Module

AWS Transit Gatewayを管理するためのTerraformモジュールです。既存のTransit Gatewayリソースをインポートし、for_eachを使った動的な構成で管理します。

## 特徴

- **動的リソース管理**: for_eachを使用し、terraform.tfvarsの変更のみでリソースを追加・削除可能
- **モジュール化**: 再利用可能なモジュール構造
- **インポート対応**: 既存のAWSリソースを簡単にインポート
- **変更に強い**: 環境固有の値はterraform.tfvarsで管理

## ディレクトリ構造

```
.
├── README.md
└── terraform/
    ├── main.tf                      # ルートモジュール
    ├── variables.tf                 # 変数定義
    ├── terraform.tfvars             # 環境固有の値（Git管理対象外推奨）
    ├── terraform.tfvars.example     # 設定例
    ├── versions.tf                  # Terraform/プロバイダーバージョン
    ├── outputs.tf                   # 出力値
    ├── import.sh                    # インポートスクリプト
    └── modules/
        └── transit-gateway/
            ├── main.tf              # モジュールのメインロジック
            ├── variables.tf         # モジュール変数
            └── outputs.tf           # モジュール出力
```

## 使い方

### 1. 初期セットアップ

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

### 2. terraform.tfvarsを編集

実際の環境に合わせて値を設定します。

```hcl
region      = "ap-northeast-1"
transit_gateway_name = "tgw"

vpc_attachments = {
  vpc1 = {
    name       = "tgw-attachment-vpc1"
    vpc_id     = "vpc-xxxxx"  # 実際のVPC IDに変更
    subnet_ids = ["subnet-xxxxx"]
  }
}

tgw_routes = {
  dev_10_1_0_0_16 = {
    destination_cidr_block = "10.1.0.0/16"
    route_table_key        = "development"
    attachment_key         = "vpc1"
  }
}
```

### 3. 既存リソースのインポート（初回のみ）

既存のTransit Gatewayリソースをインポートする場合:

```bash
# import.shを編集してリソースIDを設定
vim import.sh

# 実行
chmod +x import.sh
./import.sh
```

### 4. Terraform実行

```bash
# 初期化
terraform init

# 計画確認
terraform plan

# 適用
terraform apply
```

## リソースの追加・変更方法

### Transit Gatewayルートを追加する

`terraform.tfvars`の`tgw_routes`セクションに新しいエントリを追加:

```hcl
tgw_routes = {
  # 既存のルート...

  # 新しいルートを追加
  dev_10_3_0_0_16 = {
    destination_cidr_block = "10.3.0.0/16"
    route_table_key        = "development"
    attachment_key         = "vpc2"
  }
}
```

実行:
```bash
terraform plan   # 変更内容を確認
terraform apply  # 適用
```

### VPCアタッチメントを追加する

`terraform.tfvars`の`vpc_attachments`セクションに追加:

```hcl
vpc_attachments = {
  # 既存のVPC...

  vpc3 = {
    name       = "tgw-attachment-vpc3"
    vpc_id     = "vpc-zzzzz"
    subnet_ids = ["subnet-zzzzz"]
  }
}
```

### ブラックホールルートを追加する

`blackhole = true`を設定:

```hcl
tgw_routes = {
  dev_192_168_0_0_16_blackhole = {
    destination_cidr_block = "192.168.0.0/16"
    route_table_key        = "development"
    blackhole              = true  # attachment_keyは不要
  }
}
```

### ルートテーブルを追加する

`terraform.tfvars`の`route_tables`セクションに追加:

```hcl
route_tables = {
  # 既存のルートテーブル...

  staging = {
    name = "tgw-rt-staging"
    tags = {}
  }
}
```

## インポート手順（詳細）

### 1. AWSリソースIDの確認

```bash
# Transit Gateway IDを取得
aws ec2 describe-transit-gateways --region ap-northeast-1

# ルートテーブルIDを取得
aws ec2 describe-transit-gateway-route-tables --region ap-northeast-1

# VPCアタッチメントIDを取得
aws ec2 describe-transit-gateway-attachments --region ap-northeast-1
```

### 2. import.shの編集

取得したリソースIDを使ってimport.shを編集:

```bash
terraform import 'module.transit_gateway.aws_ec2_transit_gateway.this' tgw-xxxxx
terraform import 'module.transit_gateway.aws_ec2_transit_gateway_route_table.this["development"]' tgw-rtb-xxxxx
```

### 3. インポート実行

```bash
chmod +x import.sh
./import.sh
```

### 4. 確認

```bash
terraform plan  # "No changes"と表示されればOK
```

## 変更が必要なファイル

| 変更内容 | 編集するファイル | 変更箇所 |
|---------|----------------|---------|
| ルート追加/削除 | `terraform.tfvars` | `tgw_routes`セクション |
| VPCアタッチメント追加 | `terraform.tfvars` | `vpc_attachments`セクション |
| ルートテーブル追加 | `terraform.tfvars` | `route_tables`セクション |
| VPCルート追加 | `terraform.tfvars` | `vpc_routes`セクション |
| Association/Propagation追加 | `terraform.tfvars` | `route_table_associations`/`route_table_propagations`セクション |
| リージョン変更 | `terraform.tfvars` | `region` |
| タグ変更 | `terraform.tfvars` | `tags`セクション |

**モジュールのコード（`modules/transit-gateway/`）は変更不要です！**

## トラブルシューティング

### "Resource already managed by Terraform"エラー

リソースが既にstateに存在します。削除してから再インポート:

```bash
terraform state rm 'module.transit_gateway.aws_ec2_transit_gateway.this'
terraform import 'module.transit_gateway.aws_ec2_transit_gateway.this' tgw-xxxxx
```

### planで意図しない変更が表示される

terraform.tfvarsの値がAWSの実際の値と一致しているか確認:

```bash
# 実際のリソース情報を確認
terraform state show 'module.transit_gateway.aws_ec2_transit_gateway.this'
```

### インポート後にplanでタグの変更が表示される

正常な動作です。tagsの追加のみの場合は問題ありません:

```
Plan: 0 to add, 6 to change, 0 to destroy.
```

## 要件

- Terraform >= 1.5
- AWS Provider >= 5.0
- AWS認証情報の設定

## ライセンス

このプロジェクトはサンプルコードです。自由に使用・改変してください。
