import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const requiredFiles = [
  'lunas_astral_code_master_playbook.md',
  'governance/latest_playbook_rule_map.json',
  'governance/script_theme_arc_v42.json',
  'scripts/60day_scripts_INDEX.md',
];
const deprecatedFiles = [
  'governance/social_divination_style_profile_v33.md',
  'governance/social_divination_style_profile_v33.audit.json',
  'governance/style_source_provenance.md',
];

const failures = [];
for (const relativePath of requiredFiles) {
  if (!fs.existsSync(path.join(root, relativePath))) failures.push(`missing file: ${relativePath}`);
}
for (const relativePath of deprecatedFiles) {
  if (fs.existsSync(path.join(root, relativePath))) failures.push(`deprecated file remains: ${relativePath}`);
}

const playbook = fs.readFileSync(path.join(root, 'lunas_astral_code_master_playbook.md'), 'utf8');
const index = fs.readFileSync(path.join(root, 'scripts/60day_scripts_INDEX.md'), 'utf8');
let ruleMap;
let themeMap;
try {
  ruleMap = JSON.parse(fs.readFileSync(path.join(root, 'governance/latest_playbook_rule_map.json'), 'utf8'));
  themeMap = JSON.parse(fs.readFileSync(path.join(root, 'governance/script_theme_arc_v42.json'), 'utf8'));
} catch (error) {
  failures.push(`invalid governance JSON: ${error.message}`);
}

const writing = ruleMap?.writing_tracks ?? {};
const skillRouting = writing.skill_routing ?? [];
const checks = [
  [
    'Master Playbook 使用 v4.2 小說式描寫規則庫',
    playbook.includes('小說式描寫文風（v4.2｜唯一全局文風規範，奇門專用）'),
  ],
  [
    '型式一至五均採小說式描寫，且奇門內容仍盤象先行',
    playbook.includes('型式一、二、三、四、五都使用**玄學小說式描寫**') &&
      playbook.includes('盤象先行，不可調換') &&
      writing.all_forms?.length === 6 && writing.qimen_gate?.includes('盤象先行'),
  ],
  [
    '小說描寫只保留必要細節，且不捏造個人事實',
    playbook.includes('一至兩個可感知細節') &&
      playbook.includes('不虛構精確日期、次數、金額、職業、對話紀錄') &&
      writing.narrative_gate?.includes('一至兩個準確細節'),
  ],
  [
    '規則映射與主題地圖均為 v4.2，且包含 23 篇與 9/28 配對',
    writing.version === '4.2' && themeMap?.version === '4.2' &&
      Object.keys(themeMap?.posts ?? {}).length === 23 &&
      themeMap?.posts?.['2026-09-28']?.topic === themeMap?.posts?.['2026-09-26']?.topic &&
      JSON.stringify(themeMap?.posts?.['2026-09-28']?.totems) === JSON.stringify(themeMap?.posts?.['2026-09-26']?.totems),
  ],
  [
    '三個指定寫作 skills 已納入固定順序路由',
    ['chinese-webnovel-studio', 'good-writing-tw', 'direct-chinese-writing']
      .every((skill) => skillRouting.some((entry) => entry.startsWith(skill))),
  ],
  [
    '固定模板邊界已維持',
    writing.fixed_template_exclusion?.includes('固定模板'),
  ],
  [
    '腳本索引已同步為 v4.2',
    index.includes('小說式描寫文風 v4.2') && !index.includes('使用者文章風格 v3.4') &&
      !index.includes('social_divination_style_profile_v33.md'),
  ],
];

for (const [name, passed] of checks) {
  if (!passed) failures.push(`failed check: ${name}`);
}

if (failures.length > 0) {
  console.error(JSON.stringify({ status: 'failed', failures }, null, 2));
  process.exit(1);
}

console.log(JSON.stringify({
  status: 'passed',
  checked_files: requiredFiles,
  removed_dependencies: deprecatedFiles,
  checks: checks.map(([name]) => name),
}, null, 2));
