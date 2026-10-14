# Source Ledger · 离线资料检索与阅读台账

**检索有出处，阅读有记录，覆盖范围可核对。**

[English](README.md) · [输入格式](docs/input-format.md) · [设计说明](docs/design.md)

![资料报告](docs/overview.jpg)

从之前的个人公众号和群聊知识库中提取通用能力，支持文章、聊天、笔记和转写文本。
资料保存在本地 SQLite 中，不调用模型，也不需要 API 密钥。

```bash
python -m source_ledger import examples/demo.jsonl
python -m source_ledger search 项目
python -m source_ledger status
python -m source_ledger export review --format html --output evidence.html
```

核心需要 Python 3.10+，无额外运行依赖。导入自己的 Markdown：

```bash
python -m source_ledger import notes.md --kind note --source 我的笔记
```

检索结果带原始来源、标题、日期、编号、内容哈希和字符范围。重复导入不产生重复记录；
使用稳定原始 ID 的资料更新后，旧阅读标记会失效。可以逐块阅读、记录核对意见，
也可以导出带出处的 Markdown、JSON 或 HTML 摘录包。

“已导入”“检索命中”“人工标记已阅读”分别统计。工具不会以导入数量宣称历史完整，
也无法证明使用者确实读懂了文本。搜索采用字面匹配，尚未提供语义搜索或自动问答。

可选安装 `pip install ".[mcp]"`，通过 `source-ledger-mcp --root 资料库绝对路径`
让 AI 助手检索。接口只提供检索、读摘录、查覆盖三项能力，不会替人工标记已读，
也不能导入或删除资料。返回给 AI 的文字可能进入其模型上下文，请选择合适的资料库。
具体配置见 [MCP 接入说明](docs/mcp.md)。

运行 `python -m unittest discover -s tests -v`，当前 14 项核心测试通过；
安装可选 MCP 依赖后共 20 项通过，包含真实进程间协议验证。
仓库只有模拟示例，不包含个人聊天或采集账号。MIT 许可。
