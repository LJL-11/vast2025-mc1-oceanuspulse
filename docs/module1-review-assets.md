# 01 页素材包与本地预览

[module1-review-assets.zip](module1-review-assets.zip) 包含作品地图、音乐影响图、合作关系图及六张唱片封面，共 204 个文件。素材包与 01 页评审版配套。

SHA-256 `d151361e7f5cf050f53c412955447cb42e96365b54497b3f76c15337b977cff1`

## 复现步骤

拉取 `feat/module1-record-archive`。在仓库根目录按 [README 的快速开始](../README.md#快速开始clone-后必须先生成数据) 生成数据。然后在仓库根目录执行以下 PowerShell 命令。

```powershell
python -m zipfile -e docs/module1-review-assets.zip web
Set-Location web
npm ci
$env:VITE_MODULE1_REVIEW_ASSETS = '1'
npm run dev
```

访问 [01 页](http://127.0.0.1:5173/?module=influence)。如需生产构建，在同一个终端运行 `npm run build`，输出在 `web/dist/`。解压后，图表入口应位于 `web/public/module1-review/`。

素材包内的 `public/module1-review/PROVENANCE.md` 记录了上游来源与许可状态。Musicmap、LOTR 和唱片封面的再分发许可未确认。
