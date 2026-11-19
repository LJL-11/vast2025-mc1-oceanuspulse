<script setup>
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { dataService, friendlyDataError } from '../lib/dataService'
import { genreArtistEvidence } from '../lib/genreArtistEvidence'
import { EDGE_LABELS } from '../lib/palette'

const props = defineProps({ flows: { type: Array, required: true }, focus: { type: String, required: true },
  years: { type: Array, required: true }, selectedId: { type: Number, default: null } })
const emit = defineEmits(['select', 'inspect'])
const evidence = shallowRef(null)
const nodes = shallowRef([])
const loading = ref(false)
const error = ref('')
const query = ref('')
const notableOnly = ref(false)
const limit = ref(10)
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [e, n] = await Promise.all([dataService.influenceEvidence(), dataService.nodeIndex()])
    evidence.value = e.events
    nodes.value = n.nodes
  } catch (cause) { error.value = friendlyDataError(cause) }
  finally { loading.value = false }
}
onMounted(load)
const artists = computed(() => genreArtistEvidence(evidence.value ?? [], nodes.value, props.flows, props.focus))
const matching = computed(() => artists.value.filter(row => (!notableOnly.value || row.notableCount)
  && row.name.toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase())))
const selected = computed(() => artists.value.find(row => row.id === props.selectedId))
const firstYear = computed(() => props.years[0] ?? 1975)
const lastYear = computed(() => props.years.at(-1) ?? 2040)
function yearX(year) { return 5 + (year - firstYear.value) / Math.max(1, lastYear.value - firstYear.value) * 140 }
watch([query, notableOnly, () => props.flows], () => { limit.value = 10 })
</script>

<template>
  <div class="genre-artists">
    <p v-if="loading" class="artist-state" role="status">正在核对作品引用与表演署名…</p>
    <div v-else-if="error" class="artist-state" role="alert">{{ error }}<button class="atlas-inline" @click="load">重试加载</button></div>
    <template v-else>
      <div class="artist-toolbar">
        <label class="artist-search">查找艺人<input v-model="query" type="search" placeholder="输入姓名或组合名" /></label>
        <label class="artist-notable"><input v-model="notableOnly" type="checkbox" />仅看含登榜作品的艺人</label>
        <span>{{ matching.length }} 位 · 按相关引用数排序</span>
      </div>
      <div class="artist-layout">
        <div class="artist-index">
          <div class="artist-columns"><span>表演者 / 组合</span><span>{{ firstYear }}—{{ lastYear }}</span><span>引用 / 作品</span></div>
          <button v-for="(artist, index) in matching.slice(0, limit)" :key="artist.id" type="button" class="artist-row"
            :class="{ 'is-selected': selectedId === artist.id }" :aria-pressed="selectedId === artist.id"
            :data-artist="artist.id" :data-count="artist.count" @click="emit('select', artist)">
            <span class="artist-name"><small>{{ String(index + 1).padStart(2, '0') }}</small><span>{{ artist.name }}<em>{{ artist.type === 'MusicalGroup' ? '组合' : '艺人' }} · {{ artist.notableCount }} 部相关作品有登榜标记</em></span></span>
            <svg class="artist-years" viewBox="0 0 150 24" aria-hidden="true"><path d="M5,12H145" />
              <circle v-for="[year, count] in artist.years" :key="year" :cx="yearX(year)" cy="12" :r="1.5 + Math.sqrt(count)" /></svg>
            <span class="artist-count"><strong>{{ artist.count }}</strong><small>/ {{ artist.workCount }} 部</small></span>
          </button>
          <p v-if="!matching.length" class="artist-state">当前范围没有匹配的表演者。</p>
          <button v-if="matching.length > limit" type="button" class="atlas-inline artist-more" @click="limit += 10">再看 10 位 ↓</button>
        </div>
        <aside class="artist-detail" aria-live="polite">
          <template v-if="selected">
            <span class="artist-overline">作品与署名证据</span><h3>{{ selected.name }}</h3>
            <p>{{ selected.count }} 条引用关联 {{ selected.workCount }} 部表演作品，其中 {{ selected.notableCount }} 部有登榜标记。</p>
            <button class="atlas-inline" type="button" @click="emit('inspect')">核对全部引用 →</button>
            <article v-for="work in selected.works" :key="work.id" class="artist-work">
              <h4>{{ work.name }}</h4><p>{{ work.year }} · {{ work.genre }}<span v-if="work.notable"> · {{ work.chartYear ? work.chartYear + ' 年登榜' : '有登榜标记，年份未知' }}</span></p>
              <details><summary>{{ work.references.length }} 条作品引用与表演署名</summary>
                <p v-for="event in work.references" :key="event.id"><b>{{ event.sourceName }}</b> → {{ work.name }}<br>{{ EDGE_LABELS[event.type] }} · <code>{{ event.id }}</code></p>
                <p>表演署名：<code v-for="id in work.creditIds" :key="id">{{ id }} </code></p>
              </details>
            </article>
          </template>
          <template v-else><span class="artist-overline">从流派到作品，再到表演者</span><h3>谁接住了这些回响？</h3><p>选一位艺人，核对其作品引用了哪些 {{ focus }} 作品，以及对应的表演署名。</p></template>
          <p class="artist-method">引用数按每位表演者去重，共同表演者分别列出，不能跨艺人相加。登榜标记来自这些受影响作品，不表示该艺人排名第一，也不代表私人合作。</p>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.genre-artists { color:var(--score-ink);min-width:0; }
