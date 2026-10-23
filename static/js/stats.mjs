import {$, node, setup, tr, json} from './shared.mjs';
import {formatCount, readChapter, readHome} from './metrics.mjs';

let catalog, homePv, chapterCounts, ready = false, failed = false;

function sumCounts(values) {
  if (values.some((value) => value == null || !Number.isFinite(value))) return null;
  return values.reduce((total, value) => total + value, 0);
}

function chapterLabel(chapter) {
  const number = String(chapter.number).padStart(2, "0");
  return tr(`${number} ${chapter.title}`, `Chapter ${number} · ${chapter.title}`);
}

function render() {
  const status = $("stats-status");
  if (failed) {
    status.hidden = false;
    status.textContent = tr("访问次数暂时无法读取。", "Visit counts could not be loaded.");
  } else if (!ready) {
    status.hidden = false;
    status.textContent = tr("正在读取访问次数…", "Loading visit counts…");
  } else status.hidden = true;

  const chapterValues = catalog ? catalog.chapters.map((chapter) => chapterCounts?.get(chapter.id) ?? null) : null;
  const chapterSum = chapterValues ? sumCounts(chapterValues) : null;
  $("metric-home").textContent = formatCount(ready ? homePv : null);
  $("metric-chapters").textContent = formatCount(chapterSum);
  $("metric-total").textContent = formatCount(homePv == null || chapterSum == null ? null : homePv + chapterSum);

  const list = $("chapter-bars");
  if (!ready || !catalog) {
    list.replaceChildren();
    return;
  }
  const chapters = catalog.chapters.map((chapter) => ({...chapter, pv: chapterCounts.get(chapter.id)}));
  const max = Math.max(0, ...chapters.map((chapter) => Number.isFinite(chapter.pv) ? chapter.pv : 0));
  list.replaceChildren(...chapters.map((chapter) => {
    const row = node("li", undefined, "visit-row");
    const label = node("div", chapterLabel(chapter), "visit-label");
    label.lang = "zh-CN";
    const track = node("div", undefined, "visit-track");
    const fill = node("span", undefined, "visit-fill");
    if (Number.isFinite(chapter.pv) && chapter.pv > 0 && max > 0) fill.style.width = `${(chapter.pv / max) * 100}%`;
    track.append(fill);
    row.append(label, track, node("div", formatCount(chapter.pv), "visit-num"));
    return row;
  }));
}

setup(render);
try {
  catalog = await json("data/textbook/catalog.json");
  if (catalog.schemaVersion !== 1 || !catalog.chapters?.length) throw new Error("Invalid catalog");
  const [home, ...counts] = await Promise.all([readHome(), ...catalog.chapters.map((chapter) => readChapter(chapter.id))]);
  homePv = home;
  chapterCounts = new Map(catalog.chapters.map((chapter, index) => [chapter.id, counts[index]]));
  ready = true;
  render();
} catch (error) {
  console.error(error);
  failed = true;
  render();
}
