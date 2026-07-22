const OPS: [keys: string, name: string, expect: string][] = [
  ["V35E", "ランプテスト", "全表示 88 + 全ランプ点灯（約 5 秒）"],
  ["V16 N36 E", "ミッション時計を監視", "R1=時 R2=分 R3=秒が刻む"],
  ["V16 N65 E", "サンプル時刻", "押した瞬間の AGC 時刻を表示"],
  ["V05 N09 E", "アラームコード表示", "直近のアラーム（8進）。1202 はここ"],
  ["V34E", "モニタ終了", "連続表示が止まる"],
  ["RSET", "エラーランプ消灯", "OPR ERR / RESTART が消える"],
];

export function CheatSheet() {
  return (
    <div className="panel">
      <h2>チートシート — 試せる操作</h2>
      <table className="cheat-table">
        <tbody>
          {OPS.map(([keys, name, expected]) => (
            <tr key={keys}>
              <td className="cheat-keys">{keys}</td>
              <td>
                <div className="cheat-name">{name}</div>
                <div className="cheat-expect">{expected}</div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="cheat-note">
        E = ENTR。打ち間違いは CLR（数字の訂正）か RSET。V=動詞（何をするか）、
        N=名詞（何に対して）— 「V16 N36」=「時計を連続監視せよ」という一文になる。
      </p>
    </div>
  );
}
