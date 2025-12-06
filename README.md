# AWS Transit Gateway Terraform Importer

AWS Transit Gatewayの既存リソースをTerraform管理下に置くためのツールセットです。**ルートテーブルごとにディレクトリを分割**し、大規模環境でも管理しやすい構成を実現します。

## 特徴

- **ルートテーブル単位の分割管理**: 各ルートテーブルを独立したディレクトリで管理し、tfstate肥大化を防止
- **完全自動生成**: 既存AWSリソースからTerraform設定とインポートスクリプトを自動生成
- **モジュールレス設計**: for_eachベースのシンプルな構造で柔軟性と保守性を両立
- **全接続タイプ対応**: VPC, Peering, VPN, Direct Connect Gateway すべてサポート
- **Production Ready**: lifecycle ignore_changes や適切なエラーハンドリングを実装

## ディレクトリ構造

```
terraform/
├── tgw/              # Transit Gateway 本体
│   ├── main.tf            # TGW リソース定義
│   ├── locals.tf          # TGW 設定 (自動生成)
│   ├── outputs.tf         # TGW ID を output
│   ├── versions.tf        # Provider 設定
│   └── import.sh          # インポートスクリプト (自動生成)
│
├── rt-production/          # Production ルートテーブル
│   ├── main.tf            # リソース定義 (for_each)
│   ├── locals.tf          # 全設定 (自動生成)
│   ├── data.tf            # tgw/ から TGW ID 参照
│   ├── versions.tf
│   └── import.sh          # インポートスクリプト (自動生成)
│
├── rt-development/         # Development ルートテーブル
│   └── (同様の構成)
│
└── rt-common/              # Shared ルートテーブル
    └── (同様の構成)
```

### 設計思想

1. **State分離**: ルートテーブルごとに独立したterraform.tfstate
2. **爆発半径の最小化**: 1つのルートテーブルの問題が他に波及しない
3. **並列作業**: 複数のルートテーブルを同時に変更可能
4. **シンプルさ**: モジュールを使わず、locals.tf のみで設定完結

## 対応する接続タイプ

| 接続タイプ | リソース | 説明 |
|----------|---------|------|
| VPC | `aws_ec2_transit_gateway_vpc_attachment` | VPC との接続 |
| Peering | `aws_ec2_transit_gateway_peering_attachment` | リージョン間・アカウント間 TGW ピアリング |
| VPN | `aws_vpn_connection` | Site-to-Site VPN (Customer Gateway 経由) |
| Direct Connect | `aws_dx_gateway_association` | オンプレミスとの Direct Connect 接続 |

## 前提条件

- **Terraform**: >= 1.5
- **Python**: >= 3.8
- **AWS CLI**: 認証情報が設定済み
- **jq**: JSON処理用

## クイックスタート

### 1. AWSリソース情報を取得

```bash
# AWS認証情報を設定
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_SESSION_TOKEN="your-token"  # 一時認証情報の場合

# リソース情報を取得 (VPN, DX含む)
./scripts/fetch_aws_resources.sh

# 別リージョンの場合
AWS_REGION=us-west-2 ./scripts/fetch_aws_resources.sh

# 別のAWSプロファイルを使用する場合
AWS_PROFILE=production ./scripts/fetch_aws_resources.sh

# 複数アカウント・リージョンを管理する場合
AWS_PROFILE=account1 AWS_REGION=ap-northeast-1 ./scripts/fetch_aws_resources.sh
AWS_PROFILE=account2 AWS_REGION=us-west-2 ./scripts/fetch_aws_resources.sh
```

出力先ディレクトリ構造:
```
output/
├── 123456789012/           # アカウントID
│   ├── ap-northeast-1/     # リージョン
│   │   ├── transit-gateways.json
│   │   └── ...
│   └── us-west-2/
│       └── ...
└── 987654321098/           # 別のアカウント
    └── ap-northeast-1/
        └── ...
```

取得されるリソース:
- Transit Gateway 本体
- Transit Gateway Route Tables
- VPC/Peering/VPN/DX Attachments
- Associations/Propagations
- Transit Gateway Routes & VPC Routes

### 2. Terraform設定を自動生成

**重要**: 複数の Transit Gateway が存在する場合、スクリプトは `DefaultRouteTableAssociation = disable` の TGW を優先的に選択します。これは通常、カスタムルートテーブルで管理される TGW であり、Terraform で管理したい対象です。

