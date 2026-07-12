# Tableau 交付索引

本目录定义如何用 `bi_exports/current/` 中已经通过 DataOps 门禁的小型 ADS CSV 构建招聘展示版 Tableau Dashboard。

- [DASHBOARD_SPEC.md](DASHBOARD_SPEC.md)：页面、图表、交互与视觉规格。
- [CSV_DATA_DICTIONARY.md](CSV_DATA_DICTIONARY.md)：每个 Tableau 数据源的粒度、字段和口径。
- [BUILD_GUIDE.md](BUILD_GUIDE.md)：在 Tableau Public/Desktop 中的制作与刷新步骤。
- [ACCEPTANCE_CHECKLIST.md](ACCEPTANCE_CHECKLIST.md)：发布前逐项验收。

本项目不会生成或伪造 `.twb` / `.twbx`。工作簿必须在真实 Tableau 环境中连接已发布 CSV、逐项核对后保存；公开发布还需要项目所有者登录 Tableau Public。当前硬性交付是可复现规格和经同一 ADS 数据驱动的 Streamlit Dashboard。

