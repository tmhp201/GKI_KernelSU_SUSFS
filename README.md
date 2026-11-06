# violin 6.6.143 融合版 GKI 内核

**Xiaomi Pad 7S Pro 12.5 (`violin`) · HyperOS 3.0.304.0.WOTCNXM (Android 16)**

BakaSU + SUSFS v2.3.0 + DroidSpaces 容器 + 小米私有 F2FS 特性，基于 AOSP `android15-6.6-2026-10` (6.6.143) 构建。

> ⚠️ **刷机有风险**。仅适用于 bootloader 已解锁、系统为 HyperOS 3.0.304.0 的 violin 设备。升级澎湃 OS 4 前请勿使用（KMI 不同，会无法启动）。请保留官方 `boot.img` 作救砖件。

---

## 目录

- [这是什么](#这是什么)
- [特性](#特性)
- [与官方内核 / 各版本的区别](#与官方内核--各版本的区别)
- [下载与校验](#下载与校验)
- [刷入](#刷入)
- [已知问题与风险](#已知问题与风险)
- [安全性说明](#安全性说明)
- [开源致谢](#开源致谢)
- [许可证与合规](#许可证与合规)
- [免责声明](#免责声明)

---

## 这是什么

一个面向小米平板 7S Pro 12.5 的自定义 GKI 内核，目标是在**尽量贴近 AOSP 官方基线**的前提下，同时提供：

1. **root**（BakaSU / KernelSU 系）
2. **root 隐藏**（SUSFS v2.3.0）
3. **Linux 容器支持**（DroidSpaces 所需 7 项内核配置）
4. **补回小米私有 F2FS 特性**（VIP 文件优先写入、增强 I/O 统计、Hybrid UFS ABI）

内核版本 `6.6.143-android15-8-ga10b2932df624`，KMI `android15-8`，4K 页大小，boot header v4。

**没有**启用 BBG、NoMount、Re-Kernel、KPM、LZ4KD、BBRv3、ZRAM 增强、Unicode 绕过、一加 8E 支持等第三方增强项（全部关闭，二进制 0 命中）。

---

## 特性

### root 与隐藏
- **BakaSU v4.2.0-rc3**（version code `35257`），管理器 `com.resukisu.resukisu`
- Hook 方式：kprobe；支持多管理器共存（`KSU_MULTI_MANAGER_SUPPORT=y`）
- **SUSFS v2.3.0**，10 项配置全开：
  `SUS_PATH / SUS_MOUNT / SUS_KSTAT / SPOOF_UNAME / OPEN_REDIRECT / SUS_MAP / SPOOF_CMDLINE_OR_BOOTCONFIG / ENABLE_LOG / HIDE_KSU_SUSFS_SYMBOLS / ENABLE_AVC_LOG_SPOOFING`
- v2.3.0 相对 v2.0.0 的额外能力：按 SELinux context 隐藏、AVC 日志伪装白名单、`/proc/self/fd` 与 maps 的 open_redirect 伪装、mountinfo 伪装、FUSE 场景适配

### 容器（DroidSpaces）
`SYSVIPC / POSIX_MQUEUE / IPC_NS / PID_NS / USER_NS / DEVTMPFS / NTSYNC` 全部 =y，并应用 SYSVIPC kABI 修复补丁（槽位 678）与 NTSync 补丁。

### 小米私有 F2FS 特性
| 配置 | 作用 |
|---|---|
| `F2FS_VIP_FILE` | VIP inode 管理（上限 8192），高优先级任务写文件走优先路径；sysfs `vip_file_enable` / `vip_inode_count` |
| `XIAOMI_ENHANCED_IOSTAT` | 滚动窗口 / 日延迟 I/O 统计；sysfs `iostat_window_latency` / `iostat_daily_latency` |
| `F2FS_FS_HYBRID_UFS` + `BLOCK_HYBRID_UFS` | 保持小米 sysfs ABI；AOSP 无 paired-LUN 映射，实际回退单设备分配器（ABI 占位） |

> 这三个特性来自 dash-kernel 的 `0005-xiaomi-f2fs-features.patch`（基于 6.6.30），本仓库将其重新适配到 6.6.143：删除孤儿/重复/语法错误的 `f2fs_lock_context lc` 声明、删除与 6.6.143 原生 `F2FS_SBI_GENERAL_RW_ATTR` 重名的 4 组 sysfs 属性、清理纯重排 hunk。最终补丁 42,721 B。

### 安全基线
SELinux / CFI_CLANG / ARM64_MTE / HARDENED_USERCOPY / FORTIFY_SOURCE / STACKPROTECTOR_STRONG / KASLR / ARM64_BTI / SLAB_FREELIST_RANDOM / SLAB_FREELIST_HARDENED / PTR_AUTH 等 19 项与官方内核逐项一致。

---

## 与官方内核 / 各版本的区别

> 官方 = HyperOS 3.0.304.0 自带 6.6.118 OGKI 内核。
> 本仓库另有 V6（BakaSU + SUSFS v2.3.0，无小米 F2FS）与 SukiSU 版（SukiSU 40548 + SUSFS v2.0.0 + 小米 F2FS）。
> 本版 = **融合版**：V6 的 root/隐藏 + SukiSU 版的小米特性。

| 维度 | 官方 6.6.118 | V6 | SukiSU 版 | **本版（融合）** |
|---|---|---|---|---|
| 内核版本 | 6.6.118 | 6.6.143 | 6.6.143 | **6.6.143** |
| root | 无 | BakaSU | SukiSU(40548) | **BakaSU** |
| 管理器 | — | `com.resukisu.resukisu` | `com.sukisu.ultra` | **`com.resukisu.resukisu`** |
| SUSFS | 无 | **v2.3.0** | v2.0.0 | **v2.3.0** |
| 多管理器 | — | ✅ | ❌ | **✅** |
| Hook | — | kprobe | manual hook | **kprobe** |
| DroidSpaces 容器 | ❌（配置全关） | ✅ 7/7 | ✅ 7/7 | **✅ 7/7** |
| F2FS_VIP_FILE | ✅ | ❌ | ✅ | **✅** |
| XIAOMI_ENHANCED_IOSTAT | ✅ | ❌ | ✅ | **✅** |
| F2FS_FS_HYBRID_UFS | — | ❌ | ✅ | **✅** |
| SCSI_DISCARD / FASTDISCARD | ✅ | ❌ | ❌ | ❌ |
| XIAOMI_EROFS_IOSTAT | ✅ | ❌ | ❌ | ❌ |
| MEMFD_ASHMEM_SHIM | ✅ | ❌ | ❌ | ❌ |
| STREAM_PARSER | ✅ | ❌ | ❌ | ❌ |
| LTO | 关闭 | thin LTO | thin LTO | thin LTO |
| 换新存储 / 碎片整理 | ✅ | ✅ | ✅ | **✅**（f2fs 标准 ioctl 全在） |

**官方有、本版缺失的 5 项**：`SCSI_DISCARD` / `SCSI_FASTDISCARD` / `XIAOMI_EROFS_IOSTAT` / `MEMFD_ASHMEM_SHIM` / `STREAM_PARSER`。这些是小米私有代码，AOSP 6.6.143 源码中没有，小米公开 OSS（`violin-v-oss`，停在 6.6.30）亦未开源，无法安全移植。影响 UFS TRIM 加速、EROFS 统计、老式 ashmem 兼容性、个别 VPN 流解析场景。

配置层面，本版相对 V6 仅多 4 项小米 F2FS 配置（`F2FS_VIP_FILE` / `XIAOMI_ENHANCED_IOSTAT` / `F2FS_FS_HYBRID_UFS` / `BLOCK_HYBRID_UFS`），其余 6217 项逐字节相同。

---

## 下载与校验

产物来自 GitHub Actions Run `42188832630`（✅ success）。

| 文件 | 大小 | sha256 |
|---|---|---|
| `BakaSU_kernel-android15-6.6-143.zip` | 66,235,821 B | `4c4c98f87716c4d034f190fdaa6439a5fc6b437e77696f138ac7f2d3e83b41f0` |
| 内含 `android15-6.6.143-2026-10-boot.img` | 67,108,864 B | 见下方解包校验 |
| 内含 `android15-6.6.143-2026-10-AnyKernel3.zip` | — | 用于 recovery 卡刷 |
| `BakaSU-Manager(35257)` | 8,872,573 B | 配套管理器 |

**下载后必须校验**：
```
sha256sum BakaSU_kernel-android15-6.6-143.zip
# 应为 4c4c98f87716c4d034f190fdaa6439a5fc6b437e77696f138ac7f2d3e83b41f0
```
不一致说明下载不完整，**请勿刷入**。

解包后建议核对 AK3 内 `Image` 与 boot 内核一致：
```
unzip -p android15-6.6.143-2026-10-AnyKernel3.zip Image | sha256sum
# 应等于 boot.img 中 kernel 段的 sha256
```

---

## 刷入

```
adb reboot fastboot
fastboot getvar current-slot        # 确认槽位
fastboot flash boot android15-6.6.143-2026-10-boot.img
fastboot reboot
```
或在 recovery 中卡刷 `android15-6.6.143-2026-10-AnyKernel3.zip`。

**管理器必须对应**：刷本版请安装 BakaSU Manager（`com.resukisu.resukisu`）。安装 SukiSU / 官方 KernelSU 管理器拿不到 root。

刷前备份当前 boot 分区，并保留官方 `boot.img`。刷后第一时间测试：相机、指纹、音频、快充、通话。

**救砖**：`fastboot flash boot <官方 boot.img>` 即可恢复。

---

## 已知问题与风险

1. **跨 25 个稳定版**：官方 6.6.118 → 本版 6.6.143。KMI 同为 `android15-8`，`same_magic()` 只比 ABI 标志位，vendor 模块理论上能加载，但内部 API 有变化，**相机 / 指纹 / 音频 / 快充偶发不工作**的风险无法 100% 排除。
2. **HYBRID_UFS 是 ABI 占位**：AOSP 无 paired-LUN 混合分配器，实际回退单设备分配器。真正有实际行为的是 VIP_FILE 与 ENHANCED_IOSTAT。
3. **VIP_FILE 标记依赖 vendor hook**：内置保守回退（RT / nice<0 任务写普通文件自动标记），但无小米 perfd 服务时标记范围比官方小；I/O 统计数据无用户态消费者。
4. **缺失 5 项官方小米特性**（见上表）。
5. **每次 HyperOS OTA 会覆盖 boot 分区**，root 失效，需重刷。
6. **AVB 签名变化**：刷机包用自带密钥重签 boot，设备必须已解锁 bootloader。
7. **反回滚**：官方 `anti_version.txt`=1，勿降级刷更低 anti 的官方包。
8. **不要跨系统版本使用**：升级澎湃 OS 4（内核 6.18.21）后 KMI 不同，本内核不可用。

---

## 安全性说明

- 未引入任何闭源二进制 blob；全部改动为可审阅的 C 源码补丁与 workflow 配置
- 内核二进制扫描：Re-Kernel / BBG / NoMount / LZ4KD / BBRv3 / KPM / `bbr3` / `lz4kd` 全部 0 命中（同基线已构建内核实测，本版表单逐项关闭这些开关）
- 补丁只改 `fs/f2fs/`、`block/Kconfig`、`include/trace/`，不碰网络栈、不改用户态、不添加自启动服务
- 模块签名配置与官方一致（`MODULE_SIG=y`、`SIG_FORCE=n`）
- KSU 调试关闭（`KSU_DEBUG=n`）

**必须如实说明**：
- BakaSU / KernelSU 本身是提权框架，获取 root 会**降低系统安全边界**，这是它的用途而非暗门。请只给可信 App 授权。
- 本仓库无法对上游 BakaSU / SUSFS / 工作流框架的全部历史代码做逐行形式化验证；只能确认本版**没有额外夹带**、未启用可疑增强项。
- 请只从本仓库 Release 下载并校验 sha256，勿使用来路不明的「优化版」。

---

## 开源致谢

本项目是**集成与适配工作**，内核能力与构建框架完全来自以下开源项目，特此致谢。

### 内核基线
| 项目 | 仓库 | 用途 |
|---|---|---|
| AOSP Generic Kernel Image | `android.googlesource.com/kernel/common`（`android15-6.6-2026-10`, commit `a10b2932df624`） | 内核源码基线 |

### root 与隐藏
| 项目 | 仓库 | 用途 | 许可证 |
|---|---|---|---|
| KernelSU | [tiann/KernelSU](https://github.com/tiann/KernelSU) | root 框架（BakaSU/SukiSU 的基础） | GPL-3.0 |
| **BakaSU** | [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU) | 本版 root 实现（v4.2.0-rc3, 35257） | GPL-3.0 |
| **SUSFS (susfs4ksu)** | [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu)（`gki-android15-6.6` 分支） | 本版 SUSFS v2.3.0 | GPL-3.0（见仓库） |
| SUSFS 镜像 | [ShirkNeko/susfs4ksu](https://github.com/ShirkNeko/susfs4ksu) | 备用克隆源 | GPL-3.0 |
| SukiSU-Ultra | [SukiSU-Ultra/SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) | 工作流中可选变体（本版未启用） | GPL-3.0 |
| KernelSU-Next | [KernelSU-Next/KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next) | 工作流中可选变体（本版未启用） | GPL-3.0 |

### 容器（DroidSpaces）
| 项目 | 仓库 | 用途 | 许可证 |
|---|---|---|---|
| Droidspaces-OSS | [ravindu644/Droidspaces-OSS](https://github.com/ravindu644/Droidspaces-OSS) | SYSVIPC kABI 修复补丁（槽位 678） | GPL-3.0 |
| Droidspaces_Kernel_patch | [Goldzxcbug/Droidspaces_Kernel_patch](https://github.com/Goldzxcbug/Droidspaces_Kernel_patch) | NTSync 内核补丁 | MIT |

### 小米私有特性
| 项目 | 仓库 | 用途 |
|---|---|---|
| dash-kernel `0005-xiaomi-f2fs-features.patch` | dash-kernel 项目（小米 F2FS 特性移植补丁，基于 6.6.30） | 本版小米 F2FS 特性的来源，已重新适配 6.6.143 |
| Xiaomi Kernel OpenSource | [MiCode/Xiaomi_Kernel_OpenSource](https://github.com/MiCode/Xiaomi_Kernel_OpenSource)（`violin-v-oss` 分支） | 仅用于核对官方符号/配置，未直接编译其源码 |

> 小米内核开源代码遵循 **GPL-2.0**（Linux 内核许可证），各设备分支可能包含厂商专有文件，请以小米仓库内 LICENSE / 各文件 SPDX 标记为准。本项目只移植了 F2FS 相关开源补丁部分，未包含小米专有二进制。

### 构建与打包
| 项目 | 仓库 | 用途 | 许可证 |
|---|---|---|---|
| GKI_KernelSU_SUSFS (Actions 框架) | [zzh20188/GKI_KernelSU_SUSFS](https://github.com/zzh20188/GKI_KernelSU_SUSFS)（本仓库 fork 自 WildKernels / zzh20188 系） | GitHub Actions 构建工作流 | GPL-2.0 |
| kernel_patches | [WildKernels/kernel_patches](https://github.com/WildKernels/kernel_patches) | 内核补丁集合 | 见仓库（NOASSERTION，按各补丁原许可） |
| AnyKernel3 | [WildKernels/AnyKernel3](https://github.com/WildKernels/AnyKernel3)（`gki-2.0`），上游 [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) | 刷机包模板 | 见仓库 LICENSE |
| Action-Build | [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) | 构建脚本 | 见仓库 LICENSE |
| repo manifest | `android.googlesource.com/kernel/manifest` | AOSP 源码同步 | — |

### 工作流中存在但本版**未启用**的项目
Re-Kernel（[Sakion-Team/Re-Kernel](https://github.com/Sakion-Team/Re-Kernel), GPL-2.0）、Baseband-guard / BBG（[vc-teahouse/Baseband-guard](https://github.com/vc-teahouse/Baseband-guard), GPL-2.0）、NoMount（[maxsteeel/nomount](https://github.com/maxsteeel/nomount), GPL-3.0）、KPM、LZ4KD、BBRv3、ZRAM 增强、Unicode 绕过、一加 8E 支持。这些项目的代码**未编入本版内核**。

---

## 许可证与合规

- **Linux 内核 / AOSP kernel/common**：GPL-2.0（含 `Linux-syscall-note` 例外）。
- **本仓库新增的适配补丁与 workflow 改动**：遵循上游对应许可证；对 `0005` 补丁的适配修改同样按 GPL-2.0（内核）条款提供。
- **KernelSU / BakaSU / SUSFS / Droidspaces-OSS / SukiSU-Ultra / KernelSU-Next**：GPL-3.0。
- **Droidspaces_Kernel_patch**：MIT。
- **zzh20188/GKI_KernelSU_SUSFS**：GPL-2.0。
- **AnyKernel3 / kernel_patches / Action-Build / Re-Kernel / BBG / NoMount**：以其各自仓库内 LICENSE 为准（部分为 NOASSERTION，请以仓库实际文件为准）。
- **小米内核代码**：GPL-2.0，厂商专有部分以小米仓库声明为准。

**GPL 合规说明**：本仓库以源码补丁 + 自动构建工作流形式分发，未分发预编译的 GPL 内核模块二进制；刷机包内的内核 `Image` 由公开工作流从公开源码构建，任何人均可从本仓库复现完整构建过程并获取对应源码。若你要二次分发或修改，请遵守各上游项目的 GPL / MIT 条款（保留版权声明、提供对应源码、同样以相同许可证开源衍生作品）。

本仓库**不主张**对上述上游项目的任何所有权；所有商标、项目名称归各自所有者。

---

## 免责声明

- 本项目为个人学习/研究用途的集成构建，与 Xiaomi / Google / 上述任何上游项目**无官方关联**，也非其官方发布。
- 刷入自定义内核可能导致**设备无法启动、数据丢失、功能异常、保修失效、安全边界降低**。请自行评估风险，作者不对任何直接或间接损失负责。
- root 权限本身意味着更高的安全风险；请谨慎授予 App 权限。
- 请在合法合规、且已备份数据的前提下使用。
- 使用前请确认设备型号（`violin`）、系统版本（HyperOS 3.0.304.0 / Android 16）、bootloader 解锁状态三者全部匹配。

---

## 构建信息

```
Workflow : Android 内核构建-自定义 (kernel-custom.yml → build.yml)
Run      : 42188832630  ✅ success
Head     : 11531def (补丁 0005-adapted-v16.patch, sha 43b2f92f...)
BakaSU   : version code 35257 / v4.2.0-rc3-516d3e87
SUSFS    : v2.3.0
Kernel   : 6.6.143-android15-8-ga10b2932df624-ab10022985-4k
KMI      : android15-8 / 4K pages / boot header v4
Artifact : BakaSU_kernel-android15-6.6-143 (66,235,821 B)
```
