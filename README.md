# AWS Transit Gateway Terraform Importer

AWS Transit Gatewayの既存リソースをTerraform管理下に置くためのツールセットです。**ルートテーブルごとにディレクトリを分割**し、大規模環境でも管理しやすい構成を実現します。

## 特徴

- **複数TGW対応**: 複数のTransit Gatewayを同時に管理可能
- **ルートテーブル単位の分割管理**: 各ルートテーブルを独立したディレクトリで管理し、tfstate肥大化を防止
- **完全自動生成**: 既存AWSリソースからTerraform設定とインポートスクリプトを自動生成
- **全接続タイプ対応**: VPC, Peering, VPN, Direct Connect Gateway, Network Function すべてサポート
- **モジュールレス設計**: for_eachベースのシンプルな構造

## ディレクトリ構造

実際のディレクトリ名は AWS 環境の Transit Gateway 名とルートテーブル名（Nameタグ）から自動生成されます。

```
terraform/
├── tgw-{name}/                      # Transit Gateway ごとのディレクトリ (自動生成)
│   ├── main.tf                     # TGW, VPC/Peering Attachments 定義
│   ├── locals.tf                   # TGW 設定 (自動生成)
│   ├── outputs.tf                  # TGW ID と Attachment IDs を output
│   ├── versions.tf                 # Terraform と Provider バージョン
│   └── import.sh                   # インポートスクリプト (自動生成)
│
└── {tgw-name}-rt-{name}/           # ルートテーブルごとのディレクトリ (自動生成)
    ├── main.tf                     # Route Table, Routes, Associations 定義
    ├── locals.tf                   # 設定 (自動生成)
    ├── data.tf                     # tgw-{name}/ から TGW ID 参照
    ├── versions.tf                 # Terraform と Provider バージョン
    └── import.sh                   # インポートスクリプト (自動生成)
```

**設計思想:**
- 複数TGW対応: TGWごとに独立したディレクトリで管理
- State分離: TGWおよびルートテーブルごとに独立したterraform.tfstate
- 爆発半径の最小化: 1つのルートテーブルの問題が他に波及しない
- 並列作業: 複数のTGWやルートテーブルを同時に変更可能

## クイックスタート

### 1. AWSリソース情報を取得

```bash
# リソース情報を取得
./scripts/fetch_aws_resources.sh

# 別リージョンの場合
AWS_REGION=us-west-2 ./scripts/fetch_aws_resources.sh
```

出力: `aws_resources/{アカウントID}/{リージョン}/*.json`

### 2. Terraform設定を自動生成

```bash
python3 scripts/generate_terraform_config.py
```

生成されるファイル（名前は環境により異なる）:
```
terraform/
├── tgw-{name}/              # 例: tgw-multi_vpc_tgw/
│   ├── main.tf (固定)
│   ├── locals.tf (自動生成)
│   ├── outputs.tf (固定)
│   └── versions.tf (固定)
└── {tgw-name}-rt-{name}/    # 例: multi_vpc_tgw-rt-production/
    ├── main.tf (固定)
    ├── locals.tf (自動生成)
    ├── data.tf (固定)
    └── versions.tf (固定)
```

### 3. インポートスクリプトを生成

```bash
python3 scripts/generate_import_commands.py
```

生成されるファイル:
- `terraform/tgw-{name}/import.sh` - TGW と VPC/Peering Attachments のインポート
- `terraform/{tgw-name}-rt-{name}/import.sh` - Route Table, Associations, Routes のインポート

### 4. インポート実行

```bash
# TGWをインポート（各TGWディレクトリで実行）
cd terraform/tgw-multi_vpc_tgw  # 環境により名前が異なる
terraform init
./import.sh
terraform apply

# Route Tableをインポート（各ディレクトリで実行）
cd ../multi_vpc_tgw-rt-production  # 環境により名前が異なる
terraform init
./import.sh
terraform apply
```

## リソース追加方法

### 新しいVPC Attachmentを追加

1. **tgw-{name}/locals.tf に追加**:
```hcl
vpc_attachments = {
  # 既存...
  tgw_attachment_vpc3 = {
    name       = "tgw-attachment-vpc3"
    vpc_id     = "vpc-xxxxx"
    subnet_ids = ["subnet-aaaa", "subnet-bbbb"]
  }
}
```

2. **適用**:
```bash
cd terraform/tgw-multi_vpc_tgw
terraform plan
terraform apply
```

### 新しいルートを追加

1. **{tgw-name}-rt-{name}/locals.tf に追加**:
```hcl
tgw_routes = {
  # 既存...
  route_10_100_0_0_16 = {
    destination_cidr_block = "10.100.0.0/16"
    attachment_key         = "tgw_attachment_vpc2"
    attachment_type        = "vpc"
  }
}
```

2. **適用**:
```bash
cd terraform/multi_vpc_tgw-rt-production
terraform plan
terraform apply
```

## locals.tf の構造

### tgw-{name}/locals.tf (自動生成)

