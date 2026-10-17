# CHANGELOG — wechat-article

本技能变更记录。**对应关系只到发布线**：`main` 与 `rel-x.y.z` 分支上是「一个版本 = 一个提交 = 一个 tag」，本文件的每个版本段落对应发布线上那一个提交；本地安装目录所在的 `master` 线是工作树快照，按同一版本号提交、不参与发布。两条线没有共同祖先（`git rev-list --max-parents=0 --all` 给出 `8bc11a3` 与 `92a41af` 两个根），跨线 merge/rebase 没有定义，不要尝试。版本号只用在 tag 上，分支一律 `rel-` 前缀——此前 `refs/heads/v4.3.0` 与 `refs/tags/v4.3.0` 同名，本轮改名 `rel-4.3.0`。

## 4.5.2（2026-10-17）安装件与仓库件不逐字节相同这件事写进文档 + 本地行尾归一

发布 v4.5.1 后做了一次端到端回读：把 `v4.5.1` 装进空目录，再和发布工作树逐个文件比哈希。52 个文件里
46 个相同，6 个 `SKILL.md` 不同——不是内容丢了，是 GitHub CLI 在落地时把 frontmatter 重新序列化了一遍：
键按字母序重排（`name`/`description`/`version` 变成 `description`/`metadata`/`name`/`version`）、
`description` 的引号风格改写、`---` 后面的空行去掉，并注入 `metadata.github-path` / `github-ref` /
`github-repo` / `github-tree-sha` 四项安装来源标记。注入前的子树仍然对得上：安装件的 `github-tree-sha`
是 `e84b100c…`，与 `git rev-parse v4.5.1:skills/wechat-article` 逐字符相同。这条区别决定了
「下载件与仓库件逐字节相同」只对 tag 归档成立，读者按哪条路径安装会影响后面的比对与 diff，所以要写进文档，
不能只记在变更日志里。

- **发布仓库根 README 补一段安装路径的区别**：`gh skill install` 的落地件带安装元数据、frontmatter 被
  重排；下载 `…/archive/refs/tags/<tag>.zip` 解压取出的目录与仓库件逐字节相同。要拿技能目录做二次分发
  或版本比对，走归档路径；只是装进助手用，两条都行。
- **v4.5.1 那处判据修复的复跑结果**：Actions run `39033591716`，`bs4=installed` 与 `bs4=none` 两格
  都成功。前一格打印「Markdown 断言：bs4 路径（结构 7 项）」，后一格打印「Markdown 断言：
  regex-degraded 路径（本机未装 bs4，结构断言不适用）」，两格汇总都是「判据文件 8 个：通过 7 ·
  跳过 1 · 失败 0 项」；跳过的一格是 `test_qa_mobile.py`（CI 没有 playwright，渲染验收未跑），
  汇总行按「跳过不计入通过」的口径单列它，上一轮报红的 7 项不再复现。
- **本地行尾归一**：`materials/scripts/gen_cover.py`、`scripts/check_draft.py`、`scripts/wx_api.py`、
  `write/scripts/validate_wx_html.py`、`tests/fixtures/sogou_type2_sample.html` 五个文件此前是 CRLF，
  统一成 LF。发布树不含这一改动的影响——同步工具本来就把文本写成 LF，仓库根 `.gitattributes` 再固定
  检出行为，所以归一后 52 个文件的逐字节核对仍全部相同，发布内容一字未变。
- **本轮没有动的四处遗留**：旧 tag `v4.2.0`–`v4.4.0` 的 `CHANGELOG.md` 第 244 行仍带着当年的示例作者
  姓名（清除要改写已发布历史）；`master` 与 `main` 两条无共同祖先的谱系仍共用一个 `.git`；远端
  `rel-4.5.0` 分支与上一版本留在系统临时目录里的那个工作树未删（删分支、退工作树都是不可逆动作）；
  `gh skill publish` 仍在报六个 `SKILL.md` 缺 recommended 的 `license` 字段、仓库没有 tag 保护 ruleset。

## 4.5.1（2026-10-17）Linux CI 首跑抓到「判据只在装了 bs4 的机器上成立」

v4.5.0 发布后 `verify.yml` 首跑（Actions run `39032141690`，`ubuntu-latest`）报 7 项失败，全在
`tests/test_read_gate.py` 的 Markdown 结构断言。分诊结论不是排版回归：`read/scripts/read_wechat.py`
的 `html_to_md()` 第一句是 `from bs4 import BeautifulSoup, …`，`ImportError` 就落进正则剥标签的降级
路径（`extract_content()` 把引擎记在结果的 `parse_mode` 里，`read/SKILL.md` 写明
`regex-degraded` 这条「不产结构，只有段落文本」）。本机装了 bs4 4.15.0，结构七项全中；CI 的 Ubuntu
runner 没有 bs4，同一份判据拿降级产物去比 bs4 产物，必红。**报错的是判据的适用前提，不是脚本。**

- **判据按引擎分支**：`tests/test_read_gate.py` 新增 `_bs4_present()`（只听 `ImportError`，与被测代码
  的 catch 口径逐字对齐——bs4 装了但坏了要抛成执行异常，不当成没装）。第 1 节分两支：有 bs4 时先要求
  `parse_mode == "bs4"`，再跑结构七项；无 bs4 时改判文档承诺的那条契约——`parse_mode` 必须是
  `regex-degraded`、不得出现 `## ` 与 `**` 结构、不得出现图片/代码块语法、段落文本仍在。两支都打印
  自己走的是哪条路径，日志能看出这一跑到底测了什么。
- **CI 加 bs4 矩阵**：`verify.yml` 用 `bs4: [none, installed]` 两格，同一批判据在有/无 bs4 的环境各跑
  一遍，`fail-fast: false` 让两格互不掩盖。本机只有「有 bs4」这一格，降级分支在本轮之前从未被任何
  环境执行过——矩阵补的是这个洞。
- **判据覆盖面扩到仓库根 README**：`tests/test_evals_routes.py` 新增 `repo_meta_files()`，把发布仓库
  根那一层的 README 也纳入大小写核对——它写在技能子树之外，却全是 `skills/wechat-article/read/SKILL.md`
  这种完整式路径；判据剥掉 `skills/wechat-article/` 前缀后与子树内同一口径比对。本地安装树没有这一层，
  取不到即跳过，所以同一份判据在 324 处（本地树）和 338 处（发布树）两种布局下都是绿的。
- **变异核验 19 例全检出**（隔离副本树；「无 bs4」用临时假包复现，`bs4/__init__.py` 里抛
  `ImportError`）：D1 降级路径伪造 `## ` 结构、D2 降级路径返回空串、D3 无 bs4 却报
  `parse_mode="bs4"`、D4 有 bs4 时删掉 img 映射、D5 无 bs4 且实现正常必须为绿；E1 在
  `skills/wechat-article/` 嵌套布局旁放一份把目录名写错大小写的仓库根 README 要报红、E2 同一位置
  写法正确必须为绿（这一对是上面那条判据的证伪）；连同 4.5.0 那批 A1–A7、B1–B3b、C1，
  共 19 例，未被检出 0 个。
- **实现与文档口径**：`html_to_md()` 的实现、`parse_mode` 的三种取值一字未改，本轮只改判据的适用前提。
  要结构化 Markdown 就得装 bs4，这一条写进 `read/SKILL.md` 与发布仓库根 README，不再让读者从
  「不产结构」反推该装什么。
- **遗留**：`verify.yml` 只跑判据、不跑 `gh skill publish --dry-run`；CI 无浏览器，
  `test_qa_mobile.py` 在 CI 恒为 SKIP（渲染验收目前只有本机 msedge 跑过），是否给 CI 加
  Playwright + Chromium 取决于愿不愿意为它增加下载依赖，本轮没有加。

## 4.5.0（2026-10-17）发布口径落进判据与文档 + 读取层跨平台解耦 + 三处判据补漏

本轮不新增能力，把上一轮批判里成立的十一处逐条改掉：能在仓库里变成判据的做成判据，不能的写清口径与归属。

- **行尾收成一种**：`CHANGELOG.md` 此前本地 587 个 CRLF、0 个裸 LF，是全树唯一例外，而发布链路
  会把它改写成 LF——「发布物与本地逐字节一致」这一条对它永远不成立，且没有任何一处文档说明它为什么
  是 CRLF。本轮转成 LF（587 行，字节 59655→59068，只差 587 个 `CR`，正文逐行未变），发布仓库根加
  `.gitattributes`（全树 `text=lf`）把这条写死在检出行为里。
- **大小写双轨加了判据**：本地是 `write/ read/ search/`，发布树按 gh skill 的 `skills/<name>/` 结构
  收成小写，18 个路径两头不一致，Windows 文件系统不敏感、Linux/macOS 克隆后照文档跑就 file not found。
  `tests/test_evals_routes.py` 新增第 3 件事：全树文本里的顶层目录引用（`write/…` 斜杠式与 `"read"`
  引号式，本轮核对 321 处）与磁盘目录名**逐字符**比对，大小写不符或路径不存在即报红；同一份判据在
  大写树与小写树都跑通，所以「发布物由本地树映射而来」不再靠人工约定。存在性只查「像路径」的引用
  （末段带 `.ext` 或原文以 `/` 结尾），因为 `draft/add`、`draft/batchget` 是微信接口名、
  全由顶层目录名串起来的写法是散文并列；`os.path.join(HERE, os.pardir, "write", …)` 这种拼出来的
  加载路径不在本判据覆盖内（不是一个连续字符串），那一类由加载方测试自己炸成执行异常。
- **读取第四层不再写死 Windows 路径**：`read_wechat.py` 的 `devtools_ws_url()` 原先固定
  `~\AppData\Local\Microsoft\Edge\User Data\DevToolsActivePort`，号称可分发的技能在 macOS/Linux 上
  这一层必失败且无分支提示。现在按 `sys.platform` 给候选，新增两个符号
  `devtools_port_candidates()`（win32 那条本机实测；darwin/linux 两条按 Edge profile 目录惯例给出，
  **未跨平台实测**）与 `devtools_port_file()`（环境变量 `WX_EDGE_DEVTOOLS_PORT_FILE` 优先，
  指不到时报错点名该变量与路径）。判据在 `tests/test_read_gate.py` 第 8 节，按 8a–8e 五向断言：
  环境变量覆盖优先、指空文件报错点名、两行缺一报「内容不完整」、候选全不存在时报错点名前提、
  三平台候选两两不同（分支塌成一条即红）。`read/SKILL.md` 与 `read/references/cdp-edge.md` 同步。
