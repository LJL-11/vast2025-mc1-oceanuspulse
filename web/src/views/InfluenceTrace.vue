<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { dataService, friendlyDataError } from '../lib/dataService'
import JournalPager from '../components/JournalPager.vue'
const sailor=ref(null), graph=ref(null), error=ref(''), selectedWork=ref(null), selectedPerson=ref(17256), direction=ref('upstream')
const loomHeights=ref({upstream:900,downstream:900})
const loomHeight=computed(()=>loomHeights.value[direction.value])
const expandedWork=ref(null)
// Editorial descriptions written from the titles, rather than audio-analysis claims.
const workIntroductions={
 "The Kelp Forest Canticles": "潮水漫过海藻林，光在叶片间缓缓游动。这里的每一声回响，都像一封从海底寄来的旧信。",
 "Luminescent Tides": "夜色落下，潮水却亮了起来。那些未曾说出口的话，随着一线微光，慢慢抵达岸边。",
 "Shoreline Sonnets": "沿着海岸走，脚印被浪花一行行收走。留下的句子不长，刚好装下一次回望。",
 "Tidal Pop Waves": "浪头接连涌来，把平静的海面推向远方。短暂的晴光里，连等待也有了轻快的模样。",
 "High Tide Heartbeat": "涨潮的时候，岸边的一切都靠近了。心跳藏在水声里，像有人隔着人海，轻轻应了一声。",
 "Electric Eel Love": "水下忽然掠过一道电光，爱意也在那一瞬被照亮。来不及命名，余温已经留在掌心。",
 "Sun-Drenched Daydream": "午后的阳光铺满窗台，时间像被海风吹慢了。一场白日梦从这里出发，不急着醒来。",
 "Chord of the Deep": "深处并非寂静，只是回声要走很远。那些沉下去的念头，终会在某个时刻重新相逢。",
 "Tides of Echos": "一阵潮声退去，另一阵从记忆里涌来。旧日的回音没有散，只是换了一片海停留。",
 "Salty Dreams": "梦里仍有海盐的气息，和一扇没有关紧的窗。醒来之后，远方仿佛离枕边近了一点。",
 "Heart of the Habitat": "把目光放低，会看见石缝里的新绿。栖居于此的细小生命，让一处地方有了心跳。",
 "Reef Rhythm": "水流绕过礁石，留下深浅不一的纹路。一次停顿、一次回旋，海便有了自己的步伐。",
 "Driftwood Lullaby": "漂木在岸边歇下，结束了漫长的颠簸。晚风轻轻经过，像替远行的人掖好被角。",
 "Seashell Serenade": "把贝壳贴近耳边，远去的海又回来了。它不解释离别，只把那晚的月色留给你。",
 "Neon Heartbeat": "霓虹倒映在雨后的街面，脚步与灯影擦肩。城市很亮，心里却仍为一个人留着窗。",
 "Hidden Depths": "水面之下，还有未被光触及的地方。往深处走一点，也许会遇见一直沉默的自己。",
 "Tidesworn Ballads": "有些约定交给潮水保管，有些名字留在风里。多年以后重返岸边，仍能认出它们。",
 "Submerged Sonatas": "那些沉入水中的片段，没有真正消失。等喧嚣退去，它们便从记忆的深处一一浮起。",
 "The Current & The Chord": "水流带走一片叶，也带来另一处的消息。两条看似无关的路，在这里有了短暂的交汇。",
 "Saltwater Hymn": "海水漫过旧伤，也漫过长久的沉默。站在岸边的人，把感谢和思念一起交给了风。",
 "Ballads for the End of Time": "如果时间终有尽头，愿最后的片刻足够安静。让人来得及握紧一只手，说完一句话。",
 "Melancholy Circuitry": "灯光沿着线路亮起，又在夜深时逐一熄灭。再精密的回路，也藏得下一点无处投递的想念。",
 "Drifting Between the Stars and the Sea": "抬头是星光，低头是海，船停在两片辽阔之间。这一夜不必寻找终点，漂流本身就已足够。",
 "Coral Beats": "珊瑚在缓慢的时光里生长，把细小的变化积成颜色。海底的热闹，往往要安静下来才能看见。",
 "Moon Over the Tide": "月亮把一条银色的小路铺在潮水上。岸上的人看了很久，仿佛沿着它就能走回从前。",
 "Into the Current": "松开岸边的绳结，把迟疑留在身后。前面的水域尚未命名，流向却已经给出回答。",
 "Barnacle Heart": "有些牵挂像藤壶，牢牢附着在心上。无论经过多少片海，总会带着一点故乡出发。",
 "Artificial Sunsets": "城市用灯光留住黄昏，窗外的天却早已暗了。那片人造的晚霞里，仍有人认真等待明天。",
 "Tides & Ballads": "潮来时听故事，潮退时想起讲故事的人。那些平常的日子，被一遍遍讲述，便有了分量。",
 "Fog & Fiddle": "雾遮住远处的路，也让眼前的一切靠近。有人从朦胧中走来，带着一段熟悉的旧事。",
 "The Fisherman's Prayer": "出海前，他望了一眼尚未亮灯的家。所求不过平安归来，和晚饭时桌边完整的人影。",
 "Ballads for the Low Tide": "退潮后，沙滩露出平日看不见的痕迹。有些故事也要等心事安静，才肯慢慢显出轮廓。",
 "Electric Reverie": "电光在夜里短暂停留，照见一场尚未醒来的梦。醒与睡的缝隙中，远方显得格外清楚。",
 "Oceanbound": "行李很轻，海却很远。告别码头的那一刻，所有未说完的话，都有了新的去处。",
 "Stormsong": "风暴压低海面，雨把远方揉成一片。等天亮时，总有一盏灯还留在原来的地方。",
 "Echoes of the Deep": "深海把声音留得很久，像记忆留住某个名字。一声呼唤落下，许多年以后，仍有回音。",
 "Salt in My Veins": "走得再远，风里的盐味仍会让人停下脚步。原来故乡不只在地图上，也在每一次呼吸里。",
 "The Last Mariner": "最后一位水手收起帆，望向渐暗的海平线。一生的航程没有说完，灯塔已经替他接住余下的夜。"
}
function toggleWork(id){selectedWork.value=id;expandedWork.value=expandedWork.value===id?null:id}
// Optional local assets are deliberately absent from the public repository.
const localReviewAssets = import.meta.env.VITE_MODULE1_REVIEW_ASSETS === '1'
const base=import.meta.env.BASE_URL+'module1-review/'
const roleNames={LyricistOf:'作词',ComposerOf:'作曲',PerformerOf:'表演',ProducerOf:'制作'}
const typeNames={InStyleOf:'风格借鉴',CoverOf:'翻唱',DirectlySamples:'采样',InterpolatesFrom:'片段引用',LyricalReferenceTo:'歌词引用'}
const nodeMap=computed(()=>new Map((graph.value?.nodes||[]).map(n=>[n.id,n])))
const name=id=>nodeMap.value.get(id)?.display_name||nodeMap.value.get(id)?.name||String(id)
const works=computed(()=>(sailor.value?.works||[]).map(w=>({...nodeMap.value.get(w.id),...w})).sort((a,b)=>(a.release_year??9999)-(b.release_year??9999)||a.id-b.id))
const work=computed(()=>works.value.find(w=>w.id===selectedWork.value))
// Coverflow geometry adapted from Eduardo Calvo's SmoothUI Coverflow Carousel.
const editions = [
 { title:'First Landfall', years:'2024—2026', end:2026, palette:'#536f68', cover:'fleetwood-mac-tango.jpg' },
 { title:'Rising Tide', years:'2028—2029', end:2029, palette:'#ab6844', cover:'tame-impala-currents.jpg' },
 { title:'Beneath the Surface', years:'2030—2031', end:2031, palette:'#2e5475', cover:'radiohead-kid-a.jpg' },
 { title:'Night Passage', years:'2032—2034', end:2034, palette:'#67537c', cover:'joy-division-unknown-pleasures.jpg' },
 { title:'After the Ebb', years:'2035—2037', end:2037, palette:'#986b52', cover:'eagles-hotel-california.jpg' },
 { title:'Open Water', years:'2038—2040', end:Infinity, palette:'#3f6972', cover:'pink-floyd-the-wall.jpg' },
]
const collections = computed(() => editions.map((edition, index) => ({
 ...edition,
 entries: works.value.filter(entry => {
  const year = entry.release_year ?? Infinity
  return (index === 0 || year > editions[index - 1].end) && year <= edition.end
 }),
})))
const activeEdition = computed(() => Math.max(0, collections.value.findIndex(group => group.entries.some(entry => entry.id === selectedWork.value))))
const currentEdition = computed(() => collections.value[activeEdition.value])
function selectEdition(index) {
 const entry = collections.value[index]?.entries[0]
 if (entry && index !== activeEdition.value) selectedWork.value = entry.id
}
function coverStyle(index) {
 const offset = index - activeEdition.value
 const distance = Math.abs(offset)
 return {
  transform: `translate3d(calc(var(--rack-spacing) * ${offset}), 0, ${-distance * 120}px) rotateY(${-Math.sign(offset) * 44}deg) scale(${1 - distance * .13})`,
  zIndex: 4 - distance,
 }
}
let swipeStart = null
let suppressCoverClick = false
function beginSwipe(event) {
 if (event.isPrimary && event.button === 0) {
  swipeStart = event.clientX
  suppressCoverClick = false
 }
}
function endSwipe(event) {
 if (swipeStart === null) return
 const distance = event.clientX - swipeStart
 swipeStart = null
 if (Math.abs(distance) < 45) return
 suppressCoverClick = true
 selectEdition(activeEdition.value - Math.sign(distance))
}
function clickCover(index, event) {
 if (event.detail === 0 || !suppressCoverClick) selectEdition(index)
 suppressCoverClick = false
}

