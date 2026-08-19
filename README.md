# Luna's Astral Code — Repo 說明

## 用途
本 Repo 為 IG 帳號 @lunasastralcode 的內容生產系統唯一真源（Single Source of Truth）。
所有 AI prompt、內容腳本生成，均以 `lunas_astral_code_master_playbook.md` 作為最高優先級參考。

## 檔案結構
| 檔案 | 說明 |
|---|---|
| `lunas_astral_code_master_playbook.md` | 主操作手冊（執行規範＋五種型式素材模板＋CTA＋排版範本＋策略備忘）|

## 資料來源鎖定（SSOT）
紫微斗數與奇門遁甲相關之公式、方位、星曜、四化、吉凶判定，唯一真值來源為 [serenawct098-ai/ziwei_qimen](https://github.com/serenawct098-ai/ziwei_qimen)。本 Repo（lunasastralcode）僅負責 IG 排版、CTA、視覺規範與內容生產流程；所有腳本涉及命理數據（尤其年度九宮飛星方位、四化十干對應、安星公式）時，必須先查核 ziwei_qimen 對應引擎（`traditional_core_engine_v2.1.json` / `qimen_fengshui_layout_module_v0.1.json` 等），禁止自創方位／星曜／吉凶。無法在 ziwei_qimen 查得依據者，一律標【資料不足，未核實】，不可臆測填補。

## 飛輪階段
**當前：#1** — IG雙帳號地基階段（算命＋礦石）

## 五種型式與 CTA 同步狀態

`lunas_astral_code_master_playbook.md` 的 Part 5 與 Part 6 是五種型式 CTA 與完整正文範本的唯一作業來源。Part 5 說明 CTA 組件與行動順序；Part 6 提供可直接套用的 Hook、正文、Hashtags、CTA、視覺分鏡描述與 48 小時量測欄位。

| 型式 | 內容格式 | CTA 結構基準 | Part 6 範本 |
|---|---|---|---|
| 型式一 | 運勢抽籤 Reels | A–F 留言 → 收藏 → 24 小時後置頂解答 | 型式一｜運勢抽籤排版範本 |
| 型式二 | 動態黑底金句 Post | 留言表態 → 收藏 → 轉發 | 型式二｜動態黑底金句排版範本 |
| 型式三 | 排盤乾貨 Post | 收藏對照 → 留言提問 → 追蹤 | 型式三｜排盤解析乾貨教學排版範本 |
| 型式四 | 小知識 Post | 現場檢查 → 留言回報 → 共同轉發 | 型式四｜小知識排版範本 |
| 型式五 | 大眾奇門上下集 Reels | 上集留言＋收藏；下集收藏＋追蹤＋ DM 諮詢 | 型式五上集／型式五下集｜測驗互動型排版範本 |

> 型式三與型式四涉及星曜、四化、飛星、方位與吉凶時，先查 `ziwei_qimen` SSOT；找不到來源時標示【資料不足，未核實】。型式比例仍依 Master Playbook Part 4 執行，未因 CTA／範本同步而變更。

## 版本
- v2.1 — 2026-08-20，五種型式 CTA 組件庫、完整正文排版範本與 README 同步；型式一／五採用使用者核准的分層 CTA 範本
- v2.0 — 2026-08-01，Master Playbook 重構：新增「30秒鐵律速查」＋「唯一真源總覽」＋鐵律逐條編號（規則1-11）＋執行流程SOP＋可打勾最終自核清單；範本內容不變
- v1.1 — 2026-07-29，新增命理數據SSOT鎖定條款（指向 ziwei_qimen repo）
- v1.0 — 2026-07-24，初版整合（由 execution_standard + CTA_template_library 合併）