- **重试上限从口头改成实现值**：`read/SKILL.md` 与 `cdp-edge.md` 都写「单 URL 不超过 3 次」，而
  `http_get(tries=2)` × 第 1–3 层的实际上限是 6 次、第 4 层是浏览器导航不计入。现在写 6 次，并把数
  钉进常量 `LAYER_TRIES` / `HTTP_MAX_PER_URL`；`test_read_gate.py` 第 9 节要求常量、
  `http_get` 默认值、脚本 docstring、两份文档五处同值，改任一处而其余没跟就报红。
- **跳过不算通过**：`test_qa_mobile.py:26` 未装 playwright 时 `return []`，被 `run_all` 计成通过，
  于是「判据文件 8 个，失败 0 项」证明不了 8 个都跑过（上一轮交付里就这么引用过一次）。现在
  `run()` 把原因写进模块全局 `SKIP`，`tests/run_all.py` 汇总改成「判据文件 N 个：通过 X · 跳过 Y ·
  失败 Z 项」，有跳过时末行明写「不能当通过引用」。
- **Search 的研究记录出正文**：`search/SKILL.md` 汉字 4278、非空行 74（`write/SKILL.md` 是 889/45），
  正文里装的是 26 用例样本、判定纪律、七项未判定，是研究记录而不是工作流，且是五个子技能里唯一没有
  `references/` 的。新建 `search/references/sogou-probe.md`（1725 汉字）收样本明细、
  「为什么不做到页去重/不早停」、预热 A/B、拦截页形态、票据存活时长与七项未判定各自缺什么证据；
  正文每格只留结论并指过去，正文降到 3902 汉字。搬走的段落逐段在新文件有对应小节，没有删事实。
- **跨子技能依赖登记进根**：`scripts/wx_draft_push.py` 的推送闸口按目录名加载
  `write/scripts/validate_wx_html.py` 的 `validate()`，`tests/` 里 `test_prose_pivots.py`、
  `test_qa_mobile.py`、`test_validate_rules.py`、`test_theme_blocks.py` 四支按目录名取 `write/` 下的
  脚本与 `write/references/theme-default.md`。`write/` 改名会同时打掉推送闸和这四支判据，而这条边
  此前没写进任何前置说明；现在写在根 SKILL.md「目录与路由」下面，并由上面那条大小写判据守。
- **根 SKILL.md 自相矛盾修掉**：一边声明「清单在子技能正文里，根不重复列」，一边在安全习惯第 2 条
  列出三支 `write/scripts/*.py`。该条改为只写闸的顺序与名字（写作硬禁令 → 排版红线静态校验 →
  390px 真机渲染 → 推送 → 回读逐字比对），脚本路径归子技能；「不重复列」也收窄成「不重复列有哪些脚本、
  各自做什么」，与依赖登记那句划清。
- **用例数不设上界**：`test_evals_routes.py` 原来把 evals 用例数硬卡在 8–10，加第 11 条就报红，而
  这条约束不是质量判据、只会让下一个人先撞它。改成只卡下界（少于 8 条 = 覆盖面塌了）。
- **发布工具**：同步脚本不进技能仓库，也不再放在系统临时目录（此前 `Temp/sync_release.py` 写死含
  本机用户名的 SRC/DST，清一次临时目录等于发布能力归零）。工具改为路径全部由命令行给、脚本内不含
  任何绝对路径，新增 `--check-only` 逐文件核对发布树；本轮用它对 v4.4.0 的发布树实测同步前状态：
  **应交付 52 个文件，逐字节相同 41 个，内容有差异 10 个（9 个本轮改过的文件 + `SKILL.md` 的版本号），
  目标缺失 1 个（新增的 `search/references/sogou-probe.md`），目标多余 0 个**；同步后复核为
  逐字节相同 52 个、发布树内残留大写目录引用 0 处。仓库里留下的是映射口径本身
  （发布仓库根 README）与守它的判据，两者合起来足够重建发布树，不依赖某个脚本文件是否存在。
  仓库内不写绝对路径、不写本机用户名，个人环境留在仓库外。
- **发布仓库根补齐**：`README.md` 三处指向不存在的东西，逐处按实测改写——「`gh >= 2.90`」换成
  本机实测版本（`gh 2.101.0`，`gh skill install --help` 可查）；Claude Code 的
  `/plugin marketplace add` 那行删掉，仓库里没有 `.claude-plugin/marketplace.json`，那条命令在这里
  没有可核验的落点；「下载 Release 归档」改成 tag 归档 URL 本体，并实测 `…/archive/refs/tags/v4.4.0.zip`
  返回 200（`codeload` 重定向），因为 Releases 的自定义资产数是 0，只有 tag 归档真的能下。
  新增两节：「目录名与行尾口径」写清小写化规则、谁守它（`tests/test_evals_routes.py`，小写树与大写树都跑）、
  `.gitattributes` 钉 LF、以及同步脚本为什么在仓库外；「测试与评测」补上汇总行的含义与「跳过不计入通过」。
  另记一条发布线缺口：本轮 `gh release list` 实测最新 release 是 v4.3.1，远端 tag `v4.4.0` 存在但没有对应
  release（那次只推了 tag），v4.4.0 的 release 按已存在的 tag 补建。
- **仓库根新增 `.gitattributes` 与 Linux CI**：`.gitattributes` 用 `* text=auto eol=lf` 把检出行为钉成 LF，
  图像与压缩包声明 binary；`.github/workflows/verify.yml` 在 `ubuntu-latest` 上跑 `python tests/run_all.py`
  （`PYTHONUTF8=1`，无凭据、无网络），这一跑同时是那条大小写判据的异地验证——Linux 文件系统大小写敏感，
  本地 Windows 上「文件能打开」证明不了引用与磁盘名逐字符一致。CI 上没有浏览器，`test_qa_mobile.py`
  会打 SKIP 并计入「跳过」，汇总行不会把它写成通过。
- **个人敏感信息复扫**：发布前逐字符扫九类模式——本机用户名、`AppData`、盘符绝对路径、GitHub
  token 前缀字样、公众号 AppID 形态 `wx[0-9a-f]{16}`、32 位十六进制串、邮箱、IPv4。本地树与
  发布树各扫一遍，两边逐类相同：用户名 0、盘符绝对路径 0、AppID 0、邮箱 0、真实 token 0。
  剩下的命中全部有出处——`AppData` 是 `%LOCALAPPDATA%`、`os.path.join(home, "AppData", "Local")`
  与文档里的 `~/Library/Application Support/...`、`$XDG_CONFIG_HOME` 这类占位写法；IPv4 是回环
  `127.0.0.1` 和 UA 串里的 Chrome 版本号（`120.0.0.0` 那种四段全带点，不是地址）；32 位十六进制
  集中在 `tests/fixtures/sogou_type2_sample.html`，是搜狗结果页自带的静态资源哈希，随页面快照原样
  存进来（本地树与发布树各 20 处）。扫描时唯一命中的人名是 4.0.5 段落里那句
  「示例作者名更新为实际使用值」后面跟着的真名——本轮删掉，删后两棵树的人名命中为 0：
  作者名不属于变更说明，留在一个对外分发的仓库里没有用途。扫描脚本与发布工具放在仓库外
  （它的规则里就写着本机用户名），技能目录内不留任何绝对路径。
- **验证**：`tests/run_all.py` 在本地大写树与发布小写树各跑一遍，两次都是「判据文件 8 个：通过 8 ·
  跳过 0 · 失败 0 项」；同步后 `--check-only` 复核 52 个文件逐字节相同、发布树内大写目录引用 0 处。
  变异核验在隔离副本树跑
  12 个用例，全部被检出、0 漏：环境变量指定被忽略、报错不点名变量、重试常量改了文档没跟、常量改了
  行为没跟、`darwin` 分支塌成 `if False`、`win32` 分支恒真、端口文件两行校验被删、文中大小写与磁盘
  不符、被引用文件删除（断链）、evals 删到 8 条仍绿（证明上界已撤）与删到 7 条报红（下界仍在）、
  缺 playwright 时汇总把「跳过」单列。
- **遗留**：`check_duplicates.py`、`render_mermaid.py`、`wrap_preview.py`、`gen_cover.py`、
  `upload_imgs.py` 五支脚本仍无判据（后两支直接打接口，出错消耗配额）；搜狗那七项未判定要等本机 IP
  冷却后按 `search/references/sogou-probe.md` 第 7 节逐格复采；darwin/linux 两条 Edge 候选路径未跨平台
  实测，跨平台用户先按 `WX_EDGE_DEVTOOLS_PORT_FILE` 指定；结构哨兵只判数量关系，不判语义字段错位。

## 4.4.0（2026-10-17）搜狗搜索第二轮实测 + 时间过滤、结构哨兵、票据时刻

只动 `search/`（脚本 + 文档 + 用例 + evals 期望），接口层与写排推链路未改。

- **第二轮参数实测**（26 个参数用例，10 个最终被拦；另一次复采连续四次请求全拦后熔断收手，本机 IP 已进入持续拦截）。写进 `search/SKILL.md`
  第二节的新事实：`s_from`/`_sug_` 可省；`page=10` 仍出结果、`page=11`/`12` 返回无结果容器
  且两次页长逐字节相同（10488）；`tsn=1..4` 四次全部 302 回首页；`type=1` 两轮均空容器；
  真实切片里同页 `timeConvert` **非严格倒序**（10 条 4 处后条比前条新，跨度 0.3 天）。
  同节新增**判定纪律**：26 个用例里 10 个最终命中 `antispider`，
  成功失败与参数无稳定对应，故单发 BLOCK 只能记「未判定」，不得写成参数结论——
  `num`/`n`、`ie=gbk`、缺 `type`、`"精确短语"`、`site:`、`ft`/`et`、`ss_st`/`ss_et`
  七项按这条纪律留白，检索语法是否真生效也没做完对照。
