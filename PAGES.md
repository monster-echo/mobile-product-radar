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

## 定时采集与部署

工作流位于 .github/workflows/pages.yml。每日 UTC 13:17（北京时间21:17；洛杉矶冬令时05:17、夏令时06:17），也可手动运行。main 的普通内容提交触发构建；GitHub 调度可能延迟。GitHub Actions 使用仓库 GITHUB_TOKEN 写入公开快照，不需要用户提供密钥。

- scripts/collect_daily.py：Apple 榜单、Hugging Face、Show HN、Reddit、AppBrain、方舟网公开观察，失败逐源记录。Product Hunt 仍由编辑任务补查。目录链接不当作榜单。
- scripts/enrich_catalog.py：对已审核报告中的产品，查询 Apple、Google Play、方舟网详情；不确定匹配拒绝。当前版本和评分与历史榜单日期分离。图片只使用标识清晰的 HTTPS 来源地址，不下载或复制评论全文。
- scripts/archive_metadata.py：校验目录及最低质量门槛，保存本次匹配的资料记录。
- snapshots/YYYY-MM-DD/*.json：未审核公开观察，不能当作已发布日报。
- metadata/YYYY-MM-DD/*.json：带观测时间的资料快照。
- daily/、data/、quality/：仍由编辑任务负责，按 QUALITY.md 门禁发布。

扩展产品字段：developer, icon_url, screenshots, store_url, release_date, updated_at, version, rating, rating_count, description, features, review_insights, differentiation, completeness_score, detail_source_urls, detail_status。历史数据不得以最新元数据覆盖。当前观测字段包括 live_rating, live_rating_count, live_version, live_updated_at, metadata_observed_at。

实际运行效果以 Actions 日志及真实产出为准。第三方接口可能受限；鸿蒙解析依赖页面结构；未经审核的公开快照不进入正式日报。公开仓库不可存放私人信息、原始评论全文或未批准公开的报告。
