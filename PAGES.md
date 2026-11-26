# GitHub Pages 发布说明

本仓库包含响应式中文产品雷达 dashboard，默认无虚构数据。

1. 仓库管理员在 Settings → General → Danger Zone → Change repository visibility 将仓库改为 Public。公开后仓库所有文件及提交历史都可被访问，不能依靠网站门禁隐藏仓库文件。请先检查历史中不存在私人信息、密钥或未批准公开的草稿。
2. 在 Settings → Pages → Build and deployment → Source 选择 GitHub Actions。
3. 在 Actions 中运行 Deploy Pages（若工作流尚未提交，请先按下面示例创建）。以后 main 分支提交自动触发。
4. 默认站点地址：https://monster-echo.github.io/mobile-product-radar/

## 归档契约

data/YYYY-MM-DD.json：顶层 date、products 数组。产品字段 name、product_id、platform、category、region、chart、rank、core_function、gameplay、heat_evidence、monetization、uncertainty、source_urls、opportunity_score。缺失值使用 null，不伪造。每日同一榜单完整快照及稳定产品 ID 支持连续上榜计算。

quality/YYYY-MM-DD.json：date、total、scores（accuracy、coverage、business、actionability、presentation）、status（published）、public_approved（必须显式为 true）、hard_gates（no_fabrication、date_region、chart_types、commercial_license、json_consistency、missing_data_disclosed 均为 true）。另需同日期 daily/YYYY-MM-DD.md。

网站仅从审核通过且明确允许公开的报告生成索引。公开仓库里不要保存任何私人资料或未批准公开的报告；未达标报告应留在私有位置。

本地构建：python scripts/build_pages.py，然后 python -m http.server --directory _site 8000。

## 工作流

将下列内容保存为 .github/workflows/pages.yml：

```yaml
name: Deploy Pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - run: python3 scripts/build_pages.py
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site
      - uses: actions/deploy-pages@v4
        id: deployment
```
