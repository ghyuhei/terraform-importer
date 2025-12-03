# AWS Transit Gateway Terraform Module

AWS Transit Gatewayを管理するためのTerraformモジュールです。既存のTransit Gatewayリソースをインポートし、for_eachを使った動的な構成で管理します。

## 特徴

- **自動インポート**: スクリプトで既存リソースを自動検出し、terraform.tfvarsとimport.shを生成
- **動的リソース管理**: for_eachを使用し、terraform.tfvarsの変更のみでリソースを追加・削除可能
- **モジュール化**: 再利用可能なモジュール構造
- **変更に強い**: 環境固有の値はterraform.tfvarsで管理

## ディレクトリ構造

```
.
├── README.md
├── scripts/
│   ├── fetch_aws_resources.sh           # AWSリソース情報取得スクリプト
│   ├── generate_terraform_config.py     # terraform.tfvars自動生成
│   └── generate_import_commands.py      # import.sh自動生成
├── output/                              # AWS情報のJSON出力先（自動生成）
└── terraform/
    ├── main.tf                          # ルートモジュール
    ├── variables.tf                     # 変数定義
    ├── terraform.tfvars                 # 環境固有の値（Git管理対象外）
    ├── terraform.tfvars.example         # 設定例
    ├── versions.tf                      # Terraform/プロバイダーバージョン
    ├── outputs.tf                       # 出力値
    ├── import.sh                        # インポートスクリプト（自動生成）
    └── modules/
        └── transit-gateway/
            ├── main.tf                  # モジュールのメインロジック
            ├── variables.tf             # モジュール変数
            └── outputs.tf               # モジュール出力
```

## 使い方

2つのユースケースがあります：

### ケースA: 既存リソースをインポートする（推奨）

既存のAWS Transit Gatewayリソースを管理下に置く場合の手順です。

#### 1. AWSリソース情報を取得

```bash
# スクリプトを使って既存リソース情報を自動取得
cd terraform
../scripts/fetch_aws_resources.sh

# outputディレクトリにJSON形式で保存されます
```

#### 2. terraform.tfvarsとimport.shを自動生成

```bash
# terraform.tfvarsを生成（既存リソースから自動生成）
python3 ../scripts/generate_terraform_config.py

# import.shを生成（インポートコマンドを自動生成）
python3 ../scripts/generate_import_commands.py
```

生成されたファイルを確認・調整してください。

#### 3. Terraformを初期化してインポート実行

```bash
# 初期化
terraform init

# インポート実行
chmod +x import.sh
./import.sh

# 差分確認（差分がないことを確認）
terraform plan
```

#### 4. 差分がある場合は調整

terraform planで差分が表示された場合、terraform.tfvarsを微調整します：

```bash
# 実際のリソース情報を確認
terraform state show 'module.transit_gateway.aws_ec2_transit_gateway.this'

# terraform.tfvarsを編集して合わせる
vim terraform.tfvars

# 再度確認
terraform plan  # "No changes"が理想
```

### ケースB: 新規作成する

新しくTransit Gatewayを構築する場合の手順です。

#### 1. 設定ファイルを準備

```bash
cd terraform

# サンプルファイルをコピー
cp terraform.tfvars.example terraform.tfvars

# エディタで編集
vim terraform.tfvars
```

#### 2. terraform.tfvarsを実際の環境に合わせて編集

以下のように、実際のVPC IDやサブネットIDに変更します：

```hcl
region      = "ap-northeast-1"
transit_gateway_name = "tgw"

vpc_attachments = {
  vpc1 = {
    name       = "tgw-attachment-vpc1"
    vpc_id     = "vpc-0123456789abcdef0"  # 実際のVPC ID
    subnet_ids = ["subnet-0123456789abcdef0"]  # 実際のサブネットID
  }
}

route_tables = {
  development = {
    name = "tgw-rt-development"
    tags = {}
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

#### 3. Terraform実行

```bash
# 初期化
terraform init

# 計画確認（新規作成されるリソースを確認）
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

## 自動生成スクリプトの詳細

### fetch_aws_resources.sh

既存のAWSリソース情報をJSON形式で取得します。

```bash
# デフォルト（output/ディレクトリに出力）
./scripts/fetch_aws_resources.sh

# 出力先とリージョンをカスタマイズ
OUTPUT_DIR=./my-output AWS_REGION=us-west-2 ./scripts/fetch_aws_resources.sh
```

取得される情報：
- Transit Gateway
- Transit Gateway Route Tables
- VPC Attachments
- Route Table Associations/Propagations
- Transit Gateway Routes
- VPC Route Tables

### generate_terraform_config.py

outputディレクトリのJSON情報から、terraform.tfvarsを自動生成します。

```bash
# デフォルト（terraform/terraform.tfvarsに出力）
python3 scripts/generate_terraform_config.py

# カスタマイズ
python3 scripts/generate_terraform_config.py \
  --input-dir ./output \
  --output ./terraform/terraform.tfvars
```

### generate_import_commands.py

outputディレクトリのJSON情報から、import.shを自動生成します。

```bash
# デフォルト（terraform/import.shに出力）
python3 scripts/generate_import_commands.py

# カスタマイズ
python3 scripts/generate_import_commands.py \
  --input-dir ./output \
  --output ./terraform/import.sh
```

生成されるインポートコマンドの例：

```bash
terraform import 'module.transit_gateway.aws_ec2_transit_gateway.this' tgw-xxxxx
terraform import 'module.transit_gateway.aws_ec2_transit_gateway_route_table.this["development"]' tgw-rtb-xxxxx
terraform import 'module.transit_gateway.aws_ec2_transit_gateway_vpc_attachment.this["vpc1"]' tgw-attach-xxxxx
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
