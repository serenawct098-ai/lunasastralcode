# Luna's Astral Code

## 用途

本 Repo 是 IG 帳號 @lunasastralcode 的內容生產與治理系統。所有新腳本與內容調整，均以 `lunas_astral_code_master_playbook.md` v4.3 為最高優先級依據。

## 核心檔案

| 檔案 | 用途 |
|---|---|
| `lunas_astral_code_master_playbook.md` | 四大型式的固定模板、CTA、可變文案規則、發布與量測要求。 |
| `governance/script_governance.py` | 固定模板合約、動態盤象、跨檔治理稽核與規則映射同步。 |
| `governance/latest_playbook_rule_map.json` | Playbook、動態盤象與文案規則的機器可讀映射。 |
| `governance/script_theme_arc_v43.json` | 23 篇未發布腳本的主題承接與圖騰地圖。 |
| `governance/panxiang_dedup_registry.json` | 型式一／五已登錄的五元組與近 30 篇去重紀錄。 |

## 資料來源鎖定

紫微斗數與奇門遁甲的公式、方位、星曜、四化與吉凶判定，唯一真值來源為 [serenawct098-ai/ziwei_qimen](https://github.com/serenawct098-ai/ziwei_qimen)。

本 Repo 只負責 IG 排版、CTA、視覺規範與內容生產流程。型式三／四涉及命理資料時，先查核 `ziwei_qimen` 的對應引擎；查無依據時標示【資料不足，未核實】。型式一／五只使用已登錄、可去重的動態奇門五元組，不可把大眾互動內容寫成個人起局或個人命盤結論。

## 現行文風與模板邊界

可變文案採 **v4.3 玄學小說式描寫**：一至兩個準確細節，依「鏡頭／狀態 → 動作或停頓 → 命理白話或知識 → 可掌握的下一步 → 留白」推進。型式一／五必須盤象先行；型式三／四必須 SSOT 先行。

> **固定模板保護。** 只有 `［］`／`[]` 變數可以修改；固定字句、CTA、卡數、順序、媒介、秒數、色碼、視覺結構與已登錄五元組均不可任意變動。

## 現行四大型式與 CTA

| 型式 | 內容格式 | CTA 順序 |
|---|---|---|
| 型式一 | 運勢抽籤 Reels | A–F 留言 → 24 小時後置頂解答 |
| 型式三 | 排盤乾貨 Post | 收藏對照 → 留言提問 → 追蹤 |
| 型式四 | 奇門小知識 Post | 分享給朋友一起確認 |
| 型式五 | 大眾奇門上下集 | 上集留言；下集收藏、追蹤與 DM 諮詢 |

型式二已自 v4.3 退役，不再用於新腳本或現行規格。倉庫保留三篇舊型式二來源腳本與相容讀取邏輯，僅供歷史內容追溯，不納入現行排程或模板。

## 驗證

在倉庫根目錄執行：

```bash
python3 -m unittest discover -s governance -p 'test_*.py' -v
python3 governance/script_governance.py audit
node tools/verify_global_style_v43.mjs
```

治理稽核會檢查未發布腳本數量、主題承接、固定 CTA、視覺同步、型式一／五的五元組唯一性、型式五上下集配對、型式三／四 SSOT 定位及 48 小時量測欄位。