```bash
# 単一アカウント・リージョンの場合 (自動検出)
python3 scripts/generate_terraform_config.py \
  --input-dir ./output/123456789012/ap-northeast-1

# 複数アカウント・リージョンを管理する場合
python3 scripts/generate_terraform_config.py \
  --input-dir ./output/123456789012/ap-northeast-1 \
  --output-dir ./terraform/account1-tokyo

python3 scripts/generate_terraform_config.py \
  --input-dir ./output/987654321098/us-west-2 \
  --output-dir ./terraform/account2-oregon

# アカウントIDとリージョンを明示的に指定
python3 scripts/generate_terraform_config.py \
  --input-dir ./output/123456789012/ap-northeast-1 \
  --account-id 123456789012 \
  --region ap-northeast-1
```

生成されるファイル:
```
terraform/
├── tgw/locals.tf
├── rt-production/locals.tf
├── rt-development/locals.tf
└── rt-common/locals.tf
```

### 3. インポートスクリプトを生成

```bash
# 単一アカウント・リージョンの場合
python3 scripts/generate_import_commands.py \
  --input-dir ./output/123456789012/ap-northeast-1

# 複数アカウント・リージョンを管理する場合
python3 scripts/generate_import_commands.py \
  --input-dir ./output/123456789012/ap-northeast-1 \
  --output-dir ./terraform/account1-tokyo

python3 scripts/generate_import_commands.py \
  --input-dir ./output/987654321098/us-west-2 \
  --output-dir ./terraform/account2-oregon
```

生成されるファイル:
```
terraform/
├── tgw/import.sh
├── rt-production/import.sh
├── rt-development/import.sh
└── rt-common/import.sh
```

### 4. Transit Gateway をインポート

```bash
cd terraform/tgw
terraform init
./import.sh
terraform plan
terraform apply  # タグ等の差分を適用
```

### 5. 各ルートテーブルをインポート

**アーキテクチャ**: VPC Attachments の集中管理

**全てのVPC Attachment (VPC, Peering) はグローバルリソース**であり、`terraform/tgw/` ディレクトリで一元管理されます。各route tableは、これらのattachmentを参照して associations/propagations/routes を管理します。

**自動生成される構成**:

1. **`terraform/tgw/`**: Transit Gateway本体とすべてのVPC/Peering attachmentsを管理
2. **`terraform/rt-*/`**: 各route tableとassociations/propagations/routesを管理
3. **参照方法**: route tableは`data "terraform_remote_state" "tgw"`でattachment IDsを参照

**インポート手順**:

```bash
# 1. TGWとすべてのVPC Attachmentsをインポート
cd terraform/tgw
terraform init
./import.sh
terraform apply

# 2. 各route tableをインポート
cd ../rt-production
terraform init
./import.sh

# 差分確認と適用
terraform plan
terraform apply
```

他のルートテーブルも同様に実行します。

## locals.tf の構造

### tgw/locals.tf (Transit Gateway本体とAttachments)

```hcl
locals {
  region      = "ap-northeast-1"
  account_id  = "899824927162"
  environment = "production"

  # Transit Gateway configuration
  transit_gateway = {
    name                            = "multi-vpc-tgw"
    description                     = "Transit Gateway"
    amazon_side_asn                 = 64512
    auto_accept_shared_attachments  = "enable"
    default_route_table_association = "disable"
    default_route_table_propagation = "disable"
    dns_support                     = "enable"
    vpn_ecmp_support                = "enable"
  }

  # VPC Attachments (全VPC Attachmentsをここで管理)
  vpc_attachments = {
    tgw_attachment_vpc1 = {
      name       = "tgw-attachment-vpc1"
      vpc_id     = "vpc-xxxxx"
      subnet_ids = ["subnet-xxxxx"]
    }
  }

  # Peering Attachments (inter-region)
  peering_attachments = {
    tgw_peering_us_west_2 = {
      name                    = "tgw-peering-us-west-2"
      peer_transit_gateway_id = "tgw-xxxxx"
      peer_region             = "us-west-2"
    }
  }

  # VPN/DX Attachments
  vpn_attachments = {}
  dx_gateway_attachments = {}

  # Common tags
  tags = {
    ManagedBy   = "Terraform"
    Project     = "TransitGateway"
    Environment = local.environment
  }
}
```

