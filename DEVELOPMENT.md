# zcode-server-centos7 开发设计文档

> 历史范围说明：本文保留 `0.1.x` 旧版固定 `~/.zcode/server/node` 布局的设计，
> 不适用于 `0.2.0` 的 Source Server 流程。旧版使用方法见[旧版指南](docs/LEGACY.md)；
> 当前 0.2.1 稳定版适配 ZCode 3.16.3，用法见 [README](README.md)，验证记录见
> [3.16.3 兼容性文档](docs/ZCODE_3_16_3_COMPATIBILITY.md)。
> 0.2.0 稳定版的技术方案与验收边界见
> [3.16.2 Source Server 兼容性文档](docs/ZCODE_3_16_2_COMPATIBILITY_PLAN.md)。
> 当前适配、发版与恢复流程见[升级与兼容策略](docs/UPGRADE_POLICY.md)。

## 1. 文档目的

本文档定义 `zcode-server-centos7` 的开发范围、技术方案、安全边界、测试策略和验收标准。

本工具只解决一件事：让 CentOS 7 上由 Zcode Windows 客户端直接启动的 `~/.zcode/server/node` 能够使用一套用户目录内的兼容运行库启动，从而解决 `GLIBC_*`、`GLIBCXX_*` 和 `CXXABI_*` 版本缺失问题。

工具不得改变其他任务、其他用户或系统程序的运行环境。

## 2. 背景与问题定义

CentOS 7 通常提供：

- glibc 2.17；
- GCC 4.8 对应的旧版 `libstdc++.so.6`；
- Linux kernel 3.10 系列。

Zcode 部署到远程服务器的 Node.js 位于：

```text
~/.zcode/server/node
```

当前 Node.js 至少需要：

```text
GLIBC_2.25
GLIBC_2.27
GLIBC_2.28
GLIBCXX_3.4.20
GLIBCXX_3.4.21
CXXABI_1.3.9
```

因此该二进制无法由 CentOS 7 的系统动态加载器和运行库直接启动，Zcode 在输出握手消息前即退出。

## 3. 核心原则

### 3.1 只影响 Zcode

兼容层的作用范围必须严格限制在：

```text
~/.zcode/server/node
```

允许修改或创建的运行时文件只能位于：

```text
~/.zcode/server/node
~/.zcode/centos7-runtime/
~/.zcode/centos7-runtime/backups/
~/.zcode/centos7-runtime/state.json
```

除非用户显式指定测试目录，否则工具不得扫描、修改或包装其他 Node.js、Python、Git、Shell、编辑器服务器或用户任务。

### 3.2 不修改系统环境

严禁执行以下操作：

- 替换或修改 `/lib64`、`/usr/lib64`、`/lib`、`/usr/lib` 中的任何文件；
- 通过 RPM/YUM 升级系统 glibc；
- 修改 `/etc/ld.so.conf` 或运行 `ldconfig` 安装私有运行库；
- 修改 `.bashrc`、`.bash_profile`、`.profile`、SSH 配置或系统环境变量；
- 全局或持久化设置 `LD_LIBRARY_PATH`、`LD_PRELOAD`；
- 在 `$PATH` 中放置冒充系统 `node`、`bash`、`git` 等命令的文件；
- 对 `~/.zcode/server` 进行递归 ELF 补丁；
- 修改 Zcode 的 JavaScript/CJS 业务代码。

### 3.3 不向子任务传播兼容环境

私有 glibc 和 libstdc++ 只能通过目标 Node ELF 的私有解释器生效，不能通过环境变量传播。经验证的加载器必须从自身目录解析配套 GNU 运行库；工具不得给目标 Node 新增或修改 RPATH/RUNPATH。

Zcode 中执行的 `/bin/bash`、`git`、`ls`、编译任务和用户脚本必须继续使用系统原生动态加载器及其各自的运行库。

### 3.4 可恢复、可重复、可审计

所有安装操作必须：

- 在变更前保存原始文件及 SHA256；
- 先生成临时文件并完成验证，再原子替换目标；
- 重复执行时保持幂等；
- 状态不明确时拒绝覆盖；
- 支持恢复到字节完全一致的原始 Node；
- 将工具自身的状态记录在独立清单中。

## 4. 范围与非目标

### 4.1 第一版范围

