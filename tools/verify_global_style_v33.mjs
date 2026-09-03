import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const requiredFiles = [
  'lunas_astral_code_master_playbook.md',
  'governance/latest_playbook_rule_map.json',
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
try {
  ruleMap = JSON.parse(fs.readFileSync(path.join(root, 'governance/latest_playbook_rule_map.json'), 'utf8'));
} catch (error) {
  failures.push(`invalid rule map JSON: ${error.message}`);
}

const trackA = ruleMap?.writing_tracks?.track_a ?? {};
const trackB = ruleMap?.writing_tracks?.track_b ?? {};
const skillRouting = ruleMap?.writing_tracks?.skill_routing ?? [];
const checks = [
  [
    'Master Playbook 是 v4.1 唯一全局文風規範',
    playbook.includes('文風雙軌制（v4.1｜唯一全局文風規範，奇門專用）'),
  ],
  [
    '軌道 A 先盤象後敘事，且禁止跨占卜體系移植',
    playbook.includes('盤象先行') && playbook.includes('不得援引塔羅牌義、牌陣、星座宮位') &&
      trackA.sequence?.includes('盤象先行') && trackA.anti_portability_gate?.includes('不可套用塔羅'),
  ],
  [
    '軌道 B 可用必要敘事場景，但不捏造未提供事實',
    playbook.includes('軌道 B：玄學小說敘事風') && trackB.scene_allowed === true &&
      trackB.rule?.includes('不得捏造精確日期'),
  ],
  [
    '規則映射已更新為 v4.1',
    ruleMap?.writing_tracks?.version === '4.1',
  ],
  [
    '三個指定寫作 skills 已納入路由',
    ['good-writing-tw', 'chinese-webnovel-studio', 'direct-chinese-writing']
      .every((skill) => skillRouting.some((entry) => entry.startsWith(skill))),
  ],
  [
    '固定模板邊界已維持',
    ruleMap?.writing_tracks?.fixed_template_exclusion?.includes('固定模板'),
  ],
  [
    '腳本索引已同步為 v4.1',
    index.includes('文風雙軌制 v4.1') && !index.includes('使用者文章風格 v3.4') &&
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