const collaborators=computed(()=>sailor.value?.collaborators||[])
const person=computed(()=>collaborators.value.find(p=>p.id===selectedPerson.value))
const sharedWorks=computed(()=>works.value.filter(w=>person.value?.work_ids.includes(w.id)))
const influenceRows = computed(() => direction.value === 'upstream'
 ? (sailor.value?.inspiration_sources || []).map(row => row.name || name(row.id))
 : (sailor.value?.directly_influenced || []).map(row => row.name || name(row.id)))
const workEvents=computed(()=>(sailor.value?.events||[]).filter(e=>e.source===selectedWork.value||e.target===selectedWork.value))
const credits=computed(()=>(graph.value?.links||[]).filter(e=>e.target===selectedWork.value&&roleNames[e.type]))
function receive(e){
 if(e.origin!==location.origin||!Array.from(document.querySelectorAll('.trace-review iframe')).some(f=>f.contentWindow===e.source))return
 if(e.data?.kind==='loom-height'&&Number.isFinite(e.data.height)){
  const frame=Array.from(document.querySelectorAll('.trace-loom')).find(f=>f.contentWindow===e.source)
  if(frame?.dataset.direction)loomHeights.value[frame.dataset.direction]=Math.max(240,Math.min(2000,e.data.height))
 }
 if(e.data?.kind==='collab-ready' && e.source===document.querySelector('.trace-collab-frame')?.contentWindow){
  e.source.postMessage({kind:'select-collaborator',id:selectedPerson.value},location.origin)
 }
 if(e.data?.kind==='work')selectedWork.value=e.data.id
 if(e.data?.kind==='collaborator'&&collaborators.value.some(p=>p.id===e.data.id))selectedPerson.value=e.data.id
}
watch(selectedPerson,id=>{expandedWork.value=null;document.querySelector('.trace-collab-frame')?.contentWindow?.postMessage({kind:'select-collaborator',id},location.origin)})
function setDirection(d){direction.value=d}
onMounted(async()=>{window.addEventListener('message',receive);try{[sailor.value,graph.value]=await Promise.all([dataService.sailor(),dataService.sailorEgo()]);selectedWork.value=sailor.value.works[0]?.id}catch(e){error.value=friendlyDataError(e)}})
onBeforeUnmount(()=>window.removeEventListener('message',receive))
</script>
<template>
 <div class="trace-review">
  <header class="trace-intro journal-opening"><span class="journal-folio" aria-label="第 01 章">01</span><div class="journal-lede"><h1>Sailor Shift <span>作品与回声</span></h1></div></header>
  <p v-if="error" class="trace-status trace-status-error" role="alert">{{error}}</p><p v-else-if="!sailor" class="trace-status" role="status">正在读取 Sailor Shift 的作品档案…</p>
  <template v-else>
   <section id="trace-map" class="trace-chapter">
    <div class="trace-section-head"><div><h2>作品目录</h2></div></div>
    <div v-if="localReviewAssets" class="trace-map-stage"><iframe :src="base+'musicmap/index.html'" title="Musicmap 作品地图：滚轮缩放，拖动画布，点选作品" /></div>
    <section class="trace-record-rack" aria-label="作品选集">
     <div class="trace-record-stage" @pointerdown="beginSwipe" @pointerup="endSwipe" @pointerleave="swipeStart = null" @pointercancel="swipeStart = null"
       @keydown.left.prevent="selectEdition(activeEdition - 1)" @keydown.right.prevent="selectEdition(activeEdition + 1)">
      <button v-for="(edition, index) in collections" :key="edition.title" type="button" class="trace-record-cover"
        :class="{'is-centered': index === activeEdition}" :style="{...coverStyle(index), '--cover-ink': edition.palette}"
        :hidden="Math.abs(index - activeEdition) > 2" :aria-pressed="index === activeEdition"
        :aria-label="edition.title + '，' + edition.years" @click="clickCover(index, $event)">
       <img v-if="localReviewAssets" class="trace-record-image" :src="base + 'record-covers/' + edition.cover" alt="" width="600" height="600" draggable="false">
       <span class="trace-record-art" aria-hidden="true"></span>
       <span class="trace-record-title">{{ edition.title }}<small>{{ edition.years }}</small></span>
      </button>
     </div>
     <div class="trace-record-nav">
      <button type="button" aria-label="上一张选集" :disabled="activeEdition === 0" @click="selectEdition(activeEdition - 1)">←</button>
      <p aria-live="polite">{{ currentEdition.title }} <small>{{ activeEdition + 1 }} / {{ collections.length }}</small></p>
      <button type="button" aria-label="下一张选集" :disabled="activeEdition === collections.length - 1" @click="selectEdition(activeEdition + 1)">→</button>
     </div>
     <ul class="trace-record-tracks" aria-label="选集作品">
      <li v-for="entry in currentEdition.entries" :key="entry.id">
       <button type="button" :aria-current="entry.id === selectedWork ? 'true' : undefined" @click="selectedWork = entry.id">
        <span>{{ entry.name }}</span><small>{{ entry.genre || 'Unknown' }}</small>
       </button>
      </li>
     </ul>
    </section>
    <div class="trace-evidence-layout">
     <div class="trace-work-dossier">
      <h4 id="trace-work-label">作品档案</h4>
      <template v-if="work"><h3>{{work.name}}</h3><p>{{work.release_year??'暂无'}} · {{work.type==='Album'?'专辑':'歌曲'}} · {{work.genre||'暂无'}}</p><p>Sailor Shift：{{work.roles.map(r=>roleNames[r]||r).join(' / ')}}</p></template></div>
     <div><h4>共同创作</h4><p v-if="!credits.length" class="trace-empty">暂无</p><div class="trace-credit-list"><span v-for="c in credits" :key="c.id">{{name(c.source)}} <small>{{roleNames[c.type]}}</small></span></div></div>
     <div><h4>音乐引用</h4><p v-if="!workEvents.length">暂无</p><div class="trace-citation" v-for="e in workEvents" :key="e.id"><p>{{name(e.source)}} → {{name(e.target)}}<small class="trace-block">{{typeNames[e.type]||'暂无'}} · {{e.year??'暂无'}}</small></p></div></div>
    </div>
   </section>
   <section class="trace-chapter trace-influence-chapter">
    <div class="trace-loom-panel">
     <div class="trace-section-head trace-loom-toolbar"><div><h2>音乐影响</h2></div><div class="trace-tabs" :class="{'is-downstream':direction==='downstream'}" role="group" aria-label="音乐影响方向"><span class="trace-tab-indicator" aria-hidden="true"></span><button :aria-pressed="direction==='upstream'" @click="setDirection('upstream')">影响来源</button><button :aria-pressed="direction==='downstream'" @click="setDirection('downstream')">受其影响</button></div></div>
     <div v-if="localReviewAssets" class="trace-loom-stage" :style="{height:loomHeight+'px'}"><iframe v-for="side in ['upstream','downstream']" :key="side" class="trace-loom" :class="{'is-active':direction===side}" :data-direction="side" :aria-hidden="direction!==side" :inert="direction!==side" :tabindex="direction===side?0:-1" scrolling="no" :src="base+'loom/index.html?direction='+side" :title="side==='upstream'?'音乐影响：影响来源':'音乐影响：受其影响'" /></div>
     <div v-else class="trace-public-influence">
      <p v-if="!influenceRows.length">暂无</p>
      <ul v-else><li v-for="(label, index) in influenceRows" :key="index">{{ label }}</li></ul>
     </div>
    </div>
   </section>
   <section class="trace-chapter">
    <div class="trace-section-head"><div><h2>合作关系</h2></div></div>
    <div class="trace-collab-layout"><iframe v-if="localReviewAssets" class="trace-collab-frame" :src="base+'collaboration/index.html?person=Sailor_Shift'" title="合作关系图，沿用 Linked Jazz 节点聚焦、布局与缩放"/><div v-else class="trace-public-people" aria-label="共同创作者">
      <button v-for="entry in collaborators" :key="entry.id" type="button" :aria-pressed="entry.id === selectedPerson" @click="selectedPerson = entry.id">{{ entry.name }}</button>
     </div><aside><template v-if="person"><p class="trace-aside-label">合作档案</p><h3>{{person.name}}</h3><p>{{person.shared_work_count}} 部共同作品 · {{person.first_year??'暂无'}}—{{person.last_year??'暂无'}}</p><p v-if="!sharedWorks.length" class="trace-empty">暂无</p><div class="trace-shared-work" v-for="w in sharedWorks" :key="w.id"><button class="trace-work-link" :class="{'is-expanded':expandedWork===w.id}" :aria-expanded="expandedWork===w.id" :aria-controls="'trace-work-intro-'+w.id" @click="toggleWork(w.id)"><span>{{w.name}}</span><small>{{w.release_year??'暂无'}}</small><svg class="trace-work-chevron" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg></button><div class="trace-work-intro" :class="{'is-open':expandedWork===w.id}" :id="'trace-work-intro-'+w.id" :inert="expandedWork!==w.id"><div><p>{{workIntroductions[w.name]||'暂无'}}</p></div></div></div></template></aside></div>
   </section>
   <JournalPager module="influence" />
  </template>
 </div>