```hcl
locals {
  region      = "ap-northeast-1"
  account_id  = "123456789012"
  environment = "production"

  transit_gateway = {
    name                            = "tgw-main"
    description                     = "Main Transit Gateway"
    amazon_side_asn                 = 64512
    default_route_table_association = "disable"
    default_route_table_propagation = "disable"
    dns_support                     = "enable"
    vpn_ecmp_support                = "enable"
  }

  vpc_attachments = {
    tgw_attachment_vpc1 = {
      name       = "tgw-attachment-vpc1"
      vpc_id     = "vpc-xxxxx"
      subnet_ids = ["subnet-aaaa", "subnet-bbbb"]
    }
  }

  peering_attachments = {}
  peering_accepter_attachments = {}
  vpn_attachments = {}
  dx_gateway_attachments = {}
  network_function_attachments = {}
}
```

### {tgw-name}-rt-{name}/locals.tf (自動生成)

```hcl
locals {
  route_table_name = "tgw-rt-production"

  associations = {
    tgw_attachment_vpc1 = {
      attachment_key  = "tgw_attachment_vpc1"
      attachment_type = "vpc"
    }
  }

  propagations = {}

  tgw_routes = {
    route_10_2_0_0_16 = {
      destination_cidr_block = "10.2.0.0/16"
      attachment_key         = "tgw_attachment_vpc2"
      attachment_type        = "vpc"
    }
    route_blackhole = {
      destination_cidr_block = "10.99.0.0/16"
      blackhole              = true
    }
  }
}
```

## 重要な制限事項

### VPC Routes は管理対象外

VPC 内のルートテーブルに設定される Transit Gateway 向けルート（`aws_route`）は、Terraform の制限により import できません。

**影響:**
- `terraform plan` で "VPC route already exists" エラーは出ない（管理していないため）
- VPC Routes は手動または別の方法で管理する必要がある

**対象リソース:**
- ✗ `aws_route` (VPC route table → TGW)
- ✓ `aws_ec2_transit_gateway_route` (TGW route table → VPC/Peering/VPN/DX)

## トラブルシューティング

### "Unable to find remote state" エラー

**原因:** {tgw-name}-rt-{name} が参照する tgw-{name} の state が存在しない

**解決方法:**
```bash
# tgw を先にインポート
cd terraform/tgw-multi_vpc_tgw
terraform init
./import.sh
terraform apply

# その後 route table をインポート
cd ../multi_vpc_tgw-rt-production
terraform init
./import.sh
```

### "Resource already exists" エラー

**原因:** すでにインポート済みのリソースを再度インポートしようとしている

**解決方法:**
```bash
# State を確認
terraform state list

# 不要な場合は削除
terraform state rm 'aws_ec2_transit_gateway_route.this["route_xxx"]'
```

### CloudFormation タグの差分

**原因:** AWS リソースが CloudFormation で作成されている

**解決方法:** main.tf で ignore_changes を設定（既に実装済み）
```hcl
lifecycle {
  ignore_changes = [
    tags["aws:cloudformation:stack-name"],
    tags["aws:cloudformation:stack-id"],
    tags["aws:cloudformation:logical-id"]
  ]
}
```

## 複数アカウント・リージョン管理

### ディレクトリ構成例

```
terraform/
├── account1-tokyo/         # 本番環境 (ap-northeast-1)
│   ├── tgw-main/
│   └── main-rt-{name}/
│
├── account2-oregon/        # 検証環境 (us-west-2)
│   ├── tgw-dev/
│   └── dev-rt-{name}/
│
└── shared-tokyo/           # 共有サービス用
    ├── tgw-shared/
    └── shared-rt-{name}/
```

### ワークフロー

```bash
# 1. 各環境のリソース情報を取得
AWS_PROFILE=account1 AWS_REGION=ap-northeast-1 ./scripts/fetch_aws_resources.sh
AWS_PROFILE=account2 AWS_REGION=us-west-2 ./scripts/fetch_aws_resources.sh

# 2. 各環境の設定を生成
python3 scripts/generate_terraform_config.py \
  --input-dir ./aws_resources/111111111111/ap-northeast-1 \
  --output-dir ./terraform/account1-tokyo

python3 scripts/generate_terraform_config.py \
  --input-dir ./aws_resources/222222222222/us-west-2 \
  --output-dir ./terraform/account2-oregon

# 3. インポート実行
cd terraform/account1-tokyo/tgw-main && terraform init && ./import.sh && terraform apply
cd ../main-rt-production && terraform init && ./import.sh && terraform apply
```

## スクリプトオプション

### generate_terraform_config.py

```bash
python3 scripts/generate_terraform_config.py \
  --input-dir ./aws_resources/123456789012/ap-northeast-1 \
  --output-dir ./terraform \
  --account-id 123456789012 \
  --region ap-northeast-1
```

### generate_import_commands.py

```bash
python3 scripts/generate_import_commands.py \
  --input-dir ./aws_resources/123456789012/ap-northeast-1 \
  --output-dir ./terraform
```

## ライセンス

MIT License

## 参考ドキュメント

- [AWS Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/)
- [Terraform AWS Provider - Transit Gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway)