### rt-*/locals.tf (Route TableとRoutes)

```hcl
locals {
  route_table_name = "tgw-rt-production"

  # Associations: このルートテーブルに関連付けるアタッチメント
  # attachment_keyはtgw/locals.tfで定義されたキーを参照
  associations = {
    tgw_attachment_vpc1 = {
      attachment_key  = "tgw_attachment_vpc1"
      attachment_type = "vpc"
    }
  }

  # Propagations: ルート自動伝播を有効化
  propagations = {}

  # Transit Gateway Routes (静的ルート)
  tgw_routes = {
    route_10_2_0_0_16 = {
      destination_cidr_block = "10.2.0.0/16"
      attachment_key         = "tgw_attachment_vpc1"
      attachment_type        = "vpc"
    }
    route_blackhole = {
      destination_cidr_block = "192.168.0.0/16"
      blackhole              = true
    }
  }

  route_table_tags = {}
}
```

## リソース追加方法

### VPC Attachment を追加

1. **`terraform/tgw/locals.tf`を編集** (VPC Attachmentはここで管理):

```hcl
vpc_attachments = {
  # 既存...
  tgw_attachment_vpc2 = {
    name       = "tgw-attachment-vpc2"
    vpc_id     = "vpc-yyyyy"
    subnet_ids = ["subnet-yyyyy"]
  }
}
```

```bash
cd terraform/tgw
terraform plan
terraform apply
```

2. **route tableで新しいattachmentを使用** (`terraform/rt-production/locals.tf`):

```hcl
associations = {
  # 既存...
  tgw_attachment_vpc2 = {
    attachment_key  = "tgw_attachment_vpc2"
    attachment_type = "vpc"
  }
}
```

```bash
cd ../rt-production
terraform plan
terraform apply
```

### Route を追加

route tableの `locals.tf` を編集:

```hcl
tgw_routes = {
  # 既存...
  route_10_200_0_0_16 = {
    destination_cidr_block = "10.200.0.0/16"
    attachment_key         = "tgw_attachment_vpc1"
    attachment_type        = "vpc"
  }
}
```

```bash
terraform plan
terraform apply
```

### 新しいルートテーブルを追加

```bash
# テンプレートとして既存のディレクトリをコピー
cp -r terraform/rt-production terraform/rt-staging

# locals.tf を編集
cd terraform/rt-staging
vim locals.tf

# Terraform実行
terraform init
terraform plan
terraform apply
```

## Transit Gateway ID の参照方法

各ルートテーブルは `data.tf` で共有リソースから TGW ID を参照:

```hcl
data "terraform_remote_state" "shared" {
  backend = "local"
  config = {
    path = "../tgw/terraform.tfstate"
  }
}

locals {
  transit_gateway_id = data.terraform_remote_state.shared.outputs.transit_gateway_id
  region             = data.terraform_remote_state.shared.outputs.region
  common_tags        = data.terraform_remote_state.shared.outputs.tags
}
```

この設計により:
- ✅ TGW ID は tgw/ でのみ管理
- ✅ 各ルートテーブルは remote state で参照
- ✅ 変更の影響範囲を最小化

## 命名規則

詳細は [NAMING_CONVENTION.md](NAMING_CONVENTION.md) を参照してください。

### ディレクトリ名
- `tgw` - Transit Gateway 本体
- `rt-{name}` - ルートテーブル (例: `rt-production`)

### リソース名
- 単一リソース: `this`
- 複数リソース: `this["key"]`

### Attachment Key
- ハイフン → アンダースコア
- 小文字に統一
- 例: `tgw-attachment-vpc1` → `tgw_attachment_vpc1`

## 重要な制限事項

### インポートできないリソース

Terraformの制限により、以下のリソースは**インポートできません**。既存のルートを含む環境では、これらを手動で削除または設定ファイルから除外する必要があります:

#### 1. VPC Route Table内のTGWへのRoute

VPC route table内のTransit Gatewayへのルート (aws_route) はインポートできません。

**対処方法:**
- 既存のVPC routesは設定ファイルから削除してください
- インポート後に**新しく追加するroute**のみを定義します

