import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const file = path.resolve(here, '../M1_M2_Evaluation.pptx');
const deck = await PresentationFile.importPptx(await FileBlob.load(file));
const target = path.join(here, 'final-previews');
await fs.mkdir(target, { recursive: true });
for (let i = 0; i < deck.slides.items.length; i++) {
  const png = await deck.export({ slide: deck.slides.items[i], format: 'png', scale: 1 });
  await fs.writeFile(path.join(target, `slide-${String(i + 1).padStart(2, '0')}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(`Rendered all ${deck.slides.items.length} final slides.`);
