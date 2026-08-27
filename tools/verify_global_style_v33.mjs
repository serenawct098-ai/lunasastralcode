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
  if (!fs.existsSync(path.join(root, relativePath))) {
    failures.push(`missing file: ${relativePath}`);
  }
}
for (const relativePath of deprecatedFiles) {
  if (fs.existsSync(path.join(root, relativePath))) {
    failures.push(`deprecated file remains: ${relativePath}`);
  }
}

const playbook = fs.readFileSync(
  path.join(root, 'lunas_astral_code_master_playbook.md'),
  'utf8',
);
const index = fs.readFileSync(
  path.join(root, 'scripts/60day_scripts_INDEX.md'),
  'utf8',
);
let ruleMap;
try {
  ruleMap = JSON.parse(
    fs.readFileSync(
      path.join(root, 'governance/latest_playbook_rule_map.json'),
      'utf8',
    ),
  );
} catch (error) {
  failures.push(`invalid rule map JSON: ${error.message}`);
}

const styleApplication = ruleMap?.sentence_quality?.style_application ?? [];
const checks = [
  [
    'Master Playbook 是唯一全局文風規範',
    playbook.includes('使用者文章風格與自然中文（v3.4，全局唯一文風規範）') &&
      playbook.includes('本節是唯一可編輯的全局文風規範'),
  ],
  [
    '新版四步文風鏈已收斂至 Master Playbook',
    playbook.includes('狀態 → 接住 → 轉向 → 留白'),
  ],
  [
    'Master Playbook 不再依賴獨立文風檔',
    !playbook.includes('social_divination_style_profile_v33.md'),
  ],
  [
    '規則映射已更新為 v3.4',
    ruleMap?.sentence_quality?.version === '3.4',
  ],
  [
    '規則映射包含四步文風鏈',
    styleApplication.includes('狀態→接住→轉向→留白'),
  ],
  [
    '規則映射包含第三人斷言限制',
    ruleMap?.sentence_quality?.abstraction_boundary?.includes('不得替第三人下定論'),
  ],
  [
    '腳本索引已同步且不再引用獨立文風檔',
    index.includes('使用者文章風格 v3.4') &&
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
