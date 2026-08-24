# Luna's Astral Code

## 用途

本 Repo 為 IG 帳號 @lunasastralcode 的內容生產系統唯一真源。
所有 AI prompt 與內容腳本均以 `lunas_astral_code_master_playbook.md` 為最高優先級參考。

## 核心檔案

| 檔案 | 用途 |
|---|---|
| `lunas_astral_code_master_playbook.md` | 執行規範、五種型式 CTA、正文範本、可變文案治理與完整製作輸出。 |
| `governance/script_governance.py` | 固定模板合約、可變文案重寫與跨檔治理稽核。 |
| `governance/latest_playbook_rule_map.json` | Master Playbook、動態盤象與可變文案規則的機器可讀映射。 |

## 資料來源鎖定

紫微斗數與奇門遁甲的公式、方位、星曜、四化與吉凶判定，唯一真值來源為 [serenawct098-ai/ziwei_qimen](https://github.com/serenawct098-ai/ziwei_qimen)。

本 Repo 只負責 IG 排版、CTA、視覺規範與內容生產流程。腳本涉及年度九宮飛星方位、四化十干對應或安星公式時，先查核 `ziwei_qimen` 對應引擎；查無依據時標示【資料不足，未核實】。

## 可變文案寫作治理

所有可變文案依 Master Playbook 的「共感—重述—賦權—互動」規則撰寫：先命名讀者可辨識的困擾，再以不承諾結果的方式重新理解，最後回到一至兩個低門檻行動。此規則只可作用於 `［］` 或 `[ ]` 變數、置頂解答與完整解讀等可變內容。

> **固定模板保護。** 「五大型式文案排版輸出標準規範」及其固定字句、CTA、卡數、順序、媒介、秒數、色碼與視覺結構均不可修改。型式三／四仍只以 SSOT 為命理資料真源；型式一／五仍只使用已登錄的動態盤象五元組。

## 文件順序

1. Part 5：CTA 組件與行動順序。
2. Part 6：Hook、正文、Hashtags、CTA 的正文輸出範本。
3. Part 7：正文、視覺分鏡、視覺規範與 48 小時量測欄位的完整製作輸出。
4. Master Playbook 第 7 節：只用於可變文案的共感、重述、賦權與互動規則。

## 五種型式與 CTA

| 型式 | 內容格式 | CTA 順序 |
|---|---|---|
| 型式一 | 運勢抽籤 Reels | A–F 留言 → 收藏 → 24 小時後置頂解答 |
| 型式二 | 動態黑底金句 Post | 留言表態 → 收藏 → 轉發 |
| 型式三 | 排盤乾貨 Post | 收藏對照 → 留言提問 → 追蹤 |
| 型式四 | 小知識 Post | 現場檢查 → 留言回報 → 共同轉發 |
| 型式五 | 大眾奇門上下集 Reels | 上集留言＋收藏；下集收藏＋追蹤＋ DM 諮詢 |