- **交叉比对暴露的两处本地缺陷（修）**：其一，搜索页拿到传输层失败（超时/DNS/连接重置）时
  `search()` 直接读 `resp["html"]`，整条 CLI 以 `KeyError: 'html'` 崩掉——本机被持续拦截那段时间
  正好容易触发。现在这类失败单独打「传输层异常」NOTE 并立即停止翻页，与「被拦截」「本页 0 条」
  三种文案互斥：不把一次超时谎报成搜狗拦我，也不谎报成没结果。其二，结果页的 `href` 以前
  只 `urljoin` 补全不验域，`href="//evil.example/x"` 会被拼成合法外域链接交付出去，`-r` 还会
  拿着本机会话去请求它，调用方也可能顺手把它交给 `read/`。新增 `safe_link`：只放行
  `https://weixin.sogou.com` 且不带端口，其余条目 `link` 置空并落 `link_error`，标题/日期/摘要
  照常交付，`-r` 不为它发一次请求；条目数不变，因此不会被结构哨兵误报成改版。
- **第三轮：按「先确认有价值再做」复现并修掉两处**（探针走真实 `fetch`，打桩只换 opener；还原侧用三形态外域样本，全程离线）。其一，`fetch` 把 `HTTPError` 和 `URLError` 混在一个
  `except` 里、只留 `error` 字符串，于是 429/403/503 被打印成「传输层异常，既不是拦截也不是无结果」，
  `-r` 期间撞 429 也不触发熔断——实测 `want=5` 会照样把 5 个 `/link` 全请求一遍，正是第四节写着
  「再撞只会加深风控」的那个动作。现在失败带 `http_status`，这三个码归「被拦截：服务端按状态码拒绝」
  并立即熔断后续还原，500 与网络抖动仍归「传输层异常」，两种文案互斥。其二，`resolve_link` 判
  「是不是微信链接」用的是子串包含，`https://mp.weixin.qq.com.evil.example/s?x=1` 也算命中，
  meta refresh 与 `url +=` 两种形态抽出的目标根本不验主机，外域链接会被当真实链接交付、还会被转手
  交给 `read/`。新增 `safe_mp_link`（只放行 https + `mp.weixin.qq.com`，无端口），三形态统一过它；
  丢弃时 `resolved` 留空、原因落 `resolve_error`、条目继续带搜狗跳转链接，不算拦截、后续条目照常尝试。
  探针还撞出两处连带脆弱点并一并修掉：主机位置 `[` 不配对时 `urljoin`/`urlsplit` 抛
  `ValueError('Invalid IPv6 URL')`，一条坏 href 能把整次搜索弄崩（现在按非法 URL 只丢那一条）；
  打印的失败原因里原样带着页面文本，控制字符能直接打到终端（现在 `_brief` 先剥控制字符再截 120 字符）。
- **拦截标记集加 `anti.min.css`**：仓库样本 `tests/fixtures/sogou_antispider_sample.html` 里实存
  （拦截页自带 `static/css/anti.min.css`），本机两张真实结果页切片 0 次命中，加进去不产生误判。
- **`--after/--before`（新增）**：客户端按结果页时间戳筛，闭区间、`--before` 含当天全天、
  无时间戳条目丢弃并计数；非法日期与空区间退 2。带时间过滤而未显式给 `--pages` 时默认
  翻满 10 页——同页日期非严格倒序，只翻一页就断言「窗口内没结果」等于把覆盖不足当成
  搜狗没收录；NOTE 固定报告窗内条数与观测日期跨度。搜索 URL 始终不带 `tsn`/`ft`/`et`/`ss_st`。
- **结构哨兵（新增）**：`parse_results` 每次解析核对 box id / `h3>a` / `timeConvert` /
  `span.all-time-y2` 四类节点数量与条目数，背离即打印「结构漂移」或「字段命中率下降」NOTE，
  结果照常交付；`--fixture` 离线路径同样触发，巡检不再靠人眼比对。链接数不参与判定
  （实测每条结果有 2 跳，一页 20 条链接）。
- **拦截页与预热口径**：`block_reason` 命中 `antispider`/`wappoc_appmsgcaptcha` 时直接说明
  这是页内点选验证、脚本层无可自动化的填写动作，唯一处置是停手转人工。cookie 预热做 A/B：
  第三方入口 `v.sogou.com/v?...&p=40030600` 属视频频道，只落 `VIDEO_DEBUG`/`wuid`、
  不带微信频道要的 `ABTEST`/`SUID`，紧随其后的搜索正好被拦——**保持首页引导，不替换**。
  第四节另删掉一处引用外部帮助中心的说法（本机取不到该页，不能作为依据）。
- **`resolved_at`（新增字段）**：还原成功时落本机时刻，票据时效从口头提醒变成可比对的数；
  text 输出多一行「还原时刻」，json 带字段。票据确切存活时长仍未实测，两条处置不依赖时长。
- **第四轮：六项「信息在当前设计里会丢」的增补**（先离线复现确认缺口再动手，探针走真实 `fetch`、
  打桩只换 opener；第 7/8 项按指令先实测，结论见本组最后一条）。
  1. **`--account 公众号名`**：`type=1` 实测是空容器，账号检索没有服务端入口，于是对已解析出的
     `account` 字段做不区分大小写的子串筛选，且放进翻页循环内——筛选后的条数才参与「凑够 `-n` 即停」
     判定，否则第 1 页筛剩 2 条也会停；命中 0 条时 NOTE 报出本次读到过的公众号名，空白名退 2。
  2. **`--dump DIR`**：每页原始 HTML 落盘（被拦页文件名带 `blocked_page`），供 `--fixture` 离线复现
     解析器。`dump_page` 返回 `(path, err)` 而不抛异常，写盘失败只打 NOTE——落盘是取证手段，
     不该让写盘成败决定搜索结果；写入用 `newline=""` 保持页面字节原样。
  3. **NOTE 进 `--format json`**：顶层新增 `notes` 数组，内容与 stderr 逐条一致。以前把 stdout 重定向
     落盘的调用方只看见 `count` 变小，读不到「为什么少这两条」。
  4. **响应字节上限**：`fetch` 原本 `r.read()` 一次读到底，等于把本机内存与挂钟交给页面对象决定。
     新增 `_read_capped`（64 KiB 分块、`MAX_BODY_BYTES = 4 MiB`、短读继续取而不当成读完、
     恰好读满上限时再多探 1 字节以免误报截断），超限置 `truncated` 并打 NOTE。
     实测正常结果页约 3.1 万字符，离上限差两个量级。
  5. **熔断后的状态字段**：`-r` 期间命中拦截，以前只有 item#k 带 `resolve_error`，后续条目四个还原字段
     全空，调用方读成「这些条还原失败了」，而实际是一次请求都没发。新增 `resolve_skipped`，
     text/md 各多一行「还原未尝试」，json 带字段；「没试」与「试了没成」在交付面分开。
  6. **拦截 NOTE 带本机时刻**：搜索页被拦与还原期熔断两处文案都落 `_stamp()` 的
     `YYYY-MM-DD HH:MM:SS`，「隔时重跑」的冷却起点从主观判断变成可比对的数。
- **`--fixture` 出口补齐处置建议**：以前只有联网路径打印处置建议，`--fixture` 筛到 0 条时静默退 1，
  离线路径的调用方拿不到下一步动作。抽出 `advice(window, account)` 供两条出口共用。
- **第 7/8 项按「先实测再决定」处理，两条都不落地**：复采 5 次请求（事先报过次数）——第 1 页两次
  逐字节相同（31243 字符），第 2 页直接命中 `antispider`（5266 字符拦截页），跨页重复因此**未判定**，
  没有依据做去重；早停阈值同样没有样本可定，且「税务」切片 4 处倒序/0.3 天、「公众号排版」切片
  3 处倒序/跨度 1204 天，单页内不能用「本页已变旧」判停，时间窗口继续翻满 10 页。
- **用例**：`tests/test_search_parser.py` 新增第 8–15 节（日期端点与非法输入、窗口闭区间与
  无时间戳丢弃、空窗口必须翻满 10 页、URL 里不得出现时间参数、`resolved_at`、
  哨兵三处变异、传输异常三态互斥、href 验域后拦下的条目零请求、
  403/429/503 与 500/网络抖动的归类互斥、`-r` 撞限流必须只请求 1 个 `/link`、还原三形态外域丢弃、
  而合法目标不误杀、非法 URL 与控制字符）；`evals/evals.json` 用例 10 的期望补到 10 条（含三态互斥、状态码归类、还原主机判定、`--account`/`--dump`/json `notes` 的交付口径），`--after`/`--before` 由
  `test_evals_routes.py` 核对确实在脚本里有声明。第四轮再加第 16–22 节（`_read_capped` 到顶截断与短读容忍、json `notes` 与 stderr 逐条一致且默认空数组、熔断后 1 条 `resolve_error` + 4 条 `resolve_skipped` 且不串态、两类拦截 NOTE 的时刻可被 `time.strptime` 解析、`filter_account` 四种口径加翻页停止条件、`--dump` 落盘字节与页面一致且写盘失败退为 NOTE、子进程 CLI 的 `--account`/`--format json`/空白 `--account` 退出码）。
- **验证**：`tests/run_all.py` 判据 8 个文件 0 失败；变异核验在隔离副本树逐处破坏实现，
  四轮共 34 处（6+6+8+14）全部被检出，每轮都另跑一个未变异的对照副本退 0。第一轮（功能新增）：哨兵整体失效、无时间戳改成保留、
  `--before` 不取 23:59:59、停页条件回退成看原始条数、窗口改成给搜狗加 `tsn`、还原不写
  `resolved_at`。第二轮（本轮缺陷修复）：删掉搜索页传输异常分支（`KeyError` 复现）、
  `safe_link` 不验域、拦下不落 `link_error`、`-r` 不跳过空链接、标记集去掉 `anti.min.css`、
  搜索 URL 加回 `tsn`。第三轮（状态码分家与还原主机判定）：`fetch` 不带 `http_status`、
  `block_reason` 的失败分支回退成一律不判、翻页循环回退成先判 error、`-r` 熔断条件回退成旧写法、
  `safe_mp_link` 回退成子串判定、形态二（meta refresh）绕过验主机、`_url_parts` 不回捕 `ValueError`、
  `_brief` 不剥控制字符。CLI 四条窗口路径实测
  退出码 0/1/2/2，变异页打印结构漂移 NOTE、真实切片 0 NOTE。第四轮（六项增补）：`_read_capped` 回退成一次读到底、短读当成读完、读满上限就一律报截断、`search()` 不写截断 NOTE、json 丢 `notes` 键、熔断后不给未尝试条目落 `resolve_skipped`、未发起请求被写成 `resolve_error`、搜索页被拦与还原熔断两处 NOTE 各去掉本机时刻、账号筛选改成大小写敏感、翻页停止条件不看筛选结果、`--dump` 不存被拦页、`dump_page` 写失败静默吞掉、`--fixture` 路径不给处置建议。
