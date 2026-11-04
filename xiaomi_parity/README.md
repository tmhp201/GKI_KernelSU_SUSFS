# xiaomi_parity 小米特性对齐补丁

来源: NuoFang6/dash-kernel (legacy-6.6.118), 实机验证于 AOSP android15-6.6.118 GKI 基线。

## 采纳范围（构建时启用）
- 0005-xiaomi-f2fs-features.patch 中仅启用 CONFIG_F2FS_VIP_FILE
  （VIP inode 管理, 与原厂接口一致; 选择策略为保守 fallback: RT 任务或负 nice 的写打开）

## 显式关闭（构建配置压制, 与原厂行为一致性不足或无实义）
- CONFIG_XIAOMI_ENHANCED_IOSTAT  (原厂 20 槽窗口+10 档粒度, 补丁 5 类聚合, 粒度差距大)
- CONFIG_XIAOMI_EROFS_IOSTAT    (原厂每 CPU 10+10+5+5 槽, 补丁单桶, 粒度差距大)
- CONFIG_F2FS_FS_HYBRID_UFS     (空壳接口, hw_support_hybrid() 恒为 false, 无真实功能)
- CONFIG_BLOCK_HYBRID_UFS       (同上)

## 未采纳
- CONFIG_SCSI_DISCARD / CONFIG_SCSI_FASTDISCARD: 无源码, 多 descriptor UNMAP
  实现有丢数据风险 (dash-kernel 作者亦放弃)

## 0007-stock-parity-hooks.patch 说明
补齐 AOSP GKI 相对原厂缺失的 vendor hook 调用点 (bio merge bypass,
LZ4 tracepoint, fuse/mm/sched hooks), 638 个原厂 vendor 模块实测零符号缺失。
与 0005 独立应用。

## 应用位置
build.yml 中「应用 SUSFS 补丁」步骤之后、「配置内核选项」之前:
  patch -p1 --forward < "$GITHUB_WORKSPACE/xiaomi_parity/0005-xiaomi-f2fs-features.patch"
  patch -p1 --forward < "$GITHUB_WORKSPACE/xiaomi_parity/0007-stock-parity-hooks.patch"
