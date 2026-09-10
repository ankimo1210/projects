import { Database, AlertTriangle, LoaderCircle } from "lucide-react";
import { DataLoadError } from "@/lib/data";
export function DataState({
  error,
  loading,
  empty = "この期間の記録はありません。",
}: {
  error?: Error | null;
  loading?: boolean;
  empty?: string;
}) {
  const missing = error instanceof DataLoadError && error.kind === "missing";
  return (
    <div className="data-state" role={error ? "alert" : "status"}>
      {loading ? (
        <LoaderCircle className="animate-spin" />
      ) : error && !missing ? (
        <AlertTriangle />
      ) : (
        <Database />
      )}
      <strong>
        {loading
          ? "記録を読み込んでいます"
          : missing
            ? "エクスポートが見つかりません"
            : error
              ? "記録を表示できません"
              : empty}
      </strong>
      <p>
        {loading
          ? "保存されたスナップショットを確認しています。"
          : error
            ? missing
              ? "ローカルの health export-web で閲覧データを書き出してください。"
              : error.message
            : "取得状況は「データ棚卸し」で確認できます。欠損値をゼロには置き換えていません。"}
      </p>
    </div>
  );
}