- **遗留**：上述七项「未判定」要等本机 IP 冷却后按判定纪律复采；票据存活时长、
  翻页之间的日期是否单调均无结论；结构哨兵只判数量关系，不判语义字段错位。跨页重复因第 2 页被拦仍未判定，去重与早停都等本机 IP 冷却后按同一纪律复采。

## 4.3.1（2026-10-17）description 去重整合 + 母/子技能职能边界重划 + 相对路径口径统一

本轮只动文档口径，不改任何接口行为与判据逻辑。

- **frontmatter 去重**：删除 `display_name`、`display_name_en`、`description_zh`、`description_en`
  四个字段，只留 `name` + `description` + `version`。删除理由是这四条内容与 `description`
  逐句重复（同一份能力清单与同一句发布结论写了两到三遍），不是宿主不认——实测本机
  `user_skills` 下另有 5 份 SKILL.md（tencent 系列用 `description_zh/en` 作双语短标签、
  点金百技图 claim-expert 系列用 `display_name` 作中文显示名）也在用这些字段，
  但它们的附加字段与 `description` 各有分工，本技能没有。
- **母/子技能职能边界重划**（母技能只留"跨子技能才需要"的内容）：
  - 路由表第三列由「覆盖能力」改为「该子技能负责的一件事」，一行一句，能力细则、
    命令、参数、验收判据全部只在对应子技能正文写一份。
  - 12 项辅助脚本清单改为按归属计数（`write/` 七支、`materials/` 两支、`read/` 与
    `search/` 各一支），逐项说明归子技能正文。
  - 「参数/内容硬约束」压成一句跨子技能口径（草稿标题取正文标题短句、完整标题放正文），
    约束表归 `draft/SKILL.md`、取值域归 `references/api-docs.md`。
  - 「发布」节只留一条判据（先 `check-perm`，`perm:false` 不重试转后台），发布前必设四项
    清单、固定话术、`perm:true` 才谈 freepublish、已发布结果核对口径整体移入
    `draft/SKILL.md`「制作→预览工作流」第 4 步。
  - 「公共排障」不再抄一遍错误码，只指向 `references/gotchas.md` 这份唯一清单。
  - 安全习惯第 2 条的闸口链只保留顺序与脚本路径，各闸查什么、怎么改归对应子技能。
- **五个子技能 description 重写**：各自收窄触发词并写明跨边界归属，消除与母技能及彼此的重复
  （draft 不再带正文 HTML 规范句、不再声明"做一篇公众号文章"触发；materials 的触发词收窄为
  上传/换 URL/批量配图/做封面，数值上限移出 description；Search 声明 type=1 账号搜索未封装；
  write/read/draft/materials 互指边界）。
- **数值口径回到唯一归属**（去重，不改判据）：`--title`/`--digest` 上限只在 `draft/SKILL.md`
  「参数约束」与 `references/api-docs.md` 出现，`write/references/writing-discipline.md` 的
  参数表改为只写内容侧写法 + 指针；正文图 1MB / 封面 10MB 的格式与阈值统一归
  `materials/SKILL.md`「图片限制」与 `references/api-docs.md`「官方限额」，
  `write/references/wx-html-rules.md`、`references/gotchas.md` C2 改为指针；
  `48001/53010` 的实测范围只在 `references/gotchas.md` A3，根「发布」节与 `draft/SKILL.md`
  第 4 步改为判据 + 指针；`45110` 从 `writing-discipline.md` 删除，凭据口径归根「凭据」。
- **目录名大小写按磁盘实写**：正文与 description 里的 `write/`、`search/` 三处改为 `write/`、
  `search/`，与本地目录逐字符一致；发布树的小写布局仍由 `sync_release.py` 的改写规则产生。
- **相对路径口径统一**：文中引用一律以技能目录为根。42 处 `../xxx` 写法改写
  （`../scripts/wx_api.py` 15 处、`../materials/` 5 处、`../references/gotchas.md` 4 处、
  `../SKILL.md` 4 处等）。改写后正文与脚本里剩下的 `../` 只有 5 处，全部是
  `../assets/xxx.png` 一类"本地相对路径微信端必不显示"的反例；CHANGELOG 历史条目按惯例不改写。
  母技能「目录与路由」里早已写明"相对路径均以本技能目录为根"，本轮是让正文与脚本真正按这句口径走。
- **验证**：`tests/run_all.py` 8 个判据文件 0 失败；23 个脚本 `compileall` 通过；
  以技能根为基准的引用 172 处全部可解析、0 处落空；六份 SKILL.md frontmatter 均可被
  PyYAML 解析且字段只剩 `name`/`description`（根多一个 `version`）；与 release 树
  （v4.3.0，cd20bc4）套用发布布局改写规则后逐文件比对，真实内容差异只落在本轮改动的文档。

## 4.3.0（2026-10-17）三道闸落地为代码 + 读取/搜索脚本化 + 判据测试体系 + 可分发整改

本轮把此前只写在文档里的验收要求变成脚本内建的强制步骤，并补齐读/搜两条链路的可执行入口。

- **推送侧三处闸口内建（P0）**：
  - `wx_draft_push.py` 用 importlib 复用 `write/scripts/validate_wx_html.py`，ERROR>0 直接
    `ERR PUSH_BLOCKED` 退出，先于取 token——带错正文不再可能进入网络环节。
  - `check_draft.py` 新增 `--source <article.html>`：回读 content 与源文件归一化后逐字比对
    （统一换行、剥 mmbiz 查询参数、去标签间与连续空白），未显式给 `--expect-imgs` 时图数预期
    由源文件 mmbiz 计数得出。改源文件未重推必 FAIL。
  - `wx_api.py` 的 `draft-update` 遇腾讯 WAF 501 自动「回读原封面 → delete → add」绕行，
    成功打印 `MEDIA_ID_CHANGED old=… new=… 请对新 id 重跑 check_draft.py`，失败打印
    `ERR BYPASS_FAILED` 并提示先 `draft-list` 实查；不传 `--cover` 时自动回读原 thumb 避免 40007。
- **新增 `write/scripts/qa_mobile.py`（渲染层验收）**：Playwright 以 390px 视口渲染，断言
  `scrollWidth <= 390` 并列出越界元素；用 computed style 枚举 `display:table*`/grid/flex 节点
  （伪表格在窄屏被压缩后 scrollWidth 仍为 390，只看溢出会漏判，故必须查计算样式）；报
  `naturalWidth==0` 破图与整页截图。table/grid 判 FAIL、flex 判 WARN。浏览器 fallback：
  msedge → chrome → Playwright 默认 Chromium。
- **新增 `search/scripts/search_wechat.py`**（纯标准库 urllib+re）：搜狗 `type=2` 关键词搜文章，
  UA 池轮换 + 首页 cookie 引导，分页上限 10、命中即停；`-n` 先截断再做跳转还原（避免整页还原打光
  `/link` 撞 antispider）；还原覆盖 302 Location、`<meta refresh>`、`url += '…'` 片段拼接三形态；
  命中 antispider/验证码/环境异常标记或被 302 回首页立即停手并打印处置建议。不传 tsn/ft/et（实测被 302）。
- **新增 `read/scripts/read_wechat.py`**：四层渐进式（Mobile UA → Desktop UA+Cookie → 完整浏览器头 →
  CDP），`success` 判据为「正文节点存在 + 无验证墙标记 + 字符数 ≥ `--min-chars`（默认 800）」，
  短文需标题/发布时间/正文节点三者齐备才豁免；输出 Markdown + frontmatter；CDP 序列与
  「响应循环读到 id 匹配」的坑按 `read/references/cdp-edge.md`。`--fixture` 支持离线回归。
- **新增 `write/scripts/build_blocks.py`**：由小 JSON 产出与 `write/references/theme-default.md` 逐字一致的正文片段，
  主题表由此变成机器核对的单一来源（见测试）。
- **`upload_imgs.py` 限额口径纠正（关键）**：正文图接口 `media/uploadimg` 官方口径是
  「jpg/png、大小必须在 1MB 以下」，10MB 是封面 `material/add_material` 的口径。上传前逐张
  `os.path.getsize` 预检，>1MB 直接 FAIL 并报出文件与字节数；文档同步改写（`materials/SKILL.md`、
  `references/api-docs.md`、`references/gotchas.md` C2）。
- **判据体系 `tests/`（8 个文件 + `run_all.py`）**：16 条 validate ERROR 规则各配命中 fixture；
  theme-default 九个组件与 build_blocks 逐字比对（改 md 不改脚本即红）；check_prose 翻案句
  硬翻案 7 + 变形 11 + 反向 5；qa_mobile/P0 闸口/读门/搜解析/evals 路由各有离线判据。
  变异核验一律在仓库副本树里跑，避免 `__pycache__` 陈旧字节码造成假绿。新增 `.gitignore`。
- **`evals/evals.json`**：10 条「用户话术 → 子技能与命令」路由用例（含「改标题重推这篇」走
  `draft-update` 而非 `draft-add`、发布走 check-perm + 后台手动等易错分叉）；
  `tests/test_evals_routes.py` 核对用例引用的路径存在、`--长选项` 在所引脚本里真有声明。
- **文档结构**：`write/SKILL.md` 拆出 `write/references/writing-discipline.md`（内容侧）与
  `write/references/wx-html-rules.md`（排版侧），SKILL.md 只留九步工作流主线与闸口顺序；
  `search/SKILL.md`、`read/SKILL.md` 按实测口径重写（参数表、质量门、降级层、反爬判定）；
  根 `SKILL.md` description 精简为功能/用途，细则下沉到正文与子技能。
- **可分发整改**：移除全部外部技能名与私有编号（板块号/文章号/系列品牌），`validate_wx_html.py`
  的许可来源说明改为中性表述（检查项清单参考自一个 AGPL-3.0 许可的外部同类工具，实现独立编写）；
  「本项目」表述改为「本技能/实测」；`references/api-docs.md` 逐条区分「官方页原文」与
  「官方页未列的经验值」；删除文档里以省略号拼出的不可访问 URL，改按官方文档章节名定位。
