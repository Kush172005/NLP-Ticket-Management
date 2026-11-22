import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
import { finalizePresentation, resolvePresentationFont } from '/Users/kush/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.22136/skills/presentations/container_tools/artifact_tool_utils.mjs';

const buildDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(buildDir, '../..');
const skillDir = '/Users/kush/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.22136/skills/presentations';
const runtimePython = '/Users/kush/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const stats = JSON.parse(await fs.readFile(path.join(root, 'reports/m2_stats.json'), 'utf8'));
const font = resolvePresentationFont({ fontFamily: 'Arial' });
const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const colors = { navy: '#173e5c', teal: '#14847e', ink: '#243b4d', gray: '#5a6c78', light: '#eef4f6', orange: '#bb752b' };

function text(slide, value, x, y, width, height, size = 25, options = {}) {
  const shape = slide.shapes.add({ geometry: 'textbox', position: { left: x, top: y, width, height },
    fill: 'none', line: { fill: 'none', width: 0 } });
  shape.text = value;
  shape.text.style = { typeface: font, fontSize: size, color: colors.ink, verticalAlignment: 'top',
    autoFit: 'none', insets: 0, ...options };
  return shape;
}
function line(slide, x, y, w, color = colors.teal) {
  slide.shapes.add({ geometry: 'rect', position: { left: x, top: y, width: w, height: 3 },
    fill: color, line: { fill: 'none', width: 0 } });
}
function slide(title, notes) {
  const s = p.slides.add();
  s.background.fill = '#ffffff';
  text(s, title, 64, 42, 1150, 68, 36, { bold: true, color: colors.navy });
  line(s, 64, 123, 1152);
  text(s, String(p.slides.items.length), 1170, 672, 44, 24, 16, { color: colors.gray, alignment: 'right' });
  s.speakerNotes.text = notes;
  return s;
}
function table(s, values, x, y, width, height, widths, size = 23) {
  const t = s.tables.add({ rows: values.length, columns: values[0].length, values,
    left: x, top: y, width, height, columnWidths: widths });
  t.borders.assign({ fill: '#dbe4e9', width: 1, style: 'solid' });
  for (let r = 0; r < values.length; r++) {
    for (let c = 0; c < values[r].length; c++) {
      const cell = t.getCell(r, c);
      cell.fill = r === 0 ? colors.navy : (r % 2 ? '#ffffff' : colors.light);
      cell.text.style = { typeface: font, fontSize: size, color: r === 0 ? '#ffffff' : colors.ink,
        bold: r === 0, verticalAlignment: 'middle', insets: { left: 12, right: 12, top: 8, bottom: 8 } };
    }
  }
  return t;
}
async function picture(s, file, position) {
  const bytes = await fs.readFile(path.join(root, 'reports', file));
  s.images.add({ blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: 'image/png', alt: 'Observed training query length distribution', fit: 'contain', position });
}