- 操作系统：CentOS 7 / RHEL 7 兼容系统；
- CPU 架构：`x86_64`；
- 目标：`~/.zcode/server/node`；
- 私有运行库：glibc 2.28 及满足目标 Node ABI 的 libstdc++/libgcc；
- 功能：检查、安装、状态查询、验证、修复和卸载；
- 安装权限：普通用户，无 root 权限；
- Zcode 连接方式：Windows 客户端通过 SSH 启动远端 Node。

### 4.2 第一版非目标

- 不为任意 Node.js 或任意应用提供通用 CentOS 7 兼容层；
- 不补丁 Zcode 扩展、用户插件或其他 ELF 文件；
- 不接管 Zcode 更新器；
- 不阻止 Zcode 覆盖或更新 Node；
- 不使用常驻守护进程监控文件；
- 不使用 `chattr +i` 锁定 Zcode 文件；
- 不支持 ARM、ARM64 或 32 位平台；
- 不重新分发 Zcode Server、Zcode Node.js 或其他 Zcode 专有文件。

## 5. 推荐架构

### 5.1 运行链

安装前：

```text
Windows Zcode
    -> SSH
    -> ~/.zcode/server/node
    -> CentOS 7 系统加载器
    -> ABI 版本不足，握手前退出
```

安装后：

```text
Windows Zcode
    -> SSH
    -> ~/.zcode/server/node（仅此 ELF 被定向）
    -> ~/.zcode/centos7-runtime/lib/ld-linux-x86-64.so.2
    -> ~/.zcode/centos7-runtime/lib 中的私有 glibc/libstdc++
    -> ~/.zcode/server/zcode-server.cjs
    -> zcode-hello
```

Zcode 启动外部任务时：

```text
Zcode Node
    -> exec /bin/bash、git 或其他用户命令
    -> 外部程序自己的系统 ELF 解释器
    -> CentOS 7 系统库
```

由于未导出私有 glibc 的 `LD_LIBRARY_PATH`，外部任务不会继承 Zcode 的兼容运行库路径。

### 5.2 选择直接补丁 Node，而不是全局包装

第一版只对 `~/.zcode/server/node` 的安装副本设置 ELF `PT_INTERP`，使其指向私有 `ld-linux-x86-64.so.2` 的绝对路径。

概念命令如下，仅用于说明设计，不作为用户手工操作指引：

```text
patchelf --set-interpreter <absolute-private-loader> <temporary-node>
```

在当前 Zcode Node v22.16.0 上，写入 RPATH 会导致进程以 SIGSEGV 退出，因此实现必须保留原始 RPATH/RUNPATH。`vscode-server-centos7` 1.137.0 中的加载器已经能够从自身目录找到配套 GNU 运行库，无需修改目标 Node 的 RPATH。

补丁应在临时副本上完成。临时副本验证通过后，再原子替换 `~/.zcode/server/node`。

该设计的优点：

- 只有 Zcode 自带 Node 使用私有加载器；
- `process.execPath` 仍指向 `~/.zcode/server/node`；
- Node 自我派生或 `child_process.fork()` 时仍能正确启动；
- 不需要 Shell 包装器，不改变参数和标准输入输出协议；
- 不需要为其他进程设置环境变量；
- Zcode 启动的系统命令仍按自身 ELF 配置运行。

### 5.3 不采用全目录 ELF 扫描

参考项目 `vscode-server-centos7` 会扫描 VS Code Server 和扩展目录，这是为了适配 VS Code 的多二进制布局。

本工具第一版不得照搬该行为。当前故障发生在顶层 Zcode Node 启动之前，只补丁该 Node 是满足需求的最小变更。

如果将来发现 Zcode 必须直接启动第二个不兼容的原生二进制，应先收集明确错误证据，再通过独立需求增加精确目标白名单，不能改为无条件递归扫描。

## 6. 私有运行库

### 6.1 运行库组成

发布包应只包含目标 Node 启动所需的最小运行时文件，例如：

- `ld-linux-x86-64.so.2`；
- `libc.so.6`；
- `libm.so.6`；
- `libdl.so.2`；
- `libpthread.so.0`；
- `librt.so.1`；
- `libresolv.so.2`；
- 必要的 NSS/DNS 模块；
- `libstdc++.so.6`；
- `libgcc_s.so.1`；
- 相应许可证和构建元数据。

实际列表必须由目标 Node 的 `DT_NEEDED`、运行测试和 DNS/TLS 测试共同确定，不能仅凭文件名猜测。

### 6.2 构建约束