- **CLI 可用性**：`wx_api.py` / `wx_draft_push.py` / `check_draft.py` 均支持 `-h/--help` 打印用法即退出，
  不读凭据、不发请求（实测在 dummy 凭据下零网络尝试）；`wx_api.py` 未知子命令先于 token 请求报错，
  并移除不可达的兜底分支。
- **验证**：`python tests/run_all.py` 8 个判据文件全部通过；`env` shim（`~/.local/bin/env` 遮蔽 coreutils）
  导致的静默无输出问题已记录，改用 subprocess 捕获取证。

## 4.2.1（2026-09-28）去 AI 味措施与手段手册 + AI 启发式词表扩充

- **新增 write/references/de-ai-measures.md**（去 AI 味操作手册）：词汇层六类黑名单与改写思路
  （空洞评价/权威让步腔/路标总结/万能开头/万能结尾/模型黑话）、句式层十四种 AI 姿势（每条反例→正例）、
  结构层六特征与破解、内容层三类（假具体/假经历/说得比材料大）、检测工具链分层、按动作改写三步与冷读三问。
- **validate_wx_html.py**：AI_FLAVOR_PHRASES 由 20 词扩充至 50 词（万能开头/结尾、权威腔、路标总结、
  排比式抬价等），仍为 WARNING 级不阻断；py_compile 通过。
- **write/SKILL.md**：写作纪律第 2 条接入手册引用；根 SKILL.md 不变（check_prose 已在 4.2.0 登记）。
- 词表维护规则（写入手册第七节）：BANNED_WORDS / AI_FLAVOR_PHRASES / check_prose 硬禁词三处更新须同一轮进行。

## 4.2.0（2026-09-28）新增「活人感写作」非虚构整合参考 + check_prose 散文硬禁令检测

- **新增 write/references/human-writing-nonfiction.md**：整理自 KKKKhazix/human-writing v1.1.0（MIT）
  的非虚构写作相关内容——材料门槛（五件材料规则）、说话位置五问、局部问题推进、中文韵律、
  事实边界（reality 精要）、公众号文章体、改稿七遍（revision 精要）、成稿硬禁令完整清单
  （翻案腔动作表/黑话绝对禁词/语境词/抒情词）。虚构规则（fiction.md）未收录。
- **新增 write/scripts/check_prose.py**（自 human-writing 包 scripts/ 移入）：成稿散文硬禁令检测——
  翻案句（含变形）、黑话、硬停词、模型路标、破折号与提示性冒号；实测识别「不是A而是B」翻案句、
  赋能/商业闭环黑话、说白了/先说结论硬停词。与 validate_wx_html.py 互补（排版红线 vs 模型腔禁令），推送前都跑。
- **write/SKILL.md**：写作纪律新增第 7 条（散文质感）；推送前校验新增 check_prose 段与检查清单项；
  「与其他子技能的关系」移除已废弃的 publish 引用，改指后台手动发布。
- **根 SKILL.md**：辅助脚本清单补 check_prose.py。
- 原始资料包 write/references/human-writing/ 整合完毕后按要求移除（原仓库 MIT，来源见整合文档头部链接）。

## 4.1.0（2026-09-28）publish 子技能移除 · 发布知识并入母技能 · 排版主题通用化（可外发整改）

- **publish 子技能整体移除**：实测个人主体/未认证账号调用发布接口族（freepublish/submit|get|batchget|delete）
  一律返回 48001（2025-09 与 2026-09 两轮实测），子技能主体内容失效。有效内容并入：
  - 根 SKILL.md 新增「发布（个人未认证账号实测）」节：check-perm 权限探测、后台手动发布引导、
    「发布前四项后台手动设置」清单（开赞赏/声明原创/选择合集/创作来源 AI 生成，合集名按账号实际调整，
    不再绑定任何系列名）；draft/SKILL.md 第 4 步同步替换。
  - references/gotchas.md：保留 A3（48001/53010 接口族实测），删除 F1（发布状态码表，随接口失效）。
- **脚本清理**：删除 scripts/publish_status.py；wx_api.py 移除 publish/publish-get/publish-list/publish-delete
  四个子命令（保留 check-perm 权限探测）；py_compile 通过。
- **排版主题通用化**：write/references/theme-fasterp.md 更名 theme-default.md，去除系列品牌表述，
  改为「通用排版主题（默认主题）」；write/SKILL.md 四处引用同步；materials/gen_cover.py 去系列品牌。
- **母 SKILL.md 去个人化**：WECHAT_AUTHOR 示例值改为占位符；「FastERP 系列排版资产/封面生成器」
  表述改为通用表述；版本 4.0.5 -> 4.1.0。

## 4.0.5（2026-09-21）draft-add 作者字段 45110 修复（FastFPA 29 篇全链路实测）

全系列 29 篇教程推送实测发现并修复：

- **author 字段 45110 修复（关键 bug）**：`wx_api.py` 与 `wx_draft_push.py` 的默认作者名
  「数据舞者Ivy Notes」本身超过部分账号 author 字段长度上限，凡未配置 `WECHAT_AUTHOR`
  的用户 `draft-add` 必然报 `45110 author size out of limit`。修复：两脚本默认作者改为空，
  author 为空时**整体省略该字段**（不再发送）；docstring 与根 SKILL.md 同步更新。
  实测：配置 `WECHAT_AUTHOR` 后 29 篇全部推送成功。
- **SKILL.md 示例作者名**更新为实际使用值（4.5.0 起该姓名从本文件删除：个人姓名不是变更依据）。
- **实测确认可执行（2026-09-21，29 篇全链路）**：token / cover（永久素材）/ uploadimg（正文图
  换 mmbiz URL）/ draft-add / draft-get / draft-count / draft-list / draft-delete /
  check_draft（回读核验）/ validate_wx_html 全部按文档行为工作。
- **实测补充两条接口事实（已回写 FastFPA 教程写作纪律）**：
  1. `draft-list` 单页上限 20 条，批量对账须按 total_count 翻页，否则误判缺稿；
  2. `publish-list` 对未认证账号返回 48001，箱内草稿缺失无法经接口核实原因，
     重推前必须先与用户确认是否已在后台人工发布/删除（发布后草稿会离开草稿箱）。
- 本次 29 篇推送的媒体资产：封面 29 张（add_material 永久素材）+ 正文图约 60 张（uploadimg），
  均在官方限额内。


## 4.0.1（2026-09-18）清理无法执行的内容

按用户要求清理技能中无法执行/过时的内容，全部经实测验证：

- **命令路径修正（关键）**：`publish/SKILL.md` 能力表 5 处 `python wx_api.py ...`
  与 `draft/SKILL.md` 6 处、`materials/SKILL.md` 2 处 `python wx_api.py ...`
  统一为 `python ../scripts/wx_api.py ...`（此前在子技能目录下直接跑
  `wx_api.py` 会因文件不存在而无法执行；根目录/scripts 目录写法不受影响）。
- **去除外部技能依赖**：read/SKILL.md 原两处引用 browser-automation（含 browser4-cli / playwright-mcp）的连接方法已全部移除；新建 `read/references/cdp-edge.md` 将「读取 DevToolsActivePort 直连 WebSocket」方法搬运为技能内自包含文档（含禁止 Origin 头、帧 masked、 UUID 每次重启变化、HTTP 端点 404、CDP 消息 id 循环匹配等已验证细节）。 全技能外部技能引用扫描归零。
- **wx_api.py**：docstring `publish-delete <publish_id>` 修正为 `<article_id>`
  （官方接口 freepublish/delete 实收 article_id）；注释「gotchas 19」修正为
  「gotchas B5」（gotchas 已重组为 A–G 分组编号）。
- **read/SKILL.md**：依赖库标注 `beautifulsoup4` 为可选（本机未安装，
  缺失时降级 html.parser / 纯正则路径，实测降级链有效）；
  确认 browser-automation 技能与 playwright-mcp / Chrome-DevTools-MCP /
  browser4-cli 子技能存在，CDP 引用有效。
- **实测确认可执行**：10 个脚本 py_compile 全过；gen_cover 4 图案 +
  --help 正常；wrap_preview 生成预览页正常；upload_imgs --help / 快速失败正常；
  render_mermaid --help / 文件缺失快速失败正常（不启动浏览器）。
- **草稿箱现状**：实查 total_count=0（全部 67 篇已发布并清空）；
  publish 接口族仍 48001，发布核对以公众号后台为准。

## 4.0.0（2026-09-18）十二项改进全部落地

按用户拍板的 12 条建议全部实现并验证（草稿回读核验 / WAF 501 自动绕行 / 发布权限预探测 /
AI 味启发式 / 封面生成器入技能 / 批量上传 token 复用 / mermaid fallback / 发布状态台账联动 /
gotchas 主题重组 / 跨篇重复检测 / 发布不可逆确认 / 凭据泄露提醒）。

### 新增脚本（4 个）
- `scripts/check_draft.py` — 草稿回读自动核验：断言标题 ≤64B、摘要 ≤120 字符、thumb 非空、
  无 `<pre>`/`<style>`、mmbiz 图数=预期、无本地图片路径；`[PASS]/[FAIL]` 逐项输出，退出码 0/1；
  `--json` 结构化输出。
- `scripts/publish_status.py` — 发布状态台账联动：分页拉已发布文章（标题/URL/日期）→ 按标题
  子串匹配（≥4 字防误匹配）更新 xlsx 状态列「已发布 YYYY-MM-DD」；`--dry-run` 预览；修改前自动
  备份；48001 不改台账并说明。
- `materials/scripts/gen_cover.py` — FastERP 封面生成器入技能：4 种几何图案
  （layers/guard/grid/circuit），`--seed` 缺省随机保证每篇不同，`--size` 可调，纯几何无文字。
- `write/scripts/check_duplicates.py` — 跨篇重复段落检测：字符 4-gram Jaccard，跨文件相似段落
  报告，`--fail` 可阻断。

### 修改脚本（3 个）
- `scripts/wx_api.py`：
  - `draft-update` 遇 WAF 501（`non-JSON response`）自动绕行：回读原封面 → `draft-delete` →
    `draft-add`，返回新 media_id 并标注 `bypass:true`（gotchas B5 从人工绕行升级为自动）。
  - 新增 `check-perm` 子命令（只读探测发布接口权限）。
  - `publish` 必须 `--yes`（不可逆确认，缺省退出码 2）；执行前自动权限预探测
    （48001/53010 直接引导后台手动发布，退出码 3，不提交）。