{
  const s = p.slides.add();
  s.background.fill = colors.navy;
  text(s, 'Ticket Management\nSystem', 72, 115, 1110, 176, 64, { bold: true, color: '#ffffff' });
  line(s, 72, 328, 150, '#7dd2c7');
  text(s, 'Banking support ticket classification', 72, 373, 1100, 64, 34, { color: '#ffffff' });
  text(s, 'Industry Track: M1 and M2', 72, 484, 1100, 48, 26, { color: '#bde4e0' });
  text(s, 'Problem definition and data preparation', 72, 537, 1100, 48, 26, { color: '#bde4e0' });
  s.speakerNotes.text = 'Our submission covers the Industry Track M1 and M2. We define the business problem and prepare Banking77 data. The endpoint is checked data ready for modelling. This presentation does not report model performance.';
}
{
  const s = slide('M1: Problem and users', 'Manual categorization is the business problem. Intended users are support agents, triage staff and managers. No stakeholder interview or bank pilot has been conducted. Source: docs/M1_PROBLEM_BRIEF.md.');
  text(s, 'Agents must read each query before deciding what the customer needs.', 64, 161, 1120, 88, 32, { bold: true });
  table(s, [['User', 'Need'], ['Support agents', 'Spend less time categorizing each query'], ['Triage staff', 'Apply consistent intent labels'], ['Support managers', 'Understand incoming issues by category']],
    64, 286, 1152, 244, [330, 822]);
  text(s, 'Task: one English banking query, one of 77 intent labels.\nAn agent will review the eventual suggestion.', 64, 565, 1120, 88, 25, { color: colors.teal });
}
{
  const s = slide('M1: Success measures and feasibility', 'All numerical success measures are proposed targets, not observed results or bank requirements. Future timing study uses matched sets, counterbalanced order, and includes correction time. No time savings have been measured. Macro F1 weights intents equally. Source: docs/M1_PROBLEM_BRIEF.md.');
  table(s, [['Future measure', 'Proposed target', 'Evidence needed later'], ['Macro F1', 'At least 0.80', 'Held-out intent predictions'], ['Accuracy', 'At least 0.80', 'Held-out intent predictions'], ['Median categorization time', '20% reduction', 'Matched manual / assisted pilot']],
    64, 165, 1152, 260, [390, 260, 502], 22);
  text(s, 'Feasibility', 64, 462, 480, 42, 28, { bold: true, color: colors.teal });
  text(s, 'Labeled public data\nLaptop-sized preprocessing\nNo GPU or paid API for M2', 64, 519, 520, 114, 25);
  text(s, 'Limits to validate later', 664, 462, 540, 42, 28, { bold: true, color: colors.teal });
  text(s, 'Similar intents and uneven class sizes\nBenchmark data differs from live tickets\nBusiness gains need an agent pilot', 664, 519, 540, 114, 25);
}
{
  const s = slide('M2: Banking77 fits the scoped task', 'Banking77 source: https://github.com/PolyAI-LDN/task-specific-datasets. Paper: Casanueva et al. (2020), Efficient Intent Detection with Dual Sentence Encoders, https://aclanthology.org/2020.nlp4convai-1.5/. Dataset license CC BY 4.0, publisher license retained. Source commit and SHA-256 checksums are in reports/manifest.json.');
  text(s, '13,083 queries', 64, 162, 550, 70, 50, { bold: true, color: colors.teal });
  text(s, '77 banking intents', 664, 162, 550, 70, 50, { bold: true, color: colors.teal });
  table(s, [['Publisher split', 'Rows', 'Blank texts / labels'], ['Training source', '10,003', '0 / 0'], ['Test source', '3,080', '0 / 0']],
    64, 264, 1152, 198, [410, 230, 512], 24);
  text(s, 'English queries with one intent annotation.\nNo ground truth for sentiment, priority, routing or replies.', 64, 505, 1130, 96, 28);
  text(s, 'PolyAI dataset, CC BY 4.0. Original source bytes verified and preserved.', 64, 620, 1130, 32, 20, { color: colors.gray });
}
{
  const s = slide('M2: Preparation pipeline', 'Fixed preprocessing choices are in preprocessing.py and config.py. There is no learned vocabulary, TF-IDF fit or classifier. Source: m2_preprocess.py and docs/DATA_CARD.md. Normalization creates collisions even though original source text strings are unique.');
  const steps = [
    ['1', 'Verify and audit', 'Check source hashes, rows, labels and missing values'],
    ['2', 'Mask and normalize', 'Normalize Unicode, mask patterns, lowercase and expand contractions'],
    ['3', 'Clean the training pool', 'Record empty, conflicting and repeated normalized queries'],
    ['4', 'Check contamination', 'Group lexical duplicates and exclude training groups linked to test'],
    ['5', 'Split and export', 'Keep groups together, save data, statistics and checks']
  ];
  steps.forEach(([n, label, body], i) => {
    const y = 164 + i * 88;
    text(s, n, 64, y, 55, 42, 31, { bold: true, color: colors.teal });
    text(s, label, 145, y, 340, 43, 27, { bold: true });
    text(s, body, 510, y, 690, 68, 23);
  });
  text(s, 'Negations and stopwords remain. No stemming, lemmatization or truncation.', 64, 629, 1140, 32, 22, { color: colors.teal });
}
{
  const s = slide('M2: Cleaning examples from the source', 'These are public source examples, not generated training queries. The first appears in the official training file as train_00001 with label card_arrival. The second appears as train_00574 with label extra_charge_on_statement. Numbers are already masked in the displayed before column. Labels are publisher annotations, not model predictions. Source: reports/cleaning_examples.csv.');
  text(s, 'Before (supported patterns already masked)', 64, 163, 550, 62, 25, { bold: true, color: colors.gray });
  text(s, 'After', 664, 163, 550, 62, 25, { bold: true, color: colors.teal });
  text(s, "What can I do if my card still hasn't arrived after <number> weeks?", 64, 252, 545, 140, 30);
  text(s, 'what can i do if my card still has not arrived after <number> weeks', 664, 252, 545, 140, 30);
  line(s, 64, 421, 1152, '#dbe4e9');
  text(s, 'Why do I see an extra £ <number> charge on my statement?', 64, 458, 545, 122, 30);
  text(s, 'why do i see an extra <number> charge on my statement', 664, 458, 545, 122, 30);
  text(s, 'Contractions expand while negation remains. Amounts and counts lose their numeric values.', 64, 617, 1140, 48, 23, { color: colors.gray });
}
{
  const s = slide('M2: Training data findings', 'Observed data from the revised preparation run. Source: reports/m2_stats.json, reports/class_distribution.csv and reports/ticket_lengths.png. Length counts use whitespace before cleaning. Class sizes refer to the final training subset. The complete distribution across all 77 labels is in reports/class_distribution.png.');
  text(s, 'Class imbalance', 64, 164, 510, 44, 28, { bold: true, color: colors.teal });
  text(s, `${stats.train_class_min} to ${stats.train_class_max}`, 64, 226, 510, 78, 58, { bold: true });
  text(s, 'queries per intent', 64, 306, 510, 40, 26);
  text(s, `${stats.train_imbalance_ratio.toFixed(2)} largest / smallest ratio`, 64, 376, 510, 48, 27, { color: colors.teal });
  text(s, 'Future evaluation should report macro F1\nand recall for every intent.', 64, 465, 530, 100, 27);
  await picture(s, 'ticket_lengths.png', { left: 626, top: 172, width: 590, height: 360 });
  text(s, 'Median 10 words     Mean 11.95 words\n95th percentile 29 words', 664, 558, 540, 85, 24);
}
{
  const s = slide('M2: Exclusions and prepared splits', 'Observed counts from reports/m2_stats.json. Removed rows are accounted for once, in preprocessing order. 10,003 - 2 - 42 - 54 = 9,905 retained source rows. 8,490 + 1,415 = 9,905. Test rows remain 3,080. Validation is the first fold of seeded seven-fold StratifiedGroupKFold and represents about 14.3% of retained official train rows.');
  text(s, 'Training-source exclusions', 64, 160, 550, 45, 28, { bold: true, color: colors.teal });
  text(s, 'Final outputs', 664, 160, 550, 45, 28, { bold: true, color: colors.teal });
  table(s, [['Reason', 'Rows'], ['Conflicting labels', '2'], ['Repeated normalized text', '42'], ['Groups linked to test', '54'], ['Total excluded', '98']],
    64, 228, 550, 320, [420, 130], 22);
  table(s, [['Split', 'Rows', 'Intents'], ['Train', '8,490', '77'], ['Validation', '1,415', '77'], ['Official test', '3,080', '77']],
    664, 228, 550, 320, [240, 180, 130], 23);
  text(s, 'Retained training source: 9,905 rows.\nEach exclusion has a row ID and reason.', 64, 586, 550, 72, 24);
  text(s, 'Seed 42. Groups stay together.\nOfficial test membership and labels remain.', 664, 586, 550, 72, 24);
}
{
  const s = slide('M2: Cross-split contamination checks', 'Exact matches use normalized text. Near matches compare word-trigram sets, require at least three distinct trigrams in each query, and use Jaccard >= 0.85. Connections are transitive. This fixed audit examines test text but does not use test labels to choose parameters or train a model. verify.py independently recomputes matching from saved outputs. Source: preprocessing.py, reports/m2_stats.json and docs/DATA_CARD.md.');
  table(s, [['Split pair', 'Shared cleaned texts', 'Shared duplicate groups'], ['Train / validation', '0', '0'], ['Train / test', '0', '0'], ['Validation / test', '0', '0']],
    64, 169, 1152, 264, [390, 350, 412], 24);
  text(s, 'Near-duplicate rule: word-trigram Jaccard similarity of at least 0.85.\nShort queries use exact matching. Connected queries stay together.', 64, 475, 1140, 95, 25);
  text(s, 'Limit: lexical checks cannot rule out every semantic paraphrase.\nNo customer or conversation IDs are available for stronger grouping.', 64, 590, 1140, 70, 24, { color: colors.gray });
}
{
  const s = slide('M2: Privacy and dataset limitations', 'Pattern counts, not confirmed PII: URLs/emails/card-like/phone-like values each match zero rows in these source files. Other number rule matches 205 official training rows and 49 official test rows. Processed CSVs omit original unmasked text but regexes can miss sensitive content. Public benchmark status is not proof of anonymity. Official test has nine repeated normalized rows and one conflicting normalized-text group; all official benchmark rows and labels are retained. Sources: docs/DATA_CARD.md and reports/m2_stats.json.');
  text(s, 'Privacy controls', 64, 164, 540, 45, 29, { bold: true, color: colors.teal });
  text(s, 'Mask supported contact and numeric patterns.\nKeep unmodified raw files separate.\nOmit an unmasked text column from exports.\nRun the demo locally without storing input.', 64, 238, 540, 237, 26);
  text(s, 'Known limits', 664, 164, 540, 45, 29, { bold: true, color: colors.teal });
  text(s, 'Regexes miss some names, addresses and IDs.\nEnglish banking queries only.\nNo sentiment or priority labels.\nNo measured operational time savings.', 664, 238, 540, 237, 26);
  line(s, 64, 518, 1152, '#dbe4e9');
  text(s, 'We retain all official test rows, including 9 repeated normalized rows\nand 1 normalized-text group with conflicting labels. The data card discloses both.', 64, 558, 1140, 95, 25, { color: colors.gray });
}
{
  const s = slide('M1–M2: Evidence ready for demonstration', 'Demonstrate the HTML report, python3 demo.py, and python3 verify.py from the revised project folder. python3 m2_preprocess.py reproduces all M2 outputs. Full walkthrough and viva answers are in docs/EVALUATION_GUIDE.md. Ten regression tests pass. No model accuracy, trained classifier or fitted vectorizer is part of this version.');
  table(s, [['Requirement', 'Evidence'], ['M1 business case', 'Problem brief, users, targets and feasibility'], ['M2 data understanding', 'Data card, class counts and length statistics'], ['M2 preparation', 'Cleaning examples, exclusions and checked splits'], ['M2 privacy', 'Pattern masking and documented limits']],
    64, 164, 1152, 294, [390, 762], 23);
  text(s, 'Live demo: python3 demo.py\nChecks: python3 verify.py', 64, 503, 1140, 100, 29, { bold: true, color: colors.teal });
  text(s, 'The next milestone will fit features and develop models using the prepared data.', 64, 628, 1140, 36, 22, { color: colors.gray });
}

await fs.mkdir(path.join(buildDir, 'previews'), { recursive: true });
for (let i = 0; i < p.slides.items.length; i++) {
  const png = await p.export({ slide: p.slides.items[i], format: 'png', scale: 1 });
  await fs.writeFile(path.join(buildDir, 'previews', `slide-${String(i + 1).padStart(2, '0')}.png`), new Uint8Array(await png.arrayBuffer()));
}
const candidate = path.join(buildDir, 'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
const final = path.join(root, 'presentation', 'M1_M2_Evaluation.pptx');
await fs.mkdir(path.join(root, '.presentation-validation'), { recursive: true });
const result = await finalizePresentation({
  workspaceDir: root, candidatePath: candidate, finalPath: final, pythonExecutable: runtimePython,
  integrityValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit',
    '--cover-role', 'cover', ...[2, 3, 4, 8, 9, 11].flatMap(n => ['--require-native-table-slide', String(n)])],
  requiredNativeTableOwnerSlides: [2, 3, 4, 8, 9, 11],
  fontPolicy: { basis: 'design', families: [font] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(root, '.presentation-validation', 'validation.json'),
});
console.log('Presentation finalized:', final);
