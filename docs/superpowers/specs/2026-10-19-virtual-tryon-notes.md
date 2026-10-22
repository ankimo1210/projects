# 服の写真を自分の全身に着せるアプリ（仮称 virtual-tryon）検討メモ

- 日付：2026-10-19。状態：ブレインストーミングの途中。設計書ではなく、ユーザーの承認もまだない。このメモを元に設計書（`2026-10-19-virtual-tryon-design.md` の予定）を書く。
- プロジェクトのディレクトリはまだ作っていない。名前も未定。

## 1. ユーザーの発言（発言順）

- 作りたいもの：「洋服の写真を上げるとそれを自動的に私の全身に当てはめてファッションイメージを作ってくれるアプリを作りたい」
- きっかけ：「ネットで服を見てたりクローゼットの服のコーディネートを考えるのがめんどくさいなと思ったから」
- コーデで迷うところ：「色とか上下とか靴とかベルトとか時計とか」
- 誰が使うか：「ゆくゆくはアプリになれば面白いね」
- 端末：「スマホだけどとりあえずPCで動けばいいかな」
- 画像生成の場所：全身写真を外部の AI サービスに送ることに「抵抗はないけどローカルで実装してみたい感はある」
- §2 の要約（推測の項を含む）に「sounds good」

## 2. ここまでの理解

ユーザーが述べたこと：

- 用途は2つ。ネットで見た服が自分に似合うかの確認と、手持ちの服の組み合わせ選び。
- 範囲は上下の服だけでなく、色・靴・ベルト・時計まで含めた全身コーデ。
- 最初は自分専用。PC で動けばよい。普段使うのはスマホ。アプリ化は「ゆくゆくはなれば面白い」程度。
- 画像生成はこの PC の GPU で実装してみたい。理由はプライバシーではなく、ローカルで作ってみたいから。外部送信に抵抗はない。

私の推測（ユーザーは要約として同意したが、個別には詰めていない）：

- 全身写真は1〜数枚を登録し、使い回す。
- 服の写真は、ネットの商品写真とクローゼットで撮った写真の両方を入れる。
- クローゼットの服は登録して一覧にし、そこから組み合わせを選ぶ。
- ローカルの品質が足りないときは、比較用にクラウドの AI サービスを後から足してよい。

## 3. 手元の環境（2026-10-19 に確認）

- GPU：NVIDIA GeForce RTX 5080、VRAM 16,303 MiB、ドライバ 617.42（WSL2 から見えている）。
- メモリ 47 GB、ディスクの空き 676 GB。
- RTX 5080（sm_120）では PyTorch の cu128 以降のビルドが要る（ワークスペースの過去の記録）。

## 4. 調査結果：ローカルで動く試着モデル（2026-10-19、Web 検索）

| 種類 | 代表例 | 扱えるもの | 16 GB で動くか | 商用利用 |
|---|---|---|---|---|
| 服専用の試着モデル | CatVTON、IDM-VTON、FASHN VTON v1.5 | 上下・ワンピース。1回に1着 | 動く（CatVTON は 8 GB 未満、FASHN v1.5 は 972M パラメータ） | CatVTON・IDM-VTON は不可（CC BY-NC-SA）。FASHN v1.5 は可（Apache-2.0） |
| 何でも試着モデル | OmniTry（NeurIPS 2025） | 靴・バッグ・帽子・アクセサリーなど。1回に1点 | 動かない（bf16 で 28 GB 以上） | 不可（土台の FLUX.1-Fill-dev が非商用） |
| 汎用の画像編集モデル（参照画像を複数入れられる） | Qwen-Image-Edit-2511、FLUX.2 klein | 人物と複数のアイテムを1回で合成する（klein は参照4枚まで） | 量子化すれば動く（Qwen の GGUF Q4_K_M が約 13 GB、klein 4B は BFL によると約 13 GB） | Qwen-2511 と klein 4B は可（Apache-2.0。LoRA は個別に確認）。klein 9B は不可 |
| 最新の試着専用モデル | Oxygen-TryOn（JD、arXiv 2607.21694、2026-07） | 2〜4点の同時合成。上下・アウター・靴・バッグ・帽子・眼鏡・アクセサリー・スカーフ（時計とベルトは明記なし） | 重みが未公開（README の TODO に「Model weights」、2026-10-19 に確認）。16B の MMDiT と Qwen3-VL-8B の構成で、16 GB には大きすぎる | repo は Apache-2.0 |

