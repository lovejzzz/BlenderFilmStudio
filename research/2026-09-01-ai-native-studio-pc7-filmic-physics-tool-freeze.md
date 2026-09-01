# PC7 正式工具冻结

产品增量 `c7eece67bff64cbff2de4c6e1aee3248afbca600` 只修改
`scripts/modules/film_studio_causal.py`，统计为 116 additions / 15 deletions。
它没有场景 ID、项目名或手选帧分支，也没有目标物体关键帧写入。

正式工具在 attempt-01 根创建前冻结：

- 产品侧 helper：12 个负向控制、一次合法物理构建、三张 still、24 张 impact
  clip frames、一次保存和一次重开；
- runner：local-only source clone、明确只读 LIBDIR、clean native arm64 build、
  已验收的 app bundle rename、三个隔离产品进程和 FFmpeg/FFprobe 绑定；
- independent auditor：不导入产品模块或 helper，独立重算五目标 SHA-256 初始微差、
  IMPACT lexicographic selector、AFTERMATH settle window、媒体哈希和零最终姿态权限。

Tool freeze self hash 为
`668240997d9fcedcf16a94330c400fa939bde4fa65bdf861937bacb9a9116247`。
任何正式失败都必须保留，不能改弱活动目标数、撞击延迟、五目标倾倒、重开、媒体或
视觉门槛。