.artist-toolbar { display:flex;flex-wrap:wrap;align-items:center;gap:14px 24px;padding:5px 0 22px;border-bottom:1px solid var(--score-rule);font-size:12px; }
.artist-search { display:flex;align-items:center;gap:10px; }.artist-search input { min-width:0;max-width:100%;border:0;border-bottom:1px solid var(--score-rule);padding:8px;background:transparent;color:inherit;font:inherit; }
.artist-notable { display:flex;align-items:center;gap:6px; }.artist-notable input { accent-color:var(--score-blue); }
.artist-toolbar>span { margin-left:auto;color:var(--score-soft); }
.artist-layout { display:grid;grid-template-columns:minmax(0,1.45fr) minmax(240px,1fr);gap:clamp(24px,4vw,56px);padding-top:24px; }
.artist-columns,.artist-row { display:grid;grid-template-columns:minmax(150px,1.5fr) minmax(70px,1fr) 74px;gap:15px;align-items:center; }
.artist-columns { font-size:11px;color:var(--score-soft);padding:0 12px 12px; }.artist-columns span:last-child { text-align:right; }
.artist-row { width:100%;background:none;border:0;border-top:1px solid var(--score-rule);padding:13px 12px;text-align:left;color:inherit;cursor:pointer;transition:background 180ms,color 180ms; }
.artist-row:hover,.artist-row.is-selected { background:var(--score-raised);color:var(--score-blue); }.artist-row:focus-visible { outline:2px solid var(--score-blue);outline-offset:-2px; }
.artist-name { display:flex;align-items:baseline;gap:11px;font:17px Georgia,serif; }.artist-name>small { font:10px system-ui,sans-serif;color:var(--score-muted); }
.artist-name em { display:block;font:10px/1.7 system-ui,sans-serif;font-style:normal;color:var(--score-soft);margin-top:5px; }
.artist-years { width:100%;overflow:visible; }.artist-years path { stroke:var(--score-rule);fill:none;stroke-width:.7; }.artist-years circle { fill:var(--score-blue);stroke:var(--score-panel);stroke-width:.5; }
.artist-count { display:flex;align-items:baseline;justify-content:end;gap:5px;white-space:nowrap; }.artist-count strong { font:25px Georgia,serif; }.artist-count small { font-size:11px;color:var(--score-soft); }
.artist-more { margin:18px 12px 0;font-size:12px; }.artist-detail { border-left:1px solid var(--score-rule);padding-left:25px; }.artist-overline { font-size:11px;letter-spacing:.05em;color:var(--score-soft); }
.artist-detail h3 { font:500 clamp(23px,2.8vw,35px)/1.25 var(--atlas-display);margin:15px 0; }.artist-detail p { font-size:12px;line-height:1.8;color:var(--score-soft); }.artist-detail>.atlas-inline { font-size:12px; }
.artist-work { margin-top:22px;border-top:1px solid var(--score-rule);padding-top:14px; }.artist-work h4 { font:17px Georgia,serif;margin:0; }.artist-work p { margin:8px 0; }.artist-work details { font-size:12px; }.artist-work summary { cursor:pointer;color:var(--score-blue); }.artist-work code { font-size:10px;overflow-wrap:anywhere; }
.artist-method { margin-top:27px;padding-top:15px;border-top:1px solid var(--score-rule);font-size:11px!important; }.artist-state { padding:28px 0;font-size:13px; }.artist-state button { margin-left:12px; }
@media(max-width:900px) { .artist-layout { grid-template-columns:minmax(0,1fr); }.artist-detail { padding:22px 0 0;border-left:0;border-top:1px solid var(--score-rule); } }
@media(max-width:560px) { .artist-columns,.artist-row { grid-template-columns:minmax(120px,1fr) 66px;gap:8px; }.artist-years,.artist-columns>span:nth-child(2) { display:none; }.artist-name { font-size:15px;gap:7px; }.artist-row { padding-inline:5px; }.artist-toolbar>span { margin-left:0; } }
@media(prefers-reduced-motion:reduce) { .artist-row { transition:none; } }
</style>
