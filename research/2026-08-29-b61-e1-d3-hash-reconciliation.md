# B61-E1-D3：跨运行时self-hash reconciliation预注册

日期：2026-08-29

状态：PREREGISTERED

D2的真实Blender probe exit 0，并写出内部status PASS：bpy pixel count为0；OpenImageIO 3.1.13.1唯一解析`BFS_MASTER.Combined.RGBA`；1920×1080×4 float32-LE projection全部finite；两个独立open的SHA-256同为`192237bd…`。但Node supervisor没有写receipt，因为Python self-hash使用`json.dumps`保留`1.0`，Node canonical JSON使用`JSON.stringify`写为`1`。

D3不再启动Blender，也不重新解码。它只对immutable D2 tree做reconciliation：用Blender随附的standalone Python 3.13重算原始Python canonical hash；用Node重现不相等；递归只把finite integral float规范为integer后，要求Python规范化hash与Node hash exact。然后独立验证D2 process/log/result的全部语义门。

资源上限为zero Blender/render/model/network/Docker、最多一个bundled-Python process、15秒和1 MiB输出。D3 PASS只支持保留的真实Blender decoder observation，并允许下一步预注册B61 C2；它不修改B61工具，不授权formal retry。