複数アイテムの品質（Oxygen-TryOn 論文の TStars-VTON、2〜4点、10点満点）。Oxygen-TryOn の著者が自分たちで評価し直した数字で、自社モデルに有利な可能性がある。

| モデル | 同時試着（2〜4点） | 1点の試着 |
|---|---|---|
| Oxygen-TryOn | 8.41 | 9.36 |
| Seedream5 Lite（クラウド） | 8.19 | 8.77 |
| GPT-Image-2（クラウド） | 7.90 | 8.34 |
| Nano Banana Pro（クラウド） | 7.69 | 8.04 |
| FLUX.2-dev | 4.59 | 7.76 |
| Qwen-Image-Edit-2511 | 2.35 | 6.10 |

- 同じ論文の「手直しなしで使える割合」は、Qwen-2511 が 53〜56%、FLUX.2-dev が 67〜68%、GPT-Image-2 が 78〜80%。
- FLUX.2 klein は、この比較に入っていない。klein 4B 向けの試着専用 LoRA は見つからなかった。
- Garments2Look（CVPR 2026、全身コーデ試着用の 80K ペアのデータセット）の著者は、「今の手法は全身コーデをきれいに着せることや、重ね着とスタイリングの推定が苦手」と書いている。
- Qwen-2511 は、入力画像が3枚になると作業メモリが増える。RTX 5080 での速度の実測報告は見つからなかった。Lightning LoRA を使うと 4 ステップで生成できる。
- クラウドの選択肢として、BFL が 2026-05 に複数アイテムを扱える試着 API を出している。

## 5. 調査から読み取れること（私の解釈）

- 16 GB の GPU で、小物まで含めた全身コーデを1回で、しかも高品質に作るのは、今の公開モデルでは難しい。
- 現実的な組み立ては2つ。
  - 段階的：服は専用モデルで着せ、小物は汎用の編集モデルで1点ずつ重ねる。工程ごとの誤差が積み上がる。
  - 一括：Qwen-2511 か klein 4B に、人物と最大3点を入れる。品質は妥協する。
- ベルトや時計は、全身画像の中では数十ピクセルしかない。手首や腰の拡大画像を別に作る、といった工夫が必要になりそう。
- 将来アプリにする場合、商用で使えるのは FASHN v1.5、Qwen-2511、klein 4B の系統。CatVTON・IDM-VTON・OmniTry・klein 9B は非商用。

## 6. 未決の点

- ユーザーに聞いている途中：最初の目標は上下の服の着せ替えだけで十分か、靴や小物まで入っていないと意味がないか。
- まだ聞いていないこと：
  - 画面の流れ
  - 結果の見せ方（複数のコーデを並べて比べるか）
  - 1枚の生成に待てる時間
  - 服の登録方法（背景の除去、種類の分け方）
  - 何ができたら成功か
  - 技術的に動いても失敗と言えるのはどんなときか
- 規模の見立て：設計書を書く規模のプロジェクト。設計書の承認後に実装計画へ進む。

## 7. 出典

- [Best Open-Source Virtual Try-On Models in 2026 (FASHN)](https://fashn.ai/blog/comparing-the-top-4-open-source-virtual-try-on-viton-models)
- [Oxygen-TryOn (arXiv 2607.21694)](https://arxiv.org/html/2607.21694) / [GitHub](https://github.com/oxygenVision/Oxygen-TryOn) / [project page](https://oxygenvision.github.io/Oxygen-TryOn)
- [OmniTry GitHub](https://github.com/Kunbyte-AI/OmniTry)
- [Garments2Look (CVPR 2026)](https://openaccess.thecvf.com/content/CVPR2026/papers/Hu_Garments2Look_A_Multi-Reference_Dataset_for_High-Fidelity_Outfit-Level_Virtual_Try-On_with_CVPR_2026_paper.pdf)
- [FLUX.2 Technical Specifications (BFL)](https://help.bfl.ai/articles/4029171097-flux-2-technical-specifications) / [FLUX.2 klein blog](https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence)
- [Qwen-Image-Edit-2511 local VRAM requirements](https://lilting.ch/en/articles/qwen-image-edit-2511-local-specs)
- [Virtual Try-On with Qwen Edit 2511 (sbcode)](https://sbcode.net/genai/virtual-try-on/)
- [10 Best Virtual Try-On APIs in 2026 (fal)](https://fal.ai/learn/tools/best-virtual-try-on-apis-2026)