</template>
<style scoped>

.trace-review{--trace-ink:#183a4a;--trace-muted:#536b80;--trace-line:#d6dedf;--trace-soft:#edf3f4;--trace-accent:#914633;color:var(--trace-ink);max-width:1432px;margin:0 auto;min-width:0}
.trace-review p{line-height:1.75}.trace-review h2,.trace-review h3{font-family:Georgia,'Songti SC','SimSun',serif;font-weight:400;text-wrap:balance}.trace-review h2{font-family:"STZhongsong","Songti SC","SimSun",serif;font-weight:600;font-size:30px;letter-spacing:.06em;line-height:1.25;margin:0 0 12px}.trace-review h3{font-size:25px;line-height:1.35;margin:16px 0 12px}.trace-review h4,.trace-work-dossier>label{display:block;font-size:14px;font-weight:600;margin:0 0 18px}.trace-review small{font-size:12px;font-weight:400;color:var(--trace-muted)}
.trace-intro{display:flex;justify-content:space-between;align-items:flex-end;gap:48px;padding:16px 0 38px}.trace-intro h1{font:clamp(32px,3.8vw,52px)/1.2 Georgia,'Songti SC',serif;margin:0 0 16px;letter-spacing:-.025em}.trace-intro h1 span{font-size:.62em;display:inline-block;margin-left:20px;letter-spacing:0}.trace-intro p{margin:0;color:var(--trace-muted)}
.trace-chapter{padding:32px 0 56px;border-top:1px solid var(--trace-line);scroll-margin-top:24px}.trace-section-head{display:flex;justify-content:space-between;align-items:center;gap:32px;margin-bottom:26px}.trace-section-head>div:first-child{min-width:0}.trace-section-head h2{margin-bottom:0}.trace-review button,.trace-review select{font:inherit;font-size:13px;line-height:1.5;min-height:42px;color:var(--trace-ink);background:#fff;border:1px solid #b8c8cf;padding:10px 15px;border-radius:5px;cursor:pointer;max-width:100%}.trace-section-head>button{flex-shrink:0}.trace-review button:hover{background:var(--trace-soft);border-color:#7c99a6}.trace-review button:focus-visible,.trace-review select:focus-visible,.trace-review summary:focus-visible{outline:2px solid var(--trace-accent);outline-offset:4px}.trace-review button:active{background:#dce8eb}
.trace-map-stage{height:760px;background:#050606;overflow:hidden;border-radius:5px}.trace-review iframe{width:100%;height:100%;border:0;display:block}.trace-evidence-layout{display:grid;grid-template-columns:1.05fr .9fr 1.15fr;gap:32px;padding:20px clamp(14px,3vw,32px);border:1px solid var(--trace-line);border-top:0;background:#f9f8f3}.trace-evidence-layout>div{min-width:0}.trace-evidence-layout>div+div{padding-left:28px;border-left:1px solid var(--trace-line)}.trace-evidence-layout select{width:100%;display:block}.trace-evidence-layout h3{font-size:clamp(23px,2.2vw,32px);margin:8px 0 12px}.trace-evidence-layout p{font-size:14px;margin:10px 0;overflow-wrap:anywhere}.trace-credit-list{display:flex;flex-direction:column;gap:10px;font-size:13px}.trace-credit-list>span{display:flex;justify-content:space-between;align-items:baseline;gap:16px}.trace-credit-list small{flex-shrink:0}.trace-block{display:block;margin-top:5px}.trace-citation+.trace-citation{margin-top:18px;padding-top:12px;border-top:1px solid var(--trace-line)}.trace-empty{font-size:13px;color:var(--trace-muted)}
.trace-loom{background:#fdfcf8}.trace-review summary{cursor:pointer;width:fit-content;text-underline-offset:4px}.trace-review summary:hover{color:var(--trace-ink)}
.trace-collab-layout{display:grid;grid-template-columns:minmax(0,3fr) minmax(290px,1fr);background:#e6edee;border:1px solid #d0dadb;border-radius:5px;overflow:hidden}.trace-collab-layout iframe{height:clamp(580px,57vw,760px);min-width:0}.trace-collab-layout aside{min-width:0;overflow-wrap:anywhere;padding:28px clamp(18px,2vw,30px);background:#f1eee5;border-left:1px solid #d0dadb}.trace-collab-layout aside p{font-size:13px}.trace-collab-layout .trace-aside-label{font-size:12px;margin:0;color:var(--trace-muted)}.trace-collab-layout aside h3{margin-top:10px;color:#943f2c}.trace-work-link{display:flex;width:100%;justify-content:space-between;align-items:baseline;gap:16px;text-align:left;border-width:0 0 1px!important;border-color:var(--trace-line)!important;border-radius:0!important;padding:14px 8px!important;background:transparent!important}.trace-work-link:hover,.trace-work-link.is-expanded{background:var(--trace-soft)!important}.trace-work-link small{flex-shrink:0;font-variant-numeric:tabular-nums}
.trace-status{padding:32px 0;border-top:1px solid var(--trace-line);color:var(--trace-muted)}.trace-status-error{color:var(--trace-accent)}.trace-review ::selection{background:#d9e6eb;color:#183a4a}
@media(min-width:1600px){.trace-map-stage{height:840px}}
@media(max-width:1050px){.trace-intro{gap:24px}.trace-evidence-layout{gap:22px}.trace-evidence-layout>div+div{padding-left:20px}.trace-section-head{gap:20px}.trace-collab-layout{grid-template-columns:minmax(0,1fr) 260px}}
@media(max-width:800px){.trace-intro{align-items:flex-start;flex-direction:column;padding:12px 0 28px;gap:20px}.trace-intro h1 span{display:block;margin:10px 0 0}.trace-chapter{padding:26px 0 38px}.trace-section-head{align-items:flex-start;flex-direction:column;gap:18px;margin-bottom:20px}.trace-review h2{font-size:25px}.trace-map-stage{height:620px}.trace-evidence-layout{grid-template-columns:1fr;gap:26px}.trace-evidence-layout>div+div{border-left:0;padding-left:0;border-top:1px solid var(--trace-line);padding-top:22px}.trace-collab-layout{grid-template-columns:1fr}.trace-collab-layout aside{border-left:0;border-top:1px solid var(--trace-line);padding:24px 20px}.trace-tabs{max-width:100%}.trace-review button,.trace-review select{min-height:44px}}

/* Hide shared method disclosure only while this module is mounted. */
:global(.op-app:has(.trace-review) .atlas-footer>details){display:none}

/* Sliding indicator adapted from SmoothUI Tabs (pill variant), public registry source.
   https://smoothui.dev/r/tabs.json — React measurement is unnecessary for two equal Vue segments. */
.trace-tabs{position:relative;isolation:isolate;display:grid;grid-template-columns:1fr 1fr;flex-shrink:0;gap:4px;padding:5px;background:#e7edef;border:1px solid #d3dfe3;border-radius:999px}
.trace-tab-indicator{position:absolute;z-index:-1;left:5px;top:5px;bottom:5px;width:calc((100% - 14px)/2);background:#183a4a;border-radius:999px;transform:translateX(0);transition:transform 280ms cubic-bezier(.25,1,.5,1)}
.trace-tabs.is-downstream .trace-tab-indicator{transform:translateX(calc(100% + 4px))}
.trace-tabs button{min-width:110px;padding:10px 20px;border:0;border-radius:999px;background:transparent;color:#536b80;font-family:inherit;font-weight:500;transition:color 140ms ease;user-select:none;touch-action:manipulation}
.trace-tabs button:hover,.trace-tabs button:active{background:transparent;color:#183a4a}
.trace-tabs button[aria-pressed=true]{color:#fff}
.trace-section-head h2{position:relative;width:fit-content;padding-bottom:14px;border-bottom:1px solid #bdcbd0}
.trace-section-head h2::after{content:"";position:absolute;bottom:-1px;left:0;width:44%;height:2px;background:#183a4a}
.trace-work-link{align-items:center;gap:10px}
.trace-work-link>span{flex:1}.trace-work-chevron{flex:none;transition:transform 180ms cubic-bezier(.22,1,.36,1)}
.trace-work-link.is-expanded .trace-work-chevron{transform:rotate(180deg)}
.trace-work-intro{display:grid;grid-template-rows:0fr;opacity:0;transition:grid-template-rows 220ms cubic-bezier(.22,1,.36,1),opacity 140ms ease}
.trace-work-intro.is-open{grid-template-rows:1fr;opacity:1}.trace-work-intro>div{min-height:0;overflow:hidden}
.trace-collab-layout .trace-work-intro p{margin:0;padding:18px 14px 22px;background:#eeeade;color:#394641;font-size:14px;line-height:1.9}
@media(prefers-reduced-motion:reduce){.trace-tab-indicator,.trace-work-intro,.trace-work-chevron{transition:none}}

.trace-intro.journal-opening{display:grid;grid-template-columns:clamp(48px,6vw,88px) minmax(0,1fr);align-items:start;gap:14px clamp(15px,3.3vw,50px);margin:4px auto 24px;padding:clamp(17px,3vw,38px) 0 0}
.trace-intro .journal-folio{padding-top:6px}
/* Keep both diagrams mounted: the selection leads, the corresponding view follows. */
.trace-loom-panel{border:1px solid #d5dcda;border-radius:5px;overflow:hidden;background:#f2f1e9}
.trace-loom-panel .trace-loom-toolbar{margin:0;padding:14px clamp(16px,3vw,30px);border-bottom:1px solid #d5dcda;background:#f8f7f1}
.trace-loom-toolbar h2{padding-bottom:8px}
.trace-loom-toolbar .trace-tabs button{min-height:36px;padding:6px 14px}
@media(max-width:800px){.trace-loom-panel .trace-loom-toolbar{flex-direction:row;flex-wrap:wrap;align-items:center;gap:12px}}
.trace-loom-stage{position:relative;overflow:hidden;background:#f2f1e9;isolation:isolate;transition:height 260ms cubic-bezier(.25,1,.5,1)}
.trace-loom-stage .trace-loom{position:absolute;inset:0;opacity:0;pointer-events:none;visibility:hidden;transform:translateX(-16px);transition:opacity 130ms ease-out,transform 230ms cubic-bezier(.25,1,.5,1),visibility 0s 230ms}
.trace-loom-stage .trace-loom[data-direction=downstream]{transform:translateX(16px)}
.trace-loom-stage .trace-loom.is-active{opacity:1;transform:translateX(0);pointer-events:auto;visibility:visible;transition:opacity 200ms ease-out 55ms,transform 240ms cubic-bezier(.25,1,.5,1) 35ms,visibility 0s}
.trace-tabs button:active{transform:scale(.98)}
@media(max-width:800px){.trace-intro.journal-opening{grid-template-columns:42px minmax(0,1fr);gap:13px}.trace-intro .journal-folio{padding-top:3px}}
@media(prefers-reduced-motion:reduce){.trace-loom-stage{transition:none}.trace-loom-stage .trace-loom,.trace-loom-stage .trace-loom.is-active{transform:none;transition:opacity 80ms linear,visibility 0s}.trace-tabs button:active{transform:none}}

.trace-record-rack{margin-top:22px;padding:12px clamp(10px,4vw,54px);border:1px solid var(--trace-line);background:#f3f2ed}
.trace-record-stage{--rack-spacing:clamp(68px,13vw,174px);display:grid;place-items:center;perspective:1200px;min-height:clamp(195px,24vw,282px);overflow:hidden;touch-action:pan-y;user-select:none}
.trace-record-stage .trace-record-cover{grid-area:1/1;position:relative;display:grid;align-content:end;isolation:isolate;width:clamp(132px,22vw,230px);aspect-ratio:1;padding:16px;text-align:left;color:#fff7df;background:var(--cover-ink);border:1px solid #ffffff50;border-radius:3px;box-shadow:0 12px 24px #17272b36;overflow:hidden;transition:transform 420ms cubic-bezier(.22,.82,.28,1)}
.trace-record-stage .trace-record-cover[hidden]{display:none}
.trace-record-stage .trace-record-cover:hover{background:var(--cover-ink);border-color:#fff7df}
 .trace-record-image,.trace-record-art{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.trace-record-image{z-index:-2;object-fit:cover}
.trace-record-art{z-index:-1;background:linear-gradient(0deg,#0b141aee,transparent 57%)}
.trace-record-title{font:600 clamp(18px,2.5vw,30px)/1.2 Georgia,'Songti SC','SimSun',serif}.trace-record-title small{display:block;margin-top:7px;color:inherit;font:12px Georgia,serif}
.trace-record-nav{display:flex;align-items:center;justify-content:center;gap:18px;margin:0 0 20px}.trace-record-nav p{margin:0;min-width:130px;text-align:center}.trace-record-nav small{display:block}.trace-record-nav button:disabled{opacity:.35;cursor:default}
.trace-record-tracks{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,265px),1fr));gap:0 24px;list-style:none;padding:0;margin:0}
.trace-record-tracks button{width:100%;display:flex;justify-content:space-between;align-items:baseline;gap:12px;text-align:left;border:0;border-top:1px solid var(--trace-line);border-radius:0;background:transparent;font-size:14px}
.trace-record-tracks button[aria-current=true]{background:#dfe9e9}.trace-record-tracks small{white-space:nowrap}
@media(prefers-reduced-motion:reduce){.trace-record-stage .trace-record-cover{transition:none}}
.trace-intro .journal-folio{font:30px/1 Georgia,serif;color:#245e7d}
.trace-public-influence,.trace-public-people{padding:24px}
.trace-public-influence ul{columns:2;column-width:210px;margin:0;padding-left:20px;line-height:1.85}
.trace-public-people{display:flex;flex-wrap:wrap;align-content:start;gap:8px}
.trace-public-people button[aria-pressed=true]{background:#dfe9e9;border-color:#73909a}
.trace-review :deep(.journal-pager){display:flex;justify-content:space-between;gap:18px;border-top:1px solid var(--trace-line);padding:18px 0}
.trace-review :deep(.journal-pager a){display:flex;align-items:center;gap:8px}
.trace-review :deep(.journal-pager small){display:block}
</style>
