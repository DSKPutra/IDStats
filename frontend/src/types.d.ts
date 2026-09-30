declare module 'plotly.js-dist-min' {
  const Plotly: {
    react: (el: HTMLElement, data: unknown[], layout?: object, config?: object) => Promise<unknown>
    purge: (el: HTMLElement) => void
    downloadImage: (el: HTMLElement, opts: { format: 'png' | 'svg'; filename: string }) => Promise<string>
  }
  export default Plotly
}
