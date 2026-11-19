import { layoutCitations } from './genreCitationLayout'

self.onmessage = ({ data: { samples, extent, compact } }) => {
  self.postMessage(layoutCitations(samples, extent, compact))
}