- `write/scripts/validate_wx_html.py` — 新增 AI 味启发式（WARNING 级）：空洞修辞短语 22 个、
  正文感叹号 >3、最长段落 >120 字、段落平均 >80 字、「其一其二其三」「一是二是三是」编号排比；
  单测通过（命中组 7 项 WARN / 对照组零 AI 味误报）。
- `materials/scripts/upload_imgs.py` — 一次取 token 循环上传全部图片（不再逐张 subprocess 现取）；
  45009 自动退避重试（3s/6s/9s，最多 3 次）；复用 wx_api.py 的 get_token/multipart_upload。
- `write/scripts/render_mermaid.py` — 浏览器 fallback 链：msedge → chrome → Playwright 默认
  Chromium；全部不可用给出明确报错与 `playwright install chromium` 指引。

### 文档更新
- `references/gotchas.md` — 按主题重组：A 凭据与权限 / B 草稿推送 / C 正文与图片 /
  D 校验与写作 / E 环境与编码 / F 发布状态 / G 封面；新增 D3（AI 味启发式）；原 19 条编号改为
  主题编号（A1–G1），内容全部保留。
- 根 `SKILL.md` — version 3.1.0 → 4.0.0；description 补全新能力；辅助脚本清单更新；
  操作前安全习惯第 2 条改为「validate + check_draft 双校验」。
- `write/SKILL.md` — 校验章节加 AI 味 WARNING 与 check_duplicates；配图规范加 gen_cover.py
  与 mermaid fallback。
- `materials/SKILL.md` — 加 gen_cover.py 封面生成器、upload_imgs token 复用说明。
- `draft/SKILL.md` — 回读核验步骤改为 `check_draft.py`；能力表加 check_draft；501 自动绕行说明。
- `publish/SKILL.md` — 能力表加 check-perm / publish --yes / publish_status.py；工作流加权限
  预探测与台账联动步骤。

### 验证
- 全部 10 个脚本 py_compile 通过；check_draft/publish_status/gen_cover(4 pattern)/
  check_duplicates/validate(AI 味)/wx_api(501 分支) 均做功能单测或冒烟。
- gotchas 结构校验：A–G 七组、编号连续、D3 在 D 组内、内容 20 条无丢失。

## 3.3.2（2026-09-18）清除 Write 中 Markdown 相关内容

按用户要求删除 Write 子技能内所有涉及 Markdown 的内容，写作流程改为直接产出 wx 内联版 HTML（不存在 Markdown 中间产物）。

### 删除文件（4 个）
- `write/scripts/build_wx.py`（Markdown 母本 → wx 内联版 HTML 转换器）
- `write/scripts/fix_quotes.py`（Markdown 母本引号全角化）
- `write/scripts/extract_docx.py`（Word docx → Markdown 提取器）
- `write/references/format-normalize.md`（素材归一化：万物先转 Markdown）

### 修改文档（5 个）
- `write/SKILL.md`：删除「〇、素材归一化」节与「Markdown 母本 → wx 内联版」节；写作流程改为「直接写 wx 内联版 HTML，图片 URL 一步到位」；description 移除「素材归一化」。
- `write/references/theme-fasterp.md`：删除「映射规则（Markdown → 组件）」表，保留 HTML 组件库本体。
- 主 `SKILL.md`：辅助脚本列表移除 build_wx/fix_quotes/extract_docx；Write 行能力描述移除「素材归一化」。
- `references/gotchas.md`：删除第 15 条「转换器路径」；重编号 16–20 → 15–19；改写 `<div>` WARN 说明与 mmbiz-map 条目中的 build_wx 引用（改为「写作排版按图名查 URL」）；顺带清除 79/80 行历史混入的 / 控制字符。
- `materials/scripts/upload_imgs.py`：两处注释移除 build_wx 引用。

### 验证
- 全技能扫描 `build_wx|fix_quotes|extract_docx|format-normalize|母本` 残留为 0；gotchas 条目编号连续 1–19；剩余脚本 py_compile 全部通过。

## 3.3.1（2026-09-18）板块九复核修复

板块九三篇（0066/0067/0069）反复核实查验，逐段与 FastERP 仓库源码对照；每篇新增 1 张配图（快照构成 / SSE 时序 / 三条红线），修复 6 类内容问题，升级 fix_quotes 保护行内代码。

### 修复 1：fix_quotes.py 误全角化行内代码引号（脚本层）
- 现象：已推送草稿的行内代码出现弯引号，如 `json.loads(chunk[6:]).get(“token”)`、`if provider in (“xai”, “openai”)`，不符合 Python 语法观感。
- 本质：fix_quotes 只跳过 ``` 代码块，行内代码 `...` 内的英文引号被正则 `"([^"]*)"` 一并全角化。
- 解决：升级 fix_quotes.py——先用 ``(`[^`]*`)`` 拆出行内代码段，只全角化非代码部分；三篇母本中 6 处已误全角化的行内代码引号手动改回半角。
- 验证：重建后 validate ERROR=0，draft-get 回读行内代码引号为半角。

### 修复 2：内容核实修正 6 处（写作层）
- 0066：“四个函数”与标题“三个聚合函数”矛盾 → 改“三个函数，三层聚合”；“客户欠我们多少钱”含人称 → 改“客户欠了多少钱”；“只做一件事”表述不精确 → 改“主要动作只有一个”；时效段逻辑绕 → 重写为“快照只在提问的瞬间计算”。
- 0067：开篇虚构金额举例（84,920/85,000）→ 改为不出现具体数字的表述。
- 0069：“每一问一答都有时间戳”补充依据——SQLite 分支 INSERT 显式写入 `datetime('now')`（db.py 第 169–170 行）。

### 修复 3：PowerShell Set-Content 编码损坏母本（流程警示）
- 现象：0067/0069 母本经 PowerShell `Set-Content -Encoding utf8` 写回后变为 0 字节。
- 本质：PowerShell 5.1 的 Set-Content 数组写回与编码处理不可靠，且去 BOM 逻辑叠加后数据全失。
- 解决：母本重建改用 Write 工具（UTF-8 直接写入），文件写回一律走 Python `open(p,'w',encoding='utf-8')`，不再使用 PowerShell Set-Content 写中文内容。
- 固化：写作流程要求母本创建/修改只用 Write 工具或 Python，禁止 PowerShell Set-Content。

### 图片增强
- 每篇新增 1 张 mermaid 渲染配图（与既有图同配色：金 #B08D3E 边框、深蓝 #1F3864 文字）：0066 快照构成（1484×119）、0067 SSE 时序图（1484×624）、0069 三条红线（1484×874）。
- 三张新图 uploadimg 换 mmbiz URL 后写入对应 map JSON（各 2 条）；三篇重建 validate ERROR=0；draft-update 重推（带原封面）全部 errcode 0；draft-get 回读核验：标题/摘要/封面齐全、正文 mmbiz 图×2、无 <pre>、行内代码引号半角。
- 板块九目录三篇 HTML 已更新为双图版并经 inline_images 全量内联（0 miss、0 残留 http 引用），assets 目录已清理。

## 3.2.2（2026-09-17）板块七复核修复

板块七三篇（0055/0057/0059）反复核实查验，逐段与 FastERP 仓库源码对照；按用户要求删除母本内 mermaid 源码块（只保留渲染图引用）。
### 修复 1：draft-update 被腾讯 WAF 501 拦截，绕行 delete+add（流程层）
- 现象：0055 最终版 `draft-update` 连续三次返回 `{"errcode":501,"errmsg":"non-JSON response"}`（raw 为 `waf.tencent.com/501page.html`），退避 20s/60s 重试均无效；同批 0057 draft-update 成功、0055 的 draft-get 正常。
- 本质：腾讯网关对特定草稿的 `draft/update` 写请求（约 47KB）做风控拦截，与重试次数无关。
- 解决：`draft-delete` 旧草稿 + `draft-add` 新草稿（同标题/摘要/封面），新 media_id 内容一致。delete/add 实测不受拦截。
- 固化：`references/gotchas.md` 新增第 20 条。
### 修复 2：母本 mermaid 源码块移除（写作层）
- 现象：母本中 ```mermaid 代码块经 build_wx 落入 wx 内联版，公众号编辑器粘贴路径下会显示源码文本而非渲染图。
- 解决：按用户指示，母本只保留 `![图注](assets/fig/xxx.png)` 渲染图引用，mermaid 块从母本删除；.mmd 源文件与渲染脚本仍留存于板块 assets/fig/ 供复现。
- 验证：三篇重建后 validate 全部 ERROR=0（0059 改写一处正文半角引号触发行后 WARNING 清零），draft-get 回读无 flowchart/graph 残留、mmbiz 图×2、封面/标题/摘要齐全。

板块二四篇（0010/0011/0014/0015）反复核实查验，逐段与 FastERP 仓库源码对照。

### 修复 1：draft-update 不带 --cover 返回 40007（wx_api.py）
- 现象：0011 母本修正后 `draft-update` 重推，返回 `{"errcode":40007,"errmsg":"invalid media_id"}`；`draft-get` 同一 media_id 完全正常。手动携带原封面 thumb 后 `errcode 0`。
- 本质：`draft/update` 要求 `articles.thumb_media_id` 为有效素材 id——省略或空串均判 40007，报错文案误导为 media_id 无效。先前 `build_article` 在空封面时省略该键，仍失败。
- 解决：`draft-update` 未传 `--cover` 时先 `draft-get` 回读原 `thumb_media_id` 再构建 article；`article` 构建移到 thumb 解析之后（先构建后回读仍带空封面）。脚本路径验证 `errcode 0`。
- `references/gotchas.md` 新增第 19 条。

### 修复 2：0011 母本令牌签发代码块改为真实逐行形态（写作层面）
- 现象：0011 第三节「隐式的上下文管理」代码块为拼接形态（`with self._db() as db:` 下平铺 `_issue_token` 的 DELETE+INSERT SQL），与真实源码 `_issue_token(self, db, ...)`（db 为调用方传入的参数）不一致。
- 解决：改为 forgot 的真实逐行形态（`with self._db() as db:` 内 SELECT 校验 + `_issue_token(db, row["id"], "reset", 3600)` 调用），正文说明 `with sqlite3.connect(...)` 的 commit/rollback 语义与 `_issue_token` 内部两条写操作。
- 验证：build_wx → validate ERROR=0 → draft-update 重推 `errcode 0` → draft-get 回读标题/摘要/封面/正文 mmbiz 图 ×2/代码块新形态全部合格。