- 当前验证的导入运行库为 glibc 2.44 和 libstdc++ 6.0.36；
- 该参考运行库构建时最低 kernel 设为 `3.10.0`；
- 构建必须可复现，所有源码 URL 和 SHA256 固定；
- 构建产物必须在真正的 CentOS 7 用户空间和 kernel 3.10 环境验证；
- 发布包不得包含 Zcode 自身文件；
- 发布包中的每个文件都应进入 SHA256 清单。

### 6.3 路径约束

私有加载器的 ELF `PT_INTERP` 必须是绝对路径，因此安装时需要根据目标用户主目录和具体运行库 release 目录生成补丁。

工具必须保留目标 Node 原有的 RPATH/RUNPATH，不得加入私有运行库、Conda、系统全局自定义库目录或其他任务的运行库目录。

## 7. 管理命令设计

建议提供单一入口：

```text
zcode-centos7 inspect
zcode-centos7 install
zcode-centos7 status
zcode-centos7 verify
zcode-centos7 repair
zcode-centos7 uninstall
```

所有具有写操作的命令都必须显式指定或确认目标 Zcode 根目录，默认值为 `$HOME/.zcode`。

### 7.1 `inspect`

只读检查：

- 操作系统、CPU 架构和 kernel；
- 系统 glibc 版本；
- `~/.zcode/server/node` 是否存在、是否为普通文件和 ELF；
- Node 的架构、`PT_INTERP`、RPATH/RUNPATH；
- Node 所需的 GLIBC、GLIBCXX 和 CXXABI 版本；
- Zcode Node Runtime 元数据；
- 当前文件是否已经由本工具处理；
- 私有运行库是否完整。

`inspect` 不得写文件，不得自动下载依赖，也不得启动或终止现有 Zcode 进程。

### 7.2 `install`

建议流程：

1. 解析并规范化 `$HOME/.zcode`，拒绝空路径、根目录和符号链接越界；
2. 确认目标严格等于 `<zcode-root>/server/node`；
3. 对原始 Node 执行只读 ABI 检查；
4. 校验运行库发布包的 SHA256；
5. 将运行库安装到临时目录；
6. 将原始 Node 复制到备份目录并记录 SHA256；
7. 复制原始 Node 到同文件系统的临时路径；
8. 只对临时 Node 设置解释器，保持原始 RPATH/RUNPATH；
9. 对临时 Node 执行 `--version`、依赖和子进程隔离测试；
10. 写入临时状态清单；
11. 使用原子重命名提交运行库、Node 和状态清单；
12. 再执行一次完整验证。

任一步失败都必须保留原始 Node，不允许留下半安装状态。

### 7.3 `status`

输出至少包括：

- 安装状态；
- 当前 Node SHA256；
- 对应原始 Node SHA256；
- 当前 ELF 解释器；
- 当前 RPATH；
- 私有运行库版本；
- Zcode Node Runtime 版本；
- 是否疑似被 Zcode 更新覆盖；
- 最近一次安装或修复时间。

`status` 必须只读。

### 7.4 `verify`

验证项目：

1. 私有加载器可以启动目标 Node；
2. `node --version` 正常退出；
3. 加载到 Node 进程的是私有 libc、libstdc++ 和 libgcc；
4. 运行简单 JavaScript 成功；
5. Node 启动 `/bin/bash -c` 成功；
6. `/bin/bash` 使用系统解释器，且环境中没有工具注入的 glibc `LD_LIBRARY_PATH`；
7. Node DNS 解析成功；
8. 在用户明确允许启动测试服务时，运行 `zcode-server.cjs` 并识别 `zcode-hello`。

默认 `verify` 不得结束正在运行的 Zcode 服务。握手测试必须带超时，并只终止由本次验证创建的进程。

### 7.5 `repair`

用于处理 Zcode 更新覆盖 Node 的场景：

- 如果 Node 已正确补丁，直接成功退出；
- 如果 Node 恢复为系统解释器且 SHA256 与记录不同，视为新的 Zcode Node；
- 先为新 Node 创建新的版本化备份，再执行安装流程；
- 旧备份不得被静默覆盖；
- 如果目标既不是已知补丁文件，也不是合法的新 Node ELF，则拒绝处理并报告原因。

第一版不设置 watcher、cron 或常驻服务。修复只在用户显式运行 `repair` 时发生。

### 7.6 `uninstall`

卸载流程：

1. 验证当前 Node 与状态清单一致；
2. 找到与当前 Zcode Node 版本对应的原始备份；
3. 验证备份 SHA256；
4. 通过临时文件原子恢复；
5. 验证恢复文件使用原系统解释器；
6. 将状态标记为已卸载。

