# 日付ゲート original_N 修復：限定独立判断

1行の N → original_N 修正を限定承認。旧81源との比較では run_pilot.py の当該1keyだけが変更され、他80源・数式・価格・原N・threshold/driver契約は不変。checker変更やcacheのN別名追加はない。

追加は1つのparametrize testのTrue/False 2ケース。旧26defs/fixture/import/module ASTを保持し、native小cache → 実dategate → writer/read → 実savedcheckerへ接続。原N16、unknown/no_root、16blockの許容誤差つきSE比較、原N32 tamper拒否を確認する。finite block比較は条件付きであり、金融精度の資格ではない。

原REDは2件ともKeyError N。root GREENは246 passed・関連2files Ruff/format PASS。独立は96静的項目と保存GREENの出所を確認し、suiteを再実行していない。

新canonical=5d059dc9…、native=56815c0b…。旧canonical1cc/nativebe、全prior3cf/原partial70のsource失敗は保存。新sourceへのwhole budget/cap recipe、金融実行、main/phase受入は本判断では承認しない。数学資格はunknown。

詳細は同prefix decision/results と current-source-closure。独立の新金融/RNG/SDE/solverは0件、production/Git/CAS mutationは0。Git showはbefore-test確認のread-only2件。費用はsource static1.766518秒、root GREEN136.124262秒（inner135.06秒を加算しない）、各receipt尾部unknownをdecisionへ保持。
