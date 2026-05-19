# HyperFrames Render Notes

在本目录执行以下命令即可预览或渲染：

```bash
npx hyperframes lint
npx hyperframes inspect --samples 12
npx hyperframes render --quality draft --output ../exports/naval-longterm-draft.mp4
```

当前工程已接入 `../voice/narration-edge.wav` 中文旁白音轨。
如果后续要换配音，替换音频文件并保持同名即可直接重渲染。

当前版本为纯排版动态图形，无外部素材依赖。