## 3.1.0（2026-09-17）板块八实战检验修复

板块八 4 篇（0060/0062/0063/0064）写作推送全链路实测，发现并修复：

### 修复 1：Markdown 母本转换器缺失（最大缺口）
- 现象：新板块首次构建时 `build_wx.py`/`fix_quotes.py` 不存在于技能内，只能从板块六 assets 复制；技能文档写着"可先写 Markdown 母本再转 wx 内联版"，但转换器本身不是技能资产，散落各板块。
- 本质：方法描述与工具资产分离——规范承诺的能力没有对应的可复用实现。
- 解决：`build_wx.py`（母本 → wx 内联版，theme-fasterp 组件）与 `fix_quotes.py`（正文引号全角化）纳入 `write/scripts/`；`write/SKILL.md` 新增「Markdown 母本 → wx 内联版（转换器，首选路径）」小节与流程第 5 步转换器路径；根 SKILL.md 辅助脚本清单补齐。

### 修复 2：装饰线 `<div>` → `<section>`（WARN 清零）
- 现象：`validate_wx_html.py` 每篇报 1 处 `<div>` WARN，来源是 `build_wx.py` 的 `P_LINE` 装饰线。
- 本质：历史产物用 `<div>`（API 路径实测可用），但新产物可完全避免——`<section>` 默认 display:block，样式与 `<div>` 一致，两条推送路径都安全。
- 解决：技能内 `build_wx.py` 的 `P_LINE` 改为 `<section>`；板块八 4 篇 wx 产物重建后校验 WARN 清零（已推送草稿保持原状，`<div>` 在 API 路径安全，不重推）。

### 修复 3：`draft-get` 输出 BOM 陷阱
- 现象：PowerShell `Out-File -Encoding utf8` 写 BOM，`json.load` 报 `Unexpected UTF-8 BOM`。
- 本质：调用侧编码问题，非技能脚本缺陷。
- 解决：`references/gotchas.md` 新增第 16 条（draft-get 输出用 `utf-8-sig` 读或 `utf8NoBOM` 写）。

### 修复 4：转换器用法文档化
- `references/gotchas.md` 新增第 15 条（转换器路径：fix_quotes → upload_imgs → build_wx → 校验 → 推送；母本无 BOM 要求）。

## 3.0.3（2026-09-17）板块六实战检验修复