如果 Zcode 已经更新且当前文件状态与清单不一致，`uninstall` 不得猜测应该恢复哪个版本。

默认保留运行库和备份，避免不可逆删除。清理历史文件应作为单独、显式的后续功能。

## 8. 状态清单

建议使用 JSON，示意结构如下：

```json
{
  "schema_version": 1,
  "tool_version": "0.1.0",
  "zcode_root": "/home/example/.zcode",
  "node_path": "/home/example/.zcode/server/node",
  "node_original_sha256": "...",
  "node_patched_sha256": "...",
  "backup_path": "/home/example/.zcode/centos7-runtime/backups/node.<sha256>",
  "original_interpreter": "/lib64/ld-linux-x86-64.so.2",
  "patched_interpreter": "/home/example/.zcode/centos7-runtime/lib/ld-linux-x86-64.so.2",
  "runtime_version": "glibc-2.28-gcc-9",
  "zcode_node_version": "...",
  "installed_at": "..."
}
```

状态清单不得记录令牌、SSH 密钥、环境变量内容或 Zcode 会话数据。

## 9. 更新与兼容策略

Zcode 可能根据以下元数据决定是否重新部署 Node：

```text
~/.zcode/server/.asset-components/node-runtime.json
```

工具可以只读记录该文件内容或摘要，但不得伪造、冻结或修改版本元数据来阻止更新。

更新后的预期行为：

1. Zcode 更新覆盖 Node；
2. 下一次连接可能再次出现 ABI 错误；
3. 用户运行 `zcode-centos7 repair`；
4. 工具识别新 Node、创建新备份并重新补丁；
5. 验证后重新连接。

自动修复只有在掌握 Zcode 官方部署 hook 或稳定协议后才考虑，不能通过全局登录脚本或影响其他 SSH 任务的方式实现。

## 10. 故障安全设计

### 10.1 文件安全

- 只接受普通文件作为 Node 目标；
- 对路径中的符号链接进行解析和边界检查；
- 临时文件权限不得宽于原始 Node；
- 不跟随备份目录中的不可信符号链接；
- 使用同一文件系统中的临时文件确保原子重命名；
- 写入清单后执行 `fsync`，再提交关键重命名；
- 工具退出时只清理自己创建且路径已验证的临时文件。

### 10.2 进程安全

- 不使用 `pkill node`、`killall node` 或模糊进程匹配；
- 默认不终止现有 Zcode 进程；
- 测试只管理自己启动并记录 PID 的子进程；
- 安装前如果目标 Node 正在运行，给出提示并允许完成文件替换，但不干扰现有进程；
- 不监听或修改其他用户进程。

### 10.3 输出协议安全

Zcode 使用标准输入输出完成启动握手。补丁后的 Node 在正常启动路径上不得额外输出内容。

管理工具可以输出诊断信息，但目标 `~/.zcode/server/node` 本身的正常 stdout/stderr 行为必须与原始 Node 一致。

## 11. 测试计划

### 11.1 静态测试

- 校验运行库 SHA256；
- 检查 Node 原始和补丁后的 ELF 头；
- 检查 `PT_INTERP`；
- 检查 RPATH/RUNPATH 与原文件一致；
- 提取并比较 GLIBC/GLIBCXX/CXXABI 需求；
- 确认只变更预期目标和工具状态目录。

### 11.2 单元测试

- 路径规范化和边界检查；
- 状态清单读写；
- SHA256 和版本识别；
- 原始、已安装、被更新、未知文件等状态机；
- 重复安装幂等性；
- 修复时的备份轮换；
- 卸载时的冲突拒绝；
- 参数透传和退出码透传。

### 11.3 CentOS 7 容器测试

在干净 CentOS 7 环境中验证：

- 系统 glibc 仍为 2.17；
- 原始测试 Node 因 ABI 不兼容而失败；
- 安装后 Node 正常启动；
- Node 加载私有 glibc/libstdc++；
- Node 启动 `/bin/bash` 时 Bash 仍加载系统 glibc；
- DNS、HTTPS、文件读写、Git 子进程正常；
- 安装、重复安装、模拟更新、修复、卸载完整闭环；
- 卸载后的原始 Node SHA256 与安装前完全一致。

### 11.4 真实 Zcode 端到端测试

