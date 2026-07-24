import { GIFEncoder, quantize, applyPalette } from 'gifenc'
import { parseGIF, decompressFrames, type ParsedFrame } from 'gifuct-js'

export function isGifPath(path?: string | null): boolean {
  return !!path && /\.gif(\?.*)?$/i.test(path)
}

interface GifOptions {
  // Cap output width so the encoded GIF stays a reasonable size/speed.
  maxWidth?: number
  // Cap the number of frames encoded (delays are merged when downsampling).
  maxFrames?: number
}

async function fetchGifFrames(gifUrl: string): Promise<{ frames: ParsedFrame[]; gifW: number; gifH: number }> {
  const res = await fetch(gifUrl)
  if (!res.ok) throw new Error(`Failed to fetch GIF: ${res.status}`)
  const buf = await res.arrayBuffer()
  const parsed = parseGIF(buf)
  const frames = decompressFrames(parsed, true)
  if (frames.length === 0) throw new Error('GIF has no frames')
  return { frames, gifW: parsed.lsd.width, gifH: parsed.lsd.height }
}

// Draws a coalesced (full-size) frame onto `fullCtx`, honoring disposal so the
// running canvas is a complete image for the current frame index.
function makeCoalescer(fullCtx: CanvasRenderingContext2D, gifW: number, gifH: number) {
  const patchCanvas = document.createElement('canvas')
  const patchCtx = patchCanvas.getContext('2d')!
  let savedForRestore: ImageData | null = null

  return {
    // Blit the frame's patch onto the full canvas (call before reading `full`).
    draw(frame: ParsedFrame) {
      const { dims, disposalType } = frame
      if (disposalType === 3) savedForRestore = fullCtx.getImageData(0, 0, gifW, gifH)
      patchCanvas.width = dims.width
      patchCanvas.height = dims.height
      const patchData = new Uint8ClampedArray(frame.patch.length)
      patchData.set(frame.patch)
      patchCtx.putImageData(new ImageData(patchData, dims.width, dims.height), 0, 0)
      fullCtx.drawImage(patchCanvas, dims.left, dims.top)
    },
    // Apply this frame's disposal so the next frame starts from the right base.
    dispose(frame: ParsedFrame) {
      const { dims, disposalType } = frame
      if (disposalType === 2) fullCtx.clearRect(dims.left, dims.top, dims.width, dims.height)
      else if (disposalType === 3 && savedForRestore) {
        fullCtx.putImageData(savedForRestore, 0, 0)
        savedForRestore = null
      }
    },
  }
}

// Draws `full` (the GIF frame) scaled to "cover" the output rect, then the
// transparent foreground on top.
function compositeFrame(
  ctx: CanvasRenderingContext2D,
  full: HTMLCanvasElement,
  foreground: HTMLCanvasElement,
  outW: number,
  outH: number,
  gifW: number,
  gifH: number
) {
  const scale = Math.max(outW / gifW, outH / gifH)
  const dw = gifW * scale
  const dh = gifH * scale
  const dx = (outW - dw) / 2
  const dy = (outH - dh) / 2
  ctx.clearRect(0, 0, outW, outH)
  ctx.drawImage(full, dx, dy, dw, dh)
  ctx.drawImage(foreground, 0, 0, outW, outH)
}

/**
 * Composites a (transparent-background) foreground canvas over every frame of an
 * animated GIF background and re-encodes the result as an animated GIF blob.
 *
 * Decoding uses gifuct-js (pure JS) so it doesn't depend on the browser's
 * WebCodecs ImageDecoder, which isn't reliably exposed in every Electron build.
 */
export async function buildAnimatedGif(
  foreground: HTMLCanvasElement,
  gifUrl: string,
  { maxWidth = 1100, maxFrames = 60 }: GifOptions = {}
): Promise<Blob> {
  const { frames, gifW, gifH } = await fetchGifFrames(gifUrl)

  const full = document.createElement('canvas')
  full.width = gifW
  full.height = gifH
  const fullCtx = full.getContext('2d', { willReadFrequently: true })!
  const coalescer = makeCoalescer(fullCtx, gifW, gifH)

  const outScale = Math.min(1, maxWidth / foreground.width)
  const outW = Math.max(1, Math.round(foreground.width * outScale))
  const outH = Math.max(1, Math.round(foreground.height * outScale))

  const comp = document.createElement('canvas')
  comp.width = outW
  comp.height = outH
  const ctx = comp.getContext('2d', { willReadFrequently: true })!

  const step = frames.length > maxFrames ? Math.ceil(frames.length / maxFrames) : 1

  const gif = GIFEncoder()

  for (let i = 0; i < frames.length; i++) {
    const frame = frames[i]
    coalescer.draw(frame)

    if (i % step === 0) {
      compositeFrame(ctx, full, foreground, outW, outH, gifW, gifH)
      const { data } = ctx.getImageData(0, 0, outW, outH)
      const palette = quantize(data, 256)
      const index = applyPalette(data, palette)
      const perFrameMs = frame.delay && frame.delay > 0 ? Math.max(20, frame.delay) : 100
      gif.writeFrame(index, outW, outH, { palette, delay: perFrameMs * step })
    }

    coalescer.dispose(frame)
  }

  gif.finish()
  return new Blob([gif.bytes() as unknown as BlobPart], { type: 'image/gif' })
}

/**
 * Fallback for when animated encoding fails: composites the foreground over just
 * the GIF's first frame and returns a still PNG — so the background still appears.
 */
export async function buildGifStillPng(
  foreground: HTMLCanvasElement,
  gifUrl: string,
  { maxWidth = 1400 }: GifOptions = {}
): Promise<Blob> {
  const { frames, gifW, gifH } = await fetchGifFrames(gifUrl)

  const full = document.createElement('canvas')
  full.width = gifW
  full.height = gifH
  const fullCtx = full.getContext('2d')!
  makeCoalescer(fullCtx, gifW, gifH).draw(frames[0])

  const outScale = Math.min(1, maxWidth / foreground.width)
  const outW = Math.max(1, Math.round(foreground.width * outScale))
  const outH = Math.max(1, Math.round(foreground.height * outScale))

  const comp = document.createElement('canvas')
  comp.width = outW
  comp.height = outH
  const ctx = comp.getContext('2d')!
  compositeFrame(ctx, full, foreground, outW, outH, gifW, gifH)

  return await new Promise<Blob>((resolve, reject) => {
    comp.toBlob(b => (b ? resolve(b) : reject(new Error('toBlob failed'))), 'image/png')
  })
}