```hcl
# rt-*/locals.tf
locals {
  # VPC Routes
  # Note: Pre-existing VPC routes cannot be imported in Terraform
  # Only new routes added after import should be defined here
  vpc_routes = {}
}
```


#### 影響と運用

- **インポート時**: 既存のVPC routesは設定から除外されるため、Terraformで管理されません
- **変更時**: 既存のVPC routesを変更したい場合はAWSコンソールまたはAWS CLIで直接操作が必要
- **新規追加**: インポート後に追加するVPC routeはTerraformで正常に管理できます
- **TGW Routes**: Transit Gateway route table内のroute (aws_ec2_transit_gateway_route) はインポート可能ですが、本ツールでは自動生成されたroutesを削除して手動管理することを推奨しています

**推奨ワークフロー:**
1. インポート実行 (既存のVPC routesとTGW routesは除外)
2. `terraform apply` で現状を確認
3. 新しいrouteを `locals.tf` に追加
4. `terraform plan` で差分確認
5. `terraform apply` で新規routeを作成

## トラブルシューティング

### 複数の Transit Gateway がある場合

スクリプトは `DefaultRouteTableAssociation = disable` の TGW を自動的に選択します。別の TGW を使用したい場合:

1. 生成された `terraform/tgw/locals.tf` を確認
2. 必要に応じて TGW ID や設定を手動で修正
3. 対応するルートテーブルのみが処理されるため、不要なディレクトリは削除

### "Resource already managed" エラー

```bash
terraform state rm 'aws_ec2_transit_gateway_vpc_attachment.this["tgw_attachment_vpc1"]'
terraform import 'aws_ec2_transit_gateway_vpc_attachment.this["tgw_attachment_vpc1"]' tgw-attach-xxxxx
```

### Association のインポート

import.sh で attachment ID を補完してください:

```bash
# インポート形式: {route_table_id}_{attachment_id}
terraform import 'aws_ec2_transit_gateway_route_table_association.this["tgw_attachment_vpc1"]' \
  tgw-rtb-xxxxx_tgw-attach-yyyyy
```

### Direct Connect Gateway のインポート

```bash
# インポート形式: {dx_gateway_id}/{tgw_id}
terraform import 'aws_dx_gateway_association.this["tgw_dx_tokyo"]' \
  xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/tgw-xxxxx
```

## ベストプラクティス

### ディレクトリ分割の基準
- **環境別**: rt-production, rt-development, rt-staging
- **用途別**: rt-egress, rt-inspection, rt-transit
- **ゾーン別**: rt-dmz, rt-internal, rt-external

### 運用フロー
1. tgw/ で TGW 本体を管理
2. 各ルートテーブルは独立して変更可能
3. terraform plan で必ず差分確認
4. テスト環境で検証してから本番適用

### バージョン管理
- `*.tf`, `*.md`, `scripts/` を Git 管理
- `terraform.tfstate`, `.terraform/` は .gitignore
- S3 バックエンドの使用を推奨 (本番環境)

## 複数アカウント・リージョン管理

### ディレクトリ構成例

複数のAWSアカウントやリージョンで Transit Gateway を管理する場合:

```
terraform/
├── account1-tokyo/         # 本番環境 (ap-northeast-1)
│   ├── tgw/
│   ├── rt-production/
│   └── rt-development/
│
├── account1-osaka/         # 本番環境 (ap-northeast-3)
│   ├── tgw/
│   └── rt-dr/
│
├── account2-oregon/        # 検証環境 (us-west-2)
│   ├── tgw/
│   └── rt-staging/
│
└── shared-tokyo/           # 共有サービス用アカウント
    ├── tgw/
    ├── rt-common-services/
    └── rt-egress/
```

### ワークフロー例