- Windows Zcode 能通过 SSH 建立连接；
- 服务端输出合法 `zcode-hello`；
- 打开远程工作区成功；
- Zcode Agent 能读取和修改工作区文件；
- Zcode Agent 能执行 Shell、Git 和项目测试；
- 同时运行的普通 SSH 会话和非 Zcode 任务行为不变；
- Zcode 断开后不存在兼容层遗留环境变量或守护进程。

### 11.5 隔离性回归测试

隔离性是发布阻断条件，至少验证：

```text
/bin/bash
/usr/bin/git
/usr/bin/ssh
/usr/bin/python（如系统存在）
系统 node（如存在且不是 Zcode Node）
Conda 环境中的程序（如测试环境存在）
```

在安装前后，它们的解释器、库解析和基础行为必须一致。

工具执行前后，用户 Shell 的以下内容必须保持不变：

```text
PATH
LD_LIBRARY_PATH
LD_PRELOAD
LIBRARY_PATH
CPATH
```

## 12. 验收标准

只有同时满足以下条件，第一版才可发布：

1. CentOS 7 上不再出现目标 Node 的 GLIBC、GLIBCXX 或 CXXABI 缺失错误；
2. Windows Zcode 完成远程握手并能稳定使用；
3. 只修改 `~/.zcode/server/node` 和 `~/.zcode/centos7-runtime`；
4. 未修改系统库、Shell 配置、SSH 配置和全局环境；
5. Zcode 启动的系统任务继续使用系统运行库；
6. 非 Zcode 任务在安装前后行为一致；
7. 安装和修复幂等；
8. 卸载能恢复字节一致的原始 Node；
9. 所有失败路径都不会留下不可启动且无备份的 Node；
10. 运行库来源、构建参数、SHA256 和许可证完整可审计。

## 13. 开发阶段

### 阶段一：只读环境盘点

- 检查当前 `~/.zcode/server` 布局；
- 记录 Node 版本、SHA256、解释器和 ABI 需求；
- 检查 Zcode Runtime 元数据；
- 确认启动命令和握手行为；
- 输出盘点报告，不修改任何文件。

### 阶段二：最小技术验证

- 准备私有 glibc/libstdc++ 运行库；
- 在 Node 临时副本上只完成解释器补丁；
- 验证 Node、自我派生、Shell 子进程、DNS 和握手；
- 不替换正式 `~/.zcode/server/node`，直到临时验证全部通过。

### 阶段三：管理工具

- 实现 `inspect/install/status/verify/repair/uninstall`；
- 实现状态机、原子替换和备份恢复；
- 增加单元测试和故障注入测试。

### 阶段四：可复现构建和发布

- 固定 glibc、GCC、binutils 和 kernel headers 版本；
- 固定下载地址和 SHA256；
- 构建最小运行库发布包；
- 增加 CentOS 7 容器测试；
- 生成 SBOM、许可证清单和 release checksum。

### 阶段五：真实客户端验收

- 使用 Windows Zcode 测试远程连接；
- 执行隔离性回归；
- 模拟 Zcode Node 更新并验证 `repair`；
- 验证卸载恢复。

## 14. 许可证与分发

项目可以参考 `vscode-server-centos7` 的构建思路，但如果直接复制或改编其 GPLv3 代码，必须遵守 GPLv3。

glibc、libstdc++、libgcc 和构建工具各自具有独立许可证及例外条款。发布二进制运行库时必须：

- 保留许可证和版权声明；
- 公布对应源码版本和补丁；
- 提供完整、可复现的构建脚本；
- 满足 LGPL 对重新链接、修改和源码提供的要求；
- 不把 Zcode 专有二进制纳入本项目发布包。

若希望项目自身采用更宽松许可证，应原创实现管理工具和启动适配代码，只借鉴架构思想，不复制 GPLv3 源码。

## 15. 开发前必须确认的信息

开始编码前，阶段一需要确认：

- 当前服务器确切的 CPU 架构和 kernel 版本；
- `~/.zcode/server/node` 的 Node 版本和 SHA256；
- Node 当前的 `PT_INTERP`、RPATH/RUNPATH 和 `DT_NEEDED`；
- `~/.zcode/server` 是否包含直接执行的其他原生二进制；
- `.asset-components/node-runtime.json` 的实际格式；
- Zcode Windows 客户端传递给 Node 的完整参数；
- 是否存在文件哈希校验或自动覆盖行为；
- 私有运行库放置在 `~/.zcode/centos7-runtime` 是否符合用户期望。

在这些信息确认前，不应扩展补丁范围，也不应假设所有 VS Code Server 的处理逻辑同样适用于 Zcode。
