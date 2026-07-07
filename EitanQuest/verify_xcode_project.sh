#!/bin/bash
# EitanQuest プロジェクト設定確認スクリプト
# 使い方: .xcodeproj があるフォルダ（プロジェクトのルート）に移動してから実行してください。
#   cd ~/path/to/EitanQuest
#   bash verify_xcode_project.sh

echo "===== 現在のディレクトリ ====="
pwd

echo ""
echo "===== .xcodeproj の確認 ====="
PROJECT=$(ls -d *.xcodeproj 2>/dev/null | head -n 1)
if [ -z "$PROJECT" ]; then
  echo "❌ このフォルダに .xcodeproj が見つかりません。"
  echo "   .xcodeproj がある階層（プロジェクトのルートフォルダ）に cd してから、もう一度実行してください。"
  exit 1
fi
echo "対象プロジェクト: $PROJECT"

echo ""
echo "===== スキーム一覧 ====="
xcodebuild -list -project "$PROJECT"

SCHEME=$(xcodebuild -list -project "$PROJECT" 2>/dev/null | awk '/Schemes:/{flag=1; next} flag && NF {print $1; exit}')
echo ""
echo "使用するスキーム: $SCHEME"

echo ""
echo "===== 主要ビルド設定（Bundle ID / Deployment Target / Swift Version） ====="
xcodebuild -showBuildSettings -project "$PROJECT" -scheme "$SCHEME" 2>/dev/null \
  | grep -E "PRODUCT_BUNDLE_IDENTIFIER|IPHONEOS_DEPLOYMENT_TARGET|SWIFT_VERSION|^\s*PRODUCT_NAME "

echo ""
echo "===== シミュレータ向けにビルドを試行（テンプレートのままの状態） ====="
xcodebuild build \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -destination 'generic/platform=iOS Simulator'

echo ""
echo "===== 完了 ====="
echo "上に赤い error: が出ていなければ、テンプレート状態でのビルドは成功です。"
echo "この後、私たちのSwiftファイルを組み込んでから、もう一度このスクリプトを実行して比較すると問題の切り分けがしやすいです。"
