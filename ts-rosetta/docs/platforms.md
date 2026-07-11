# Electron / React Native — プラットフォーム階層（コード解説のみ）

この 2 つは「Web の外」にアプリを届ける階層。今回は実行環境の制約
（Electron は WSLg 必須で重い、RN は実機/エミュレータ必須）により
コードで違いを理解する。**書く言語と UI ライブラリは同じ**（TypeScript + React 系）
という点がエコシステムの強み。

## Electron — デスクトップ = 「ブラウザ + Node.js を同梱して配る」

アーキテクチャ: **main プロセス**（Node.js。ウィンドウ管理・OS アクセス）と
**renderer プロセス**（ブラウザ。この repo の React/Vue アプリがそのまま動く）を
IPC で繋ぐ。

ブラウザ版タスクアプリには絶対できない「ローカルファイルに保存」がこう書ける:

```ts
// main.ts — Node.js 側。fs も dialog も使い放題
import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import { writeFile } from 'node:fs/promises';
import type { Task } from '@rosetta/core';   // 同じ core が使える

ipcMain.handle('save-tasks', async (_e, tasks: Task[]) => {
  const { filePath } = await dialog.showSaveDialog({ defaultPath: 'tasks.json' });
  if (filePath) await writeFile(filePath, JSON.stringify(tasks, null, 2));
});

app.whenReady().then(() => {
  const win = new BrowserWindow({ webPreferences: { preload: 'preload.js' } });
  win.loadFile('dist/index.html');   // ← apps/react のビルド成果物がそのまま載る
});
```

```ts
// preload.ts — 2 つの世界の橋渡し（セキュリティ境界）
import { contextBridge, ipcRenderer } from 'electron';
contextBridge.exposeInMainWorld('desktop', {
  saveTasks: (tasks: Task[]) => ipcRenderer.invoke('save-tasks', tasks),
});
```

```tsx
// React 側の変更はボタン 1 個だけ
<button onClick={() => window.desktop.saveTasks(tasks)}>Save to file…</button>
```

- できるようになること: ファイル/ネイティブダイアログ/メニュー/トレイ/自動更新、
  オフライン配布（.exe / .app / .AppImage）
- 代償: 配布物が Chromium + Node 同梱で **~100MB 超**、メモリ消費大。
  VSCode・Slack・Discord がこの方式。

## React Native — モバイル = 「React 構文でネイティブ部品を描画」

**DOM が存在しない。** `div` も `span` も CSS ファイルもない。
JSX が描画するのは iOS/Android のネイティブ UI 部品。

apps/react の一覧表示を RN に移植するとこうなる:

```tsx
// React (DOM)                        // React Native
<ul className="tasks">                <FlatList
  {visible.map(t => (                   data={visible}
    <li key={t.id}>                     keyExtractor={t => t.id}
      <span>{t.title}</span>            renderItem={({ item }) => (
      <button onClick={...}>✕</button>     <View style={styles.row}>
    </li>                                    <Text>{item.title}</Text>
  ))}                                        <Pressable onPress={...}>
</ul>                                          <Text>✕</Text>
                                             </Pressable>
                                           </View>
                                        )} />
```

```tsx
// スタイルは CSS ではなく JS オブジェクト（flexbox のサブセット）
const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', padding: 8 },
});
```

- 同じもの: コンポーネント/props/useState/useReducer などの **React の考え方全部**。
  `@rosetta/core` の store も**無修正で import できる**（DOM 非依存に作ったため）。
- 違うもの: `<View>/<Text>/<FlatList>` 等の部品、`onClick`→`onPress`、
  CSS→StyleSheet、ナビゲーションやジェスチャは専用ライブラリ。
- ツールチェーン: 現在は **Expo** が標準（`npx create-expo-app`）。実機の
  Expo Go アプリで即動作確認できる（WSL2 でも QR コード経由なら可）。

## 階層としての整理

| | 実行場所 | UI の描画先 | Node API | 配布 |
|---|---|---|---|---|
| SPA (React/Vue/Angular) | ブラウザ | DOM | ✘ | URL |
| Next.js | サーバー+ブラウザ | DOM (SSR+hydration) | サーバー側のみ | URL |
| Electron | 同梱 Chromium + Node | DOM | ✔ (main/preload 経由) | インストーラ |
| React Native | 端末の JS エンジン | ネイティブ部品 | ✘ (RN 専用 API) | アプリストア |

つまり「TypeScript + React を覚えると Web / デスクトップ / モバイルが書ける」は
**UI の考え方とドメインロジック（core）が使い回せる**という意味であって、
描画層とプラットフォーム API はそれぞれ学び直しがある。
