import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const requiredFiles = [
  'governance/social_divination_style_profile_v33.md',
  'governance/social_divination_style_profile_v33.audit.json',
  'governance/style_source_provenance.md',
  'lunas_astral_code_master_playbook.md',
  'scripts/60day_scripts_INDEX.md',
];

const failures = [];
for (const relativePath of requiredFiles) {
  if (!fs.existsSync(path.join(root, relativePath))) {
    failures.push(`missing file: ${relativePath}`);
  }
}

let audit;
try {
  audit = JSON.parse(
    fs.readFileSync(
      path.join(root, 'governance/social_divination_style_profile_v33.audit.json'),
      'utf8',
    ),
  );
} catch (error) {
  failures.push(`invalid audit JSON: ${error.message}`);
}

const playbook = fs.readFileSync(
  path.join(root, 'lunas_astral_code_master_playbook.md'),
  'utf8',
);
const provenance = fs.readFileSync(
  path.join(root, 'governance/style_source_provenance.md'),
  'utf8',
);
const index = fs.readFileSync(
  path.join(root, 'scripts/60day_scripts_INDEX.md'),
  'utf8',
);
const profile = fs.readFileSync(
  path.join(root, 'governance/social_divination_style_profile_v33.md'),
  'utf8',
);

const checks = [
  ['Playbook v3.3 標題', playbook.includes('使用者文章風格與自然中文（v3.3）')],
  ['Playbook 引用規則檔', playbook.includes('governance/social_divination_style_profile_v33.md')],
  ['來源定位引用規則檔', provenance.includes('governance/social_divination_style_profile_v33.md')],
  ['腳本索引同步 v3.3', index.includes('使用者文章風格 v3.3')],
  ['規則檔標示 design_rule', profile.includes('`design_rule`')],
  ['規則檔保護 SSOT 邊界', profile.includes('不構成命理規則')],
  ['規則檔要求讀者自主', profile.includes('自主收束')],
  [
    '稽核檔列出四個目標文件',
    Array.isArray(audit?.target_files) && audit.target_files.length === 4,
  ],
  [
    '稽核檔未記錄鎖定值變更',
    Array.isArray(audit?.canonical_locks_changes) && audit.canonical_locks_changes.length === 0,
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
  checks: checks.map(([name]) => name),
}, null, 2));