```bash
# 1. 各環境のリソース情報を取得
AWS_PROFILE=prod-tokyo AWS_REGION=ap-northeast-1 ./scripts/fetch_aws_resources.sh
AWS_PROFILE=prod-osaka AWS_REGION=ap-northeast-3 ./scripts/fetch_aws_resources.sh
AWS_PROFILE=staging AWS_REGION=us-west-2 ./scripts/fetch_aws_resources.sh

# 2. 各環境の設定を生成
python3 scripts/generate_terraform_config.py \
  --input-dir ./output/111111111111/ap-northeast-1 \
  --output-dir ./terraform/account1-tokyo

python3 scripts/generate_terraform_config.py \
  --input-dir ./output/111111111111/ap-northeast-3 \
  --output-dir ./terraform/account1-osaka

python3 scripts/generate_terraform_config.py \
  --input-dir ./output/222222222222/us-west-2 \
  --output-dir ./terraform/account2-oregon

# 3. インポートスクリプトを生成
python3 scripts/generate_import_commands.py \
  --input-dir ./output/111111111111/ap-northeast-1 \
  --output-dir ./terraform/account1-tokyo

# 4. 各環境で個別に apply
cd terraform/account1-tokyo/tgw && terraform init && ./import.sh && terraform apply
cd ../../account1-osaka/tgw && terraform init && ./import.sh && terraform apply
```

### リモートバックエンド (S3)

本番環境では S3 バックエンドを推奨。アカウントIDとリージョンをキーに含めることで、複数環境を整理して管理できます:

```hcl
# account1-tokyo/tgw/versions.tf
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "tgw/111111111111/ap-northeast-1/tgw/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# account1-tokyo/rt-production/versions.tf
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "tgw/111111111111/ap-northeast-1/rt-production/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# account1-tokyo/rt-production/data.tf
data "terraform_remote_state" "shared" {
  backend = "s3"
  config = {
    bucket = "your-terraform-state-bucket"
    key    = "tgw/111111111111/ap-northeast-1/tgw/terraform.tfstate"
    region = "ap-northeast-1"
  }
}
```

生成されたファイルには、S3バックエンドを有効化するためのコメント付きテンプレートが含まれています。コメントを外して使用してください。

## スクリプトリファレンス

### fetch_aws_resources.sh
既存 AWS リソースの情報を JSON 形式で取得

**環境変数:**
- `AWS_REGION`: リージョン (デフォルト: `ap-northeast-1`)
- `AWS_PROFILE`: AWS CLI プロファイル (デフォルト: なし)
- `AWS_ACCOUNT_ID`: アカウントID (自動取得可能)
- `OUTPUT_DIR`: 出力先ディレクトリ (デフォルト: `./output`)

**出力先:**
`${OUTPUT_DIR}/${ACCOUNT_ID}/${REGION}/` に JSON ファイルを出力

### generate_terraform_config.py
ルートテーブルごとに分割された Terraform 設定を生成

**オプション:**
- `--input-dir`: 入力ディレクトリ (デフォルト: `./output`)
- `--output-dir`: 出力ディレクトリ (デフォルト: `./terraform`)
- `--account-id`: アカウントID (入力パスから自動検出可能)
- `--region`: リージョン (入力パスから自動検出可能)

**自動検出:**
入力ディレクトリが `./output/{account_id}/{region}/` の形式の場合、アカウントIDとリージョンを自動検出

### generate_import_commands.py
各ディレクトリ用のインポートスクリプトを生成

**オプション:**
- `--input-dir`: 入力ディレクトリ (デフォルト: `./output`)
- `--output-dir`: 出力ディレクトリ (デフォルト: `./terraform`)
- `--account-id`: アカウントID (入力パスから自動検出可能)
- `--region`: リージョン (入力パスから自動検出可能)

## ファイル一覧

| ファイル | 編集 | 説明 |
|---------|-----|------|
| `tgw/locals.tf` | △ | TGW 設定 (初回のみ) |
| `tgw/main.tf` | ✗ | TGW リソース定義 |
| `tgw/outputs.tf` | ✗ | TGW ID 出力 |
| `rt-*/locals.tf` | ◯ | **頻繁に編集** |
| `rt-*/main.tf` | ✗ | リソース定義 |
| `rt-*/data.tf` | ✗ | TGW参照 (remote state) |

**通常の運用では `locals.tf` のみを編集します。**

## ライセンス

このプロジェクトはサンプルコードです。自由に使用・改変してください。

## 参考ドキュメント

- [NAMING_CONVENTION.md](NAMING_CONVENTION.md) - 命名規則の詳細
- [TEST_RESULTS.md](TEST_RESULTS.md) - テスト結果レポート
- [Terraform AWS Provider - EC2 Transit Gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway)
- [AWS Transit Gateway Documentation](https://docs.aws.amazon.com/vpc/latest/tgw/)