> **许可合规说明（AGPL-3.0）**：`write/scripts/extract_docx.py` 逐字移植自
> gzh-design-skill（AGPL-3.0，作者 甲木 × 摸鱼小李）；`validate_wx_html.py`、
> `wrap_preview.py`、`format-normalize.md` 借鉴其方法体系。上述文件均已标注
> 来源与许可。本技能如对外分发，涉及这些文件的部分须遵循 AGPL-3.0 开源。
> 源技能 gzh-design-skill 已于 2026-09-17 移入
> `fasterp_ledger_backup\gzh-design-skill\`（保留备查）。

### 修复 6：validate_wx_html.py 对英文词内撇号误报
- 现象：0048 正文含科目名 Owner\'s Equity，校验器 ASCII_QUOTE 将撇号判为半角直引号，误报 WARNING。
- 本质：ASCII 单引号检测未区分「英文所有格撇号」与「中文语境直引号」。
- 解决：新增 APOSTROPHE_WORD（[A-Za-z]'\w 等），检测前先剔除英文词内撇号；0047/0048 均回归通过。
## 3.0.2（2026-09-17）板块六实战再修复

### 修复 3：`wx_api.py` http_json 对非 JSON 错误响应崩溃
- 现象：`draft-update` 返回 501（腾讯 WAF 拦截页，HTML 而非 JSON），`json.loads` 直接抛 `JSONDecodeError`，真实错误被吞。
- 本质：错误路径只假设"永远是微信 JSON 错误体"，遇到网关/防火墙 HTML 页就崩。
- 解决：HTTPError 分支先尝试解析 JSON，失败则返回 `{"errcode": code, "errmsg": "non-JSON response", "raw": ...}` 供诊断。

### 修复 4：`upload_imgs.py` `--map` 覆盖写丢失旧映射
- 现象：先传流程图生成 map，再传封面 `--map` 同文件，旧映射被整份覆盖，HTML 里流程图退回本地路径。
- 解决：写 map 前先读已有文件合并，只增不覆盖。

### 修复 5（转换器侧，非技能）：md 母本 BOM 导致标题降级为正文
- 现象：草稿正文顶部显示「# 复式记账：一张凭证为什么必须记两笔」而非标题样式。
- 根因：PowerShell `Set-Content -Encoding utf8` 写入 BOM，build_wx.py 的 `startswith("# ")` 匹配失败，标题行落入正文段。
- 解决：build_wx.py 以 `utf-8-sig` 读母本并 `lstrip("\ufeff")`；正文顶部按公众号惯例加封面头图（mmbiz）。

## 3.0.1（2026-09-17）板块六实战检验修复

板块六第 1 篇（0047 复式记账原理）写作与推送全链路实测，发现并修复：

### 修复 1：`<div>` 标签级别三处矛盾统一
- 现象：`write/SKILL.md` 红线节与校验说明节仍写「禁止 `<div>`」，而校验器实测 `<div>` 为 WARN（API 推送路径不清洗、板块五已发布文章在用），且 `theme-fasterp.md` 组件 2 装饰线正是 `<div>`——技能内部三处互相矛盾。
- 本质：规范文本滞后于校验器实现与真实产物。
- 解决：`write/SKILL.md` 两处、`theme-fasterp.md`「与校验的关系」节统一为「`<div>` WARN 级、能用 `<section>` 用 `<section>`」。

### 修复 2：`upload_imgs.py` 的 WX 路径指向不存在的文件
- 现象：批量上传 `FAIL fig6-1-events.png`，而直接调 `scripts/wx_api.py uploadimg` 成功。
- 根因：`upload_imgs.py` 内 `WX = 同目录/wx_api.py`，但 `wx_api.py` 实际在技能根 `scripts/`（`materials/scripts/` 下只有 upload_imgs.py）。
- 解决：WX 改为三级上级目录拼接 `scripts/wx_api.py`；修复后批量上传成功。

## 3.0.0（2026-09-17）全面重构（批判后完善）

依据对技能的批判与 gzh-design-skill 借鉴，完成以下变更：

### 身份与结构
- **frontmatter `name` 由 `wechat-mp-api` 改为 `wechat-article`**，display_name 改为「微信公众号文章（写作·排版·草稿·发布）」——名实相符。
- 主 SKILL.md 收敛为纯入口：身份、路由、凭据、统一 CLI、公共排障、三条安全习惯；批量发布/状态码/四项后台设置等工作流全部归位到 `publish/`（原本分散在主 SKILL）。
- 正文 HTML 约束唯一权威定义收敛到 `write/SKILL.md`，`draft/` 与 `references/gotchas.md` 改为引用（消除三处重复维护）。

### 新增能力（借鉴 gzh-design-skill）
- `write/scripts/validate_wx_html.py` — 确定性合规校验器（API 推送路径版）：禁标签/属性、图片必须 mmbiz 域名、纯 section 片段、禁用词、半角标点；ERROR=0 才可推送。把「推送前检查清单」从模型自觉变为确定性兜底。
  - **实现要点（实测校准）**：样式红线只检查元素 `style` 属性（代码块文本里的 CSS 示例不算违规——FastERP 文章常展示 `.app{display:grid;var(--rail)}` 这类代码）；`<code>` 标签计入代码区（行内代码的半角符号不误报）；`<div>` 实测 API 推送不清洗、显示正常（板块五已发布文章在用），降为 WARN 并注明编辑器粘贴路径会被改写。
  - 双向验证：0035 mmbiz 版（已推送）→ ERROR=0；0042 旧版（本地路径）→ 检出 3 处图片 ERROR。
- `write/references/theme-fasterp.md` — FastERP 系列排版资产（从板块五已发布文章 `push_tmp/*-mmbiz.html` 逐条提取，样式与产物逐字一致）：主色深蓝 #1F3864 + 金 #B08D3E，9 个已验证组件 + 映射规则 + 系列约定。装饰线组件按真实产物为 `<div>`（API 路径实测可用）。
- `write/scripts/wrap_preview.py` — 推送前本地预览页（模拟公众号阅读 + 一键复制）。
- `write/scripts/extract_docx.py` + `write/references/format-normalize.md` — 素材归一化（docx/pdf/纯文本/网页 → Markdown），移植自 gzh-design-skill（零依赖）。
- `read/`、`search/` 增加脆弱性标注（外部路径可能随平台改版失效，使用前即时验证）。
- `git init` + 本 CHANGELOG：技能迭代可追溯。

### 既有能力保留
- `scripts/wx_api.py`（13 子命令）、`scripts/wx_draft_push.py`、`materials/scripts/upload_imgs.py`、`write/scripts/render_mermaid.py`。
- 六子技能路由、凭据安全、发布前四项后台设置、48001 发布权限实测结论。

## 2.1.1（2026-09-17）
- 撤销 `Verify/` 子技能（借鉴来源 web-app-function-test 被用户更正为误引用）；路由表回退为 6 子技能。

## 2.1.0（2026-09-17）
- 纳入 `wx_draft_push.py` 为简易推送脚本；新增 `write/` 子技能（写作纪律 + wx 内联版 HTML 硬规范）。

## 2.0.0（2026-09-17）
- 全面完善：新增 `write/`（首版）、`read/`、`search/` 子技能；publish 状态码全表、48001 实测结论、批量按序发布工作流；gotchas 扩至 13 条；wx_api.py 增加 `--full`/`--source-url`。
## 3.2.0（2026-09-17）板块二实战检验修复

板块二 4 篇（0010/0011/0014/0015）写作推送全链路实测，发现并修复：

### 修复 1：upload_imgs --map 键为绝对路径，build_wx 匹配失败（本轮最大问题）
- 现象：0010 首次 validate 报 3 处图片 ERROR（ssets/fig/xxx.png 本地路径未替换为 mmbiz URL）。
- 本质：两个脚本的键约定不一致——upload_imgs.py 用 os.path.normpath 绝对路径作 map 键（含非 ASCII 时控制台显示乱码），uild_wx.py 匹配逻辑 mmbiz.get(src) or mmbiz.get(os.path.basename(src)) 只认相对路径/basename，绝对路径键永远匹配不上。
- 解决：upload_imgs.py 写 map 时键统一为 os.path.basename(p)（3.2.0 起新产物直接正确）；旧 map 需重建（basename 键）；write/SKILL.md 转换器段标注 map 键约定；
eferences/gotchas.md 新增第 17 条。
- 验证：0010 重建后 ERROR=0；四篇推送后 draft-get 正文 mmbiz 图数 = 配图数（每篇 2 张）。

### 修复 2：draft/materials 子技能 wx_api.py 路径引用失效
- 现象：按 draft/SKILL.md 的 scripts/wx_api.py 执行报「路径不存在」——脚本实际在技能根 scripts/。
- 本质：3.0.0 重构将 wx_api.py 提到根 scripts/，子技能文档路径引用未同步（3.0.1 只修了 upload_imgs.py 内部 WX 拼接，没修文档）。
- 解决：draft/SKILL.md、materials/SKILL.md 内 scripts/wx_api.py 全部改为 ../scripts/wx_api.py。

### 修复 3：validate 禁用词命中「首先」的替代表达沉淀
- 现象：0011 正文「它首先是文档」命中禁用词扫描 ERROR。
- 本质：写作纪律禁用词与表达习惯冲突，需要可用替代表达而非只能改写。
- 解决：
eferences/gotchas.md 新增第 18 条（禁用词替代表达清单，「首先→第一身份/一方面」等实测替换）。

### 补充：板块二 4 篇全链路产物与台账
- 0010/0011/0014/0015 母本 + mermaid 配图（1484px）+ 几何封面（每篇唯一 seed）+ wx 内联版（validate ERROR=0）+ 已推送草稿并回读核验（标题/摘要/封面/正文图/代码块结构齐全）。
- 台账 FastERP_82篇教程台账-最终版.xlsx 板块二 4 行状态与标题已同步。

## 3.2.1（2026-09-18）板块十实战修复：validate class/id 误报代码块文本
### 修复：validate_wx_html.py class/id 属性检查误伤代码块文本
- 现象：0088 正文含 SQL `WHERE id=?`、Python `row["id"]`，validate 报「id 属性会被剥离（命中 1 处）」ERROR。
- 本质：标签级检查的 `\sid\s*=` / `\sclass\s*=` 是全文宽松正则；代码块文本经 build_wx 转义（`<`→`&lt;`、空格→`&nbsp;`）后仍保留 `id=`/`class=` 字样，宽松正则无法区分「真实标签属性」与「代码文本」，而样式级红线（FORBIDDEN_STYLES）已豁免代码块、属性检查未豁免——两条检查的豁免口径不一致。
- 解决：class/id 检查正则限定为「真实标签内」：`<[a-z][^>]*\sclass\s*=` 与 `<[a-z][^>]*\sid\s*=`（代码块内不可能出现 `<标签` 形态，因 `<` 已转义）。
- 验证：0088 重跑 validate ERROR=0；含 `WHERE id=?` 的 0087 复跑同样 ERROR=0（回归通过）。

## 3.3.0（2026-09-18）板块九实战检验修复

板块九三篇（0066 先算账再说话 / 0067 斜杠命令与 SSE / 0069 提示词与安全）写作推送全链路实测。本次重点为技能体检：清理垃圾文件、核对 validate 机制、验证内联收尾。

### 修复 1：根目录 4 个垃圾文件清理（技能维护）
- 现象：技能根目录存在 `--help`（一个 PNG 误存 116.3KB）、`多公司：company_id 贯穿与按公司隔离`（33B 截断文件）、`扩展点与自研 ERP：注册机制与规模边界`（40.5KB）、`系统架构与分层：单向依赖与不可变账本`（39.4KB，后两者为板块十文章副本）。
- 本质：历史误写与板块产物误落技能根，非运行必需。
- 解决：4 个文件全部删除；技能现 21 文件 9 脚本，`py_compile` 全过。

### 修复 2：validate 禁词规则误伤内容性表述（写作层，0069）
- 现象：0069 母本"回答边界在最后，因为它是总闸"命中禁词 `最后，`，validate ERROR=1。
- 本质：规则设计为拦截连接词"最后，"，但内容性表述"在最后，因为"同样触发；属规则的字面匹配边界，非缺陷。
- 解决：改写为"回答边界排在末位"，validate ERROR=0。沉淀：母本中一切"在最后/首先/其次"式内容表述都应避开字面组合。

### 修复 3：板块九收尾内联与清理（流程验证）
- 现象：新板块三篇 wx 产物在 work 区，Tutorial 板块九目录为空。
- 解决：按既有收尾流程——wx HTML 落入板块目录 → `inline_images.py` 全目录内联（本次全 Tutorial 134 图 map=3 dl=0 miss=0，板块九三篇 dataURI 内联无 mmbiz 残留）→ 删除板块 assets。
- 验证：板块九目录仅存 0066/0067/0069 三个自包含 HTML。

### 已推送草稿（三篇均 draft-get 回读核验通过）
- 0066 先算账，再说话：FastERP 的 AI 助手与快照问答
- 0067 不接大模型也能问账：斜杠命令与 SSE 打字机
- 0069 系统提示词的四句话与三条红线：数据不出边界
- 每篇：标题≤64 字节、摘要≤120 字符、封面独立（guard/layers 几何图）、正文 mmbiz 配图×1、无 <pre>、validate ERROR=0。

## 4.0.2（2026-09-19）表格红线与架构文章修复

0088《系统架构与分层设计》发布后实测发现两个问题，修复并沉淀为技能规则：

- **新增 `<table>` 红线（ERROR 级）**：0088 用 `<table>` 排"四层结构职责表"，微信手机端整表不渲染、表格消失——与 `<pre>` 同类，属微信编辑器不支持标签。`write/scripts/validate_wx_html.py` 的 FORBIDDEN_TAGS 增加 `<table>` 检查；`write/SKILL.md` 原「简单表格用 `<table>`」的错误建议改为**禁止 `<table>`、一律用 div + display:table 伪表格**，并新增可直接套用的「表格模板」小节；`display:flex` 降为 WARN 级（微信部分机型异常，多列优先 display:table-cell）；主 SKILL.md 描述与路由表同步更新。
- **0088 内容补齐（写作文档同步确认）**：0088 标题承诺「关注点分离、高内聚低耦合」但正文 0 处展开——修复版补入三段论证：模块化设计与关注点分离（四层职责的软件工程命名）、业务域维度模块化（fasterp/ 五个服务类）、高内聚与低耦合度量（db.py 数据收敛 + 窄接口单向依赖），素材全部取自 AGENTS.md 原文与仓库目录结构。
- **0088 修复版重推**：表格转 div 伪表格 + 补内容后，母本已同步更新；解码内联图重传 mmbiz（0088-img-1/2 → mmbiz_map_0088.json）；新草稿 media_id=yEeJgNlLG2-6CUjvfN_kX9wn_4L0LEazsQ6jDoPrrAjQqb6Em2nl4gce21env2WM，check_draft 全 PASS。已发布旧版不可编辑，需删除旧文重新发布。

## 4.0.3（2026-09-19）产物形态改为 mmbiz 单版本优先

用户质疑「何必两个版本并存」：双版本（base64 存档版 + mmbiz 推送版）源自早期一次「图像全部内联」的历史指令，非写作常态。经确认改为：

- **单版本优先**：正式产物只有一个 mmbiz 推送版（写作时一步到位直接引用 uploadimg URL）；base64 内联版降为「用户明确要求离线归档时才生成」的可选动作，不作双份维护。
- write/SKILL.md「〇、产物形态」一节重写；存量 base64 存档版保留现状，重新推送时才走「解码→uploadimg→替换」一次性转换。

## 4.0.4（2026-09-19）div 伪表格红线化，表格改条目卡片

0088 表格问题两次实测打脸，沉淀为规则：

- **问题链条**：`<table>` 微信端整表不渲染（4.0.2 已加 ERROR 红线）→ 改用 div + `display:table` 伪表格 → 微信预览端仍堆叠成纯文本。结论：`display:table/table-cell` 在微信渲染不可靠，div 伪表格不成立。
- **新规则**：表格一律用「条目卡片」——每条一个 `<section>`（浅灰底 #F7F8FA + 金左边框 #B08D3E + 条目名加粗深蓝 + 说明行灰字），纯块级布局微信 100% 稳定；列多必须保持行列结构的渲染成图片。write/SKILL.md 红线段、表格模板、正文排版、检查清单、主 SKILL.md 路由表全部同步。
- **0088 已修复**：四层职责表替换为 4 张条目卡片，validate ERROR=0，草稿重推（WAF501 自动 delete+add 绕行）。

## 4.0.5（2026-09-19）全面检验：脚本与文档对齐、伪表格确定性兜底

对六个子技能 + 主 SKILL.md + 全部脚本交叉核对，发现问题并修复：

- **版本号不同步**：主 SKILL.md version 停在 4.0.2，CHANGELOG 已到 4.0.4 → 升至 4.0.4（本轮再记 4.0.5）。
- **validate_wx_html.py 与 4.0.4 文档冲突**：`<table>`/`display:grid`/`display:flex` 的报错文案仍推荐"div 伪表格"（已废弃路线）→ 文案全部改为「条目卡片或渲染成图片」。
- **实现缺失**：文档承诺"无 div 伪表格（自动）"但脚本不查 display:table → 新增 `display:table/table-cell/table-row/table-column` ERROR 红线（实测三样本：伪表格 ERROR、table 标签 ERROR、代码块"本文"不误报）。
- **禁用词误报风险**：BANNED_WORDS 原来直接全文子串匹配，代码块注释里的"本文"会误报 ERROR → 改为只查非代码区正文（checker.texts），实测代码块含"本文"通过。
- **check_draft.py 缺伪表格回读**：回读层不查 display:table → 新增「无 div 伪表格」检查项 + summary 字段 + 摘要行显示；0088 实跑 PASS（伪表格×0）。
- 全技能扫描确认无过时表述残留（剩余命中均为禁令记录本身）。
