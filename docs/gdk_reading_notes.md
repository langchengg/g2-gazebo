# GDK 2.6.3 全目录阅读笔记

Python migration update: the existing43-page ledger is preserved. Selective current re-reading and the document-derived read-only adapter are recorded in [gdk_python_review.md](gdk_python_review.md); real SDK and hardware validation remain separate.
Review date: 2026-09-08. Scope: 43 pages in the observed zhCn directory: home 1, getting started 4, concepts 2, how-to 5, tools 2, Python API 12, C++ API 11, ROS2 API 5, appendix 1. No additional documentation language or release-notes page appears in this version configuration. The three Markdown hash links resolve to indexed pages; no body-only images or undiscovered Markdown links were found.
Provenance: the same conversation previously completed all 28 API pages (Python by the main agent, C++ and ROS2 by read-only agents), including all examples and warnings. Those authored notes are reused below. This pass captured all current raw pages and hashes; re-read the 15 remaining pages in full; re-read Common/Types/ROS2/IMU/Lidar/Ultrasonic pages and checked the remaining API section lists, task-relevant field tables and warnings against the earlier full reading. Earlier raw-byte hashes do not exist, so this is semantic cross-checking, not a claim of byte equality with the earlier session. READ_COMPLETE records the combined actual review, never a download alone.
All SDK inspection, compiler/linker, hardware read-only and motion states remain independent and unverified. API headings often omit argument types; the inventory retains them as heading text and marks a missing full declaration explicitly. The complete vendor pages are kept only under gitignored `.cache/gdk/`.

## 主页
Page ID: `index.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#index.md)

SHA-256: `ffad957bdd95e2547b9614f6c86ca3608900d2a093a3f736d0048df5884efd31`

Read status: READ_COMPLETE
- **功能摘要**：GDK用于Genie机器人二次开发；概览列运动、传感器、任务、外部系统集成和教育/工业/服务等场景。
- **重要约束**：没有逐项API声明；支持语言说明不是SDK包的可用性证明。
- **相关依赖**：需实际GDK和机器人运行时才可使用硬件能力。
- **示例要点**：首页为说明文，没有可运行硬件示例。底部嵌入version.txt脚本，当前站点未观察到它发出版本请求，不能拿它当独立版本证据。
- **与本项目关系**：定义本项目外部依赖边界。
- **未解决问题**：SDK获取授权、许可、固件兼容矩阵NOT DOCUMENTED。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 快速开始 > 概览
Page ID: `contents/getting-started/quick-start.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/getting-started/quick-start.md)

SHA-256: `4b513955db0e5ae5676bf3d46c8300c86131e3095abd864a997f10a878781320`

Read status: READ_COMPLETE
- **功能摘要**：快速入门总页介绍GDK支持C++、Python、ROS2和运动/感知/建图等能力。
- **重要约束**：三个语言链接保留#hash路由，不能删去后当首页。
- **相关依赖**：具体部署步骤见语言子页。
- **示例要点**：仅三个导航入口，无额外控制示例。
- **与本项目关系**：目录覆盖入口；三个链接均指向已登记页面。
- **未解决问题**：本页没有额外版本变更说明。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 快速开始 > C++
Page ID: `contents/getting-started/quick-start/cpp.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/getting-started/quick-start/cpp.md)

SHA-256: `f2467b08f632328b6ef021fb4a10b537e9bc682fa38e08d772712dccd379ab90`

Read status: READ_COMPLETE
- **功能摘要**：机器人局域网获取GDK后，以CMake编译examples/cpp，source env.sh后运行mc_example。
- **重要约束**：目标位置为弧度；列22个关节，头部示例顺序11、13、12，和控制接口的11、12、13顺序不同。
- **相关依赖**：机器人Debug链路、安装包、CMake、GDK动态库。
- **示例要点**：CLI按关节名/目标位置成对输入；本文未执行安装脚本或运动示例。
- **与本项目关系**：C++结构参考；真实关节映射必须从实机反馈及型号配置确认。
- **未解决问题**：建议开发机地址与deploy页范围不同；不能自动采用文档示例IP或零目标。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 快速开始 > Python
Page ID: `contents/getting-started/quick-start/python.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/getting-started/quick-start/python.md)

SHA-256: `551a380a8576b9ee25b23d5e161c88cf665ccea9162f899946cd6d0d87fb9d8c`

Read status: READ_COMPLETE
- **功能摘要**：从机器人部署依赖，source环境后运行交互式mc_example.py。
- **重要约束**：a/d选关节，w/s调角，m切序列，p播放，q退出。
- **相关依赖**：GDK Python绑定及官方示例目录。
- **示例要点**：脚本来源是机器人提供的包，公开文档未提供可下载wheel。
- **与本项目关系**：仅核对语言可选项，本项目采用C++ mock。
- **未解决问题**：此页不说明退出程序是否停止已接受的硬件动作。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 快速开始 > ROS
Page ID: `contents/getting-started/quick-start/ros2.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/getting-started/quick-start/ros2.md)

SHA-256: `cbf90c806f517cdc75831ab5b9d34e991c446f5f16373ddd9c911625cd5be51b`

Read status: READ_COMPLETE
- **功能摘要**：拷贝部署包中的genie_msgs进工作空间，colcon构建后启动gdk_controller转发。
- **重要约束**：/hal/joint_state是厂商消息，不能当成sensor_msgs/JointState直接订阅。
- **相关依赖**：GDK部署包、genie_msgs、ros_env.sh、gdk_controller/controller.launch.py。
- **示例要点**：topic list/hz/echo是只读诊断示例；本次未连接硬件。
- **与本项目关系**：明确真实ROS2路径额外需要官方桥接节点。
- **未解决问题**：消息包版本、QoS、频率和DDS domain本页未给出。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 基本概念 > 混合部署
Page ID: `contents/concepts/hybrid_deploy.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/concepts/hybrid_deploy.md)

SHA-256: `a28cb7431b41f86d24eff09d06508aeaea2635790ca16eb649f780b32f5ac56a`

Read status: READ_COMPLETE
- **功能摘要**：混合部署将GDK依赖放在开发机，由外部应用通过网络使用机器人能力。
- **重要约束**：要求有线直连且IP互通；表给G02机器人与开发机示例地址。
- **相关依赖**：机器人和开发机之间可用网络、GDK依赖。
- **示例要点**：无SDK代码，只有网络模型和地址表。
- **与本项目关系**：Mac/VM运行环境与机器人SDK执行平台必须分别核验。
- **未解决问题**：传输端口、认证、DDS配置、架构兼容没有在此页说明。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 基本概念 > TF坐标变换
Page ID: `contents/concepts/transform.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/concepts/transform.md)

SHA-256: `ca4e89a7e211d009765f347aa91331d0ff0e8010eb815b26fc8c4e8c00707b9d`

Read status: READ_COMPLETE
- **功能摘要**：TF模块表达机器人各坐标系及传感器之间的变换关系。
- **重要约束**：这是简短概念页，未定义具体轴方向、缓存或外推语义。
- **相关依赖**：具体API见Python/C++ TF页。
- **示例要点**：无示例代码。
- **与本项目关系**：当前mock关节遥测不需要TF。
- **未解决问题**：设备坐标树需实际配置验证。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 如何使用 > 部署
Page ID: `contents/howto/deploy.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/deploy.md)

SHA-256: `1d5cb1f24438b752dee3dae35275ee0db07aa9898cfb82ff9a8a5eaa5744f7d3`

Read status: READ_COMPLETE
- **功能摘要**：开发机环境写Ubuntu22.04、x86_64、Intel i9及以上；从G2 Debug网口部署GDK并获取examples。
- **重要约束**：这是文档部署要求，不是对未取得的所有SDK包架构的检测结果；不得由此断言无aarch64包。
- **相关依赖**：以太网链路和机器人局域网安装/示例端点；未访问这些私网端点。
- **示例要点**：列C++/Python/ROS示例目录，安装通过机器人提供的shell脚本。
- **与本项目关系**：当前用户ARM64 Ubuntu22.04.5 VM可做mock；真实SDK平台仍UNVERIFIED。
- **未解决问题**：未提供公开SDK包、compiler/ABI、固件矩阵、版本锁定、再分发许可。开发机IP范围与quickstart示例不同。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 如何使用 > 时间同步
Page ID: `contents/howto/ptp.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/ptp.md)

SHA-256: `459874d6fe685ab5fe56f6c3d97399704352ed64bfa8376f307799e6cdad6d0c`

Read status: READ_COMPLETE
- **功能摘要**：描述ptp_server.sh机器人端和ptp_client.sh开发机端时间同步。
- **重要约束**：客户端明确不要在容器中运行；需PTP设备、linuxptp、root。文中理论纳秒精度与当前软件10ms内/一小时约50ms漂移分别描述，不可当性能保证。
- **相关依赖**：物理网卡时钟和机器人端脚本；本项目未执行这些有系统影响的操作。
- **示例要点**：server需手动停止，client同步完退出；雷达延迟文中约100ms；测传感器延迟前需同步。
- **与本项目关系**：支持本项目区分ROS、单调时钟、设备时间；不伪报硬件采样延迟。
- **未解决问题**：没有时钟epoch映射/误差认证或容器硬件时钟支持保证。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 如何使用 > C++
Page ID: `contents/howto/cpp.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/cpp.md)

SHA-256: `faabdc6482ca671cd73ab761872888f7e4435d4268e2708e82ea07b616f372a9`

Read status: READ_COMPLETE
- **功能摘要**：引入gdk/gdk.h，GDKInit后构造Robot，以JointControlReq调用JointControl。
- **重要约束**：编译和运行动态库版本必须一致；文中明确可能打印Version mismatch。不能把示例sleep(1)当连接就绪。
- **相关依赖**：GDK_HOME默认~/.cache/agibot；build_dep/cpp/x86_64或aarch64/include和lib/libgdk_adapter.so；env.sh。
- **示例要点**：CMake根据CMAKE_SYSTEM_PROCESSOR选择目录，但示例不是包文件存在或平台认证证据。
- **与本项目关系**：可选GDK构建边界的文档参考；无真实库时保持不可用入口。
- **未解决问题**：示例arm_l_joint1无idx前缀，与reference/quickstart不同；ABI/compiler与aarch64实际支持须查包。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 如何使用 > python使用
Page ID: `contents/howto/python.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/python.md)

SHA-256: `28d3fd721c559b5286bf0b113c1cdee48d497d463afb40fc90ba6b2ec58c9db0`

Read status: READ_COMPLETE
- **功能摘要**：默认Python3.10；其他版本可在提供的pybind源码目录重新构建。
- **重要约束**：系统要求Linux x86_64或aarch64、Python3.8+；这是绑定构建文档，不保证任意ARM机器受支持。
- **相关依赖**：pybind11>=2.6.0、numpy>=1.19.0、protobuf>=5.28.3，源码来自已部署GDK。
- **示例要点**：pip无隔离构建、wheel打包；示例调用gdk_init、Robot、get_joint_states，需env.sh设置路径。
- **与本项目关系**：C++优先无需更改；不能使用其他Python版wheel冒充2.6.3。
- **未解决问题**：实际包构建标签、Python ABI、底层so架构和绑定版本未检查。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 如何使用 > ROS2使用
Page ID: `contents/howto/ros2.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/howto/ros2.md)

SHA-256: `cb785b1803222b5e880c8dac4e08619b5e029a2a2fb19413df85226cd31daa36`

Read status: READ_COMPLETE
- **功能摘要**：G02默认高性能DDS，需启动官方ROS2转发节点才能发ROS消息；本页明确Humble。
- **重要约束**：控制是request/response topic；uuid用于唯一标识。示例包含JointPositionRequst拼写，不能擅自修正。
- **相关依赖**：genie_msgs、gdk_controller、ros_env.sh，生成uuid示例依赖Boost。
- **示例要点**：订阅/hal/joint_state，发布/MotionControlService/JointPosition/request；示例速度数组只有一个元素，真实长度语义仍须核实。
- **与本项目关系**：证明真实桥接是额外常驻依赖；本项目/g2接口均是自定义接口。
- **未解决问题**：与Control页CommonResponse请求类型标题冲突；QoS/domain/桥接线程和完成/停止语义未明确。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 工具 > 关节控制工具
Page ID: `contents/tools/mc_example.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/tools/mc_example.md)

SHA-256: `55064572182294ec99089076cf2f2d82121795b12f5a8b01993b2336d9c3589f`

Read status: READ_COMPLETE
- **功能摘要**：键盘控制22个关节；saved_commands目录JSON存名字和位置，多文件逐帧播放。
- **重要约束**：步长默认0.1rad、speed示例0.3；不是本项目实机安全参数。空目录/坏JSON会报错。
- **相关依赖**：GDK Python、机器人连接及动作文件。
- **示例要点**：w/s步进、a/d选关节、p下一帧、m下一文件；全列5腰3头14臂；q只写退出程序。
- **与本项目关系**：用于检查名称清单与位置单位，不复制到硬件配置。
- **未解决问题**：未证明q是急停/取消；预录零位/手工小角度不能自动认定无碰撞。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 工具 > Web相机查看器
Page ID: `contents/tools/camera_web_viewer.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/tools/camera_web_viewer.md)

SHA-256: `b9bb4aa42995ad3426ff3c3db291880c6bc32a3f898daa04a7aa9c9e41ed7796`

Read status: READ_COMPLETE
- **功能摘要**：Flask相机查看器自动探测最多9相机，以100ms刷新显示并缓存重复帧，支持深度伪彩。
- **重要约束**：UI10fps不是传感器实际10Hz采样保证；默认监听所有地址；quality范围1–100默认75。
- **相关依赖**：Python3.10+、agibot_gdk、Flask；OpenCV/NumPy可选。
- **示例要点**：支持九种枚举；可改host/port/quality/HTML刷新周期，深度做归一化JET显示。
- **与本项目关系**：本项目不引入Web服务或相机依赖，只记录全站阅读。
- **未解决问题**：原始深度值不能由伪彩恢复为可信测量；本页未说明鉴权。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## 接口文档 > Python > Common
Page ID: `contents/reference/Python/common.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/common.md)

SHA-256: `86af0f7f25ef3d7a11721eca151fd1870895e62093a56783c6e6ae4f06decb79`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/common.md)

`agibot_gdk.gdk_init()` / `gdk_release()` 无参数，返回 `GDKRes`。状态包括成功、输入无效、输出无效、运行错误、未知错误。先初始化系统再构造模块；退出时先关闭模块，再释放系统，异常路径也应清理。各模块示例中的 1–3 秒等待是文档建议，不代表已验证的连接就绪判据。

**接口清单：** `gdk_init`, `gdk_release`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** Robot/Common及ROS2 Control是后续真实后端候选证据；当前没有厂商API调用，映射与阻塞见gdk_api_mapping.md。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > Types
Page ID: `contents/reference/Python/types.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/types.md)

SHA-256: `2fbf79d3960c2f7293e251b428d0d19a93729a443a636b525b0dcd0e9277c425`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/types.md)

覆盖结果码、相机/雷达/IMU/控制组/外参枚举；Vector3、Quaternion、Pose、Twist、Wrench；Image、PointCloud、ImuData、CameraIntrinsic；关节和末端请求；地图、栅格及 TF 结构。位置通常为米，旋转为弧度，四元数字段顺序为 x/y/z/w，采样时间戳为纳秒；Vector3 的实际单位取决于所属物理量。

需交叉核对：Types 把图像和点云 data 写为 NumPy 数组，专门页面写 bytes；Image 编码/颜色在此写枚举，而 Camera 页写字符串。Types 示例使用 `Map.get_map()`，但 Map 专页未列该方法。CameraType 清单也比 Camera 专页短。不能将此概览视为完整绑定定义。

**接口清单：**

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > TF
Page ID: `contents/reference/Python/tf.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/tf.md)

SHA-256: `b6209eab2304ecb3386734407badc23950181309f2980b520cce7e2b32e76e7a`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/tf.md)

`TF` 提供九个方法：`get_all_tf_from_base_link()` 返回 TransformStamped 列表；`get_tf_from_base_link(child_frame_id)`、`get_tf_from_sensor(sensor_extrinsic_type)` 返回 Transform；`lookup_transform_latest(target_frame, source_frame, return_timestamp=False)` 始终返回二元组，第二项为 None 或纳秒时间戳；`lookup_transform(target_frame, source_frame, time_ns)` 支持历史时间插值；另有 `can_transform()`、`get_all_frame_names()`、`get_latest_timestamp(frame_id)`、`clear()`。

使用右手坐标系；查询失败需处理异常。传感器外参概述笼统写从 base_link 到传感器，但枚举和示例明确包含传感器之间的变换，方向应按具体外参核对。文档没有给出历史缓存保留范围，不能推定任意久远时间均可查询。

**接口清单：** `get_all_tf_from_base_link`, `get_tf_from_base_link`, `get_tf_from_sensor`, `lookup_transform_latest`, `lookup_transform`, `can_transform`, `get_all_frame_names`, `get_latest_timestamp`, `clear`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > Robot
Page ID: `contents/reference/Python/robot.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/robot.md)

SHA-256: `4a5d40568491e6d1c36a7e8f3f268380365ceb0c231dcf234c7dd6cda9704c0a`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/robot.md)

16 项接口分为状态读取、规划控制、伺服和末端控制。状态包括关节、全身、运动控制、末端、底盘电源、胸部电源。`get_joint_states()` 应读取 `motor_position` / `motor_velocity`，`position` / `velocity` 在本版本为预留字段。

`joint_control_request` 和 `move_head/waist/arm_joint` 到目标后返回。`joint_servo_control` 与三种 `move_*_joint_servo` 要求 100 Hz；头/腰/单臂/双臂长度为 3/5/7/14；位置须符合限位；普通模式为默认，低延时模式无碰撞保护。通用伺服的速度列表目前预留。

`move_ee_pos` 按型号要求 1、10 或 12 个状态，双末端为两倍且左侧在前；`nums=len(states)`。`end_effector_pose_control` 使用 base_link 位姿，要求 50 Hz、连续插值，无碰撞检测。控制方法一般成功返回整数 0，失败抛异常。

示例疑点：ctek90d 示例设置 0.5，超出该页规定的 [-0.91,0]；“控制周期比控制频率稍大”量纲不一致；SLERP 示例在负点积的球面插值分支仍使用原 q1，需审查，不能直接用于实机。

**接口清单：** `get_joint_states`, `get_whole_body_status`, `get_motion_control_status`, `get_end_state`, `get_chassis_power_state`, `get_chest_power_state`, `joint_control_request`, `move_head_joint`, `move_waist_joint`, `move_arm_joint`, `joint_servo_control`, `move_head_joint_servo`, `move_waist_joint_servo`, `move_arm_joint_servo`, `move_ee_pos`, `end_effector_pose_control`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** Robot/Common及ROS2 Control是后续真实后端候选证据；当前没有厂商API调用，映射与阻塞见gdk_api_mapping.md。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

**本轮补充核对：** C++/Python MotionControlStatus模式含0停止、1 G1伺服、2规划、5 G2伺服；ROS2 Control页仅列0/1/2，存在跨页缺项，不能凭模式数字授权运动。规划MoveArmJoint只展示完整14元素/双臂示例；7或14的明确长度约束属于MoveArmJointServo，不可移植到规划接口当已证实单臂语义。

## 接口文档 > Python > IMU
Page ID: `contents/reference/Python/imu.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/imu.md)

SHA-256: `5096d9628c7ffc30f9ddc78cd180d29680ff1c2e071c8009ca4433687bdc90b6`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/imu.md)

`Imu.get_latest_imu(type, timeout)`、`get_nearest_imu(type, timestamp, timeout)` 读取前/后/底盘 IMU。timeout 为毫秒，目标时间为纳秒；结果包含角速度 rad/s、加速度 m/s²、时间戳。需处理 None 与异常，结束调用 `close_imu()`，其返回 GDKRes。

页末明确 `get_imu_fps` 与 `get_imu_latency` 当前未实现，尽管正文提供了签名和示例。延迟窗口以秒计、结果以毫秒计，统计前须时间同步。概述提到方向，但 ImuData 字段并未给姿态四元数。

**接口清单：** `get_latest_imu`, `get_nearest_imu`, `get_imu_fps`, `get_imu_latency`, `close_imu`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > Camera
Page ID: `contents/reference/Python/camera.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/camera.md)

SHA-256: `6abf18df31c90fc531c3c967718c50a4ad9521919c29a5e7160573af807a48de`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/camera.md)

八项方法：`get_latest_image`、`get_nearest_image`、`get_image_shape`、`get_image_fps`、`get_image_latency`、`get_camera_intrinsic`、`set_dev_camera_config`、`close_camera`。读取接口 timeout 为毫秒；shape 顺序是宽、高；时间戳为纳秒。内参为 fx/fy/cx/cy，畸变长度随双目/RGBD/鱼眼分别为 8/5/6，不能硬编码成统一长度。

相机枚举中包含预留项，不代表均已开放。配置使用部署包的 cam_config.json；修改并调用配置接口后，还需重新切入 develop 模式。更多相机同时运行会增加性能负担。close 返回 GDKRes，其余失败抛异常；图像读取也需检查 None。图像 data 与编码字段的 Python 类型与 Types 页不一致，实际解析前须核对 SDK 绑定。

**接口清单：** `get_latest_image`, `get_nearest_image`, `get_image_shape`, `get_image_fps`, `get_image_latency`, `get_camera_intrinsic`, `set_dev_camera_config`, `close_camera`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > Lidar
Page ID: `contents/reference/Python/lidar.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/lidar.md)

SHA-256: `fdca4e9ba14c7bc435797881b2aba611dca643f03982d023c0d60852f7f65715`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/lidar.md)

`Lidar.get_latest_pointcloud(type, timeout)`、`get_nearest_pointcloud(type, timestamp, timeout)` 读取前/后雷达，timeout 毫秒、timestamp 纳秒。PointCloud 必须结合 fields 的 offset/datatype/count、point_step、row_step 与端序解析，不能假定是连续 XYZ 三元数组。示例使用 data_size，但属性表未列该项。

`close_lidar()` 返回 GDKRes。页末明确 `get_lidar_fps()` 与 `get_lidar_latency()` 当前未实现。延迟统计描述要求先时间同步；读取需兼顾 None 和异常路径。

**接口清单：** `get_latest_pointcloud`, `get_nearest_pointcloud`, `get_lidar_fps`, `get_lidar_latency`, `close_lidar`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > PNC
Page ID: `contents/reference/Python/pnc.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/pnc.md)

SHA-256: `d7b7d52a2adae1fb3204863c4495e028a9c18b92b6217f74c98f4b8f0bfe881e`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/pnc.md)

`Pnc.get_task_state()` 返回 state/message/id/type，状态 0–9 表示空闲、启动、运行、暂停中、已暂停、恢复中、取消中、已取消、失败、成功；类型 0/1/2 为闲置/导航/遥控。

`normal_navi(NaviReq)` 目标在 map；`relative_move(NaviReq)` 在 base_link，只有简单停障、无绕障，两者均注明先在 Pad 重定位。`high_precision_navi` 暂未上线。`cancel_task`、`pause_task`、`resume_task` 接受任务 ID。

遥控先 `request_chassis_control(0或1)`，分别表示阿克曼/蟹行，再 `move_chassis(Twist)`。除状态查询外，成功通常无返回、失败抛异常；发送成功不等于任务完成。示例取消阿克曼任务后直接发送蟹行速度，未展示重新申请模式 1；页末的笼统坐标系描述不能覆盖各方法的具体约定。

**接口清单：** `get_task_state`, `normal_navi`, `high_precision_navi`, `relative_move`, `cancel_task`, `pause_task`, `resume_task`, `request_chassis_control`, `move_chassis`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > SLAM
Page ID: `contents/reference/Python/slam.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/slam.md)

SHA-256: `286a5aeddfd8d2bd6b3f282f398f53e4e9cb7d42f890a2584b81c7791c32df75`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/slam.md)

七项方法：`get_slam_state()`，`start_mapping()`，`stop_mapping()`，`cancel_mapping()`，`get_odom_info()`，`record_spec_loc()`，`get_curr_pose()`。状态 1/2/0 分别对应开始/停止/取消；stop 同时保存地图。控制类成功无返回、失败抛异常；当前位姿返回 Pose，里程计返回 OdomInfo，含速度、机体速度、加速度、定位置信度及静止/打滑状态。

`record_spec_loc()` 用于充电位置，但明确暂未上线，完整示例仍调用它。字段拼写为 `is_sliping`，不能自行改成常见英语拼写。页面没有明确写出所有位姿、速度字段的参考坐标系，不应自行补充为已确认事实。

**接口清单：** `get_slam_state`, `start_mapping`, `stop_mapping`, `cancel_mapping`, `get_odom_info`, `record_spec_loc`, `get_curr_pose`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > Map
Page ID: `contents/reference/Python/map.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/map.md)

SHA-256: `8e93c91c72972ce745f6478301d20eaa6976ccc65afc8c5cbc349bb27ff0c48e`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/map.md)

只详细列出四项：`get_curr_map()` 返回 MapName；`get_all_map()` 返回 MapName 列表；`switch_map(map_id)` 与 `remove_map(map_id)` 成功无返回，失败抛异常。MapName 含 id/name/is_curr_map；文档注明底层 ID 为 uint8_t、范围 0–255。切图前不应有导航任务；删除不可逆。

与 Types 页的 `get_map()` / MapInfo 示例存在文档覆盖差异，不能仅凭 Types 示例认定完整地图读取 API 已确认可用。

**接口清单：** `get_curr_map`, `get_all_map`, `switch_map`, `remove_map`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > Interaction
Page ID: `contents/reference/Python/interaction.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/interaction.md)

SHA-256: `a1047fe45b6ec432e40e9b6bb11f8810a8d574b91ef9717645d959ae32df0537`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/interaction.md)

13 项方法覆盖语言、通话、音量、唤醒、音频、显示开关；TTS/音频/视频播放；功能状态和 ASR；注册与注销回调。通话模式自动进入/退出唤醒状态；目前回调仅支持字符串类型名 `get_asr_text`，回调参数为识别文本。视频 loop_count=-1 表示无限循环；成功通常无返回，状态查询返回 VoiceFuncStatus，ASR 返回 str。

文档说明依赖跨网段通信，给出容器需修改宿主网络及 privileged 的部署提示。本次只是记录依赖，没有执行提权或改网操作。多媒体播放示例用固定等待，没有提供完成事件或阻塞语义保证。

**接口清单：** `set_language`, `set_call_mode`, `set_volume`, `set_wakeup_switch`, `set_audio_switch`, `set_display_switch`, `play_tts`, `play_audio`, `play_video`, `get_func_status`, `get_asr_text`, `register_callback`, `unregister_callback`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > Python > UltrasonicRadar
Page ID: `contents/reference/Python/uss.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/uss.md)

SHA-256: `c3a79d07b698729918db8ab9f59ee238f0b1bee5f0c69e21a06c028a560a519a`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/Python/uss.md)

`get_latest_ultrasonic_radar()` 无参数，返回字典，含底盘传感器纳秒时间戳和测距列表；每项为 id/distance_mm/fault_state。`get_nearest_ultrasonic_radar(timestamp_ns)` 的子项明确不含 id，不能直接与 latest 使用同一解析假设。

距离为毫米，fault_state=0 为正常。另有 `get_ultrasonic_radar_fps()`、`get_ultrasonic_radar_latency(window_seconds=10.0)` 和返回 GDKRes 的 `close_ultrasonic_radar()`；统计需先积累数据。无新数据或目标时间超出范围可能抛异常。此页没有将统计方法标为未实现，不能把 IMU/Lidar 的限制泛化过来。

**接口清单：** `get_latest_ultrasonic_radar`, `get_nearest_ultrasonic_radar`, `get_ultrasonic_radar_fps`, `get_ultrasonic_radar_latency`, `close_ultrasonic_radar`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > Common
Page ID: `contents/reference/cpp/common.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/common.md)

SHA-256: `d957790c41c9d34fec1978fd2ba4c9901a2adc94f7e5b4dc96dd8552c88f2f50`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/common.md)

- `GDKInit()`、`GDKRelease()` 均无参数，返回 `GDKRes`；负责全局 DDS、配置和资源生命周期。
- 初始化应先于任何其他 GDK 功能；多线程只需一个线程初始化一次；异常退出也应释放。
- 本页列举 `kInvalidInput`、`kInvalidOutput`、`kTimeout`、`kNotInitialized`、`kAlreadyInitialized`、`kInternalError` 等状态，未给出数字值。

**接口清单：** `GDKInit`, `GDKRelease`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** Robot/Common及ROS2 Control是后续真实后端候选证据；当前没有厂商API调用，映射与阻塞见gdk_api_mapping.md。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > IMU
Page ID: `contents/reference/cpp/imu.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/imu.md)

SHA-256: `84263d266e8f41386e9f4ad4b10f93bec1e70581e8f31b3e26e983d846b73609`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/imu.md)

- `GetLatestImu(imu_type, timeout_ms, shared_ptr<ImuData>&)`；`GetNearestImu` 额外接收目标 `uint64_t timestamp_ns`。
- `ImuType` 有前部、后部、底盘三种。输出仅列角速度 `Vector3`（rad/s）、线加速度 `Vector3`（m/s²）、时间戳（ns）。概述虽提到方向，结构并未给出姿态四元数。
- `GetImuFps(imu_type, fps)`、`GetImuLatency(imu_type, window_seconds, LatencyStats&)`；延迟结构有最大、平均、P99、P99.9、P99.99，单位 ms。
- `CloseImu()` 关闭 DDS。延迟测量要求先同步时钟。
- **实现状态/疑点：页末明确 FPS 与延迟统计当前未实现；FPS 参数表为 `int&`，示例为 `float`。**

**接口清单：** `GetLatestImu`, `GetNearestImu`, `GetImuFps`, `GetImuLatency`, `CloseImu`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > Camera
Page ID: `contents/reference/cpp/camera.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/camera.md)

SHA-256: `e16351dcb429c79b0bb3cab8ae76dca6e79151bbf594f53618fc04e4afeed1e7`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/camera.md)

- `GetLatestImage(camera_type, timeout_ms, shared_ptr<Image>&)`；`GetNearestImage` 增加目标纳秒时间戳。
- `Image` 带宽高、编码（未压缩/JPEG/PNG）、颜色格式、位深、`DataView`、时间戳。支持 RGB/BGR、RGBA/BGRA、YUV/NV、灰度、Bayer、Z16 等；必须按实际编码和格式解释数据。
- `GetImageShape(camera_type, tuple<int,int>&)` 输出宽高；`GetImageFps(camera_type, float&)`；`GetImageLatency(camera_type, window_seconds, LatencyStats&)`，延迟需时间同步。
- `GetCameraIntrinsic(camera_type, CameraIntrinsic&)`：内参向量为 fx/fy/cx/cy；畸变向量长度按双目/RGBD/鱼眼分别列为 8/5/6。只支持列出的 11 个非预留相机类型，其余报错。
- `SetDevCameraConfig(const string& path)` 设置开关和 FPS；路径不存在返回无效输入。R1 与 Thor 分别使用 `r1_camera_conf.json`、`thor_camera_conf.json`。每次修改并调用后，需重新切到 develop 模式才生效。`CloseCamera()` 关闭连接。
- 常规模式只默认开放部分相机；其余建议在 develop 模式调整。开启更多相机存在性能成本；部分上下手部相机枚举标为预留。
- 疑点：默认相机清单有“左右彩色相机”措辞；内参示例把手部彩色相机归在鱼眼分支，应以设备标定和实际 SDK 数据核实。最近帧示例用时间戳 0，但本页未解释 0 的特殊语义。部分错误退出路径没有调用释放函数。

**接口清单：** `GetLatestImage`, `GetNearestImage`, `GetImageShape`, `GetImageFps`, `GetImageLatency`, `GetCameraIntrinsic`, `SetDevCameraConfig`, `CloseCamera`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > Lidar
Page ID: `contents/reference/cpp/lidar.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/lidar.md)

SHA-256: `6b096d659ed3ad102a5221221079fab8f40b70fe2ade1c8ca93ecf583e4631b5`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/lidar.md)

- `GetLatestPointCloud(lidar_type, timeout_ms, shared_ptr<PointCloud>&)`；`GetNearestPointCloud` 增加目标纳秒时间戳。类型为前/后雷达。
- 点云包含 width/height、fields、point_step/row_step、大端标志、稠密标志、DataView 和时间戳。字段含 name/offset/datatype/count；解析必须遵守字段布局、字节序和步长。
- `DataView` 区分 OWNED/BORROWED；有 `data()`、`size()`、`IsOwned()`、`Clone()`、`CreateOwnedFrom()`、`AssignOwnedData()`。跨生命周期保存借用数据需明确所有权。
- `GetLidarFps(lidar_type, float&)`、`GetLidarLatency(lidar_type, window_seconds, LatencyStats&)`、`CloseLidar()`。
- **页末明确 FPS 与延迟统计当前未实现。** 示例预先 `make_shared` 后仅检查非空、未检查获取返回值，这不足以证明数据获取成功。

**接口清单：** `GetLatestPointCloud`, `GetNearestPointCloud`, `GetLidarFps`, `GetLidarLatency`, `CloseLidar`, `DataView`, `DataView`, `DataView`, `DataView`, `operator=`, `DataView`, `operator=`, `data`, `mutable_data`, `size`, `IsOwned`, `Clone`, `CreateOwnedFrom`, `AssignOwnedData`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > TF
Page ID: `contents/reference/cpp/tf.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/tf.md)

SHA-256: `a7f438583e9f24a4be80e791cb026dd12d56d53a977d1783ec8fd67988fedf36`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/tf.md)

- `GetAllTfFromBaseLink(vector<TransformStamped>&)`；`GetTfFromBaseLink(child_frame_id, Transform&)`；`GetTfFromSensor(SensorExtrinsicType, Transform&)`。
- `TransformStamped` 有父/子 frame、变换和纳秒时间；变换含米制平移与 x/y/z/w 四元数。传感器外参枚举覆盖双目、深度/彩色、鱼眼、雷达、IMU 与末端/头部/底盘关系。
- `LookupTransformLatest(target, source, Transform&, uint64_t* optional_timestamp)` 明确返回 **source 到 target** 的变换；`LookupTransform(target, source, time_ns, Transform&)` 支持历史时间插值。
- `CanTransform(target, source)` 直接返回 bool；`GetAllFrameNames()` 直接返回字符串向量；`GetLatestTimestamp(frame, uint64_t&)` 返回 GDKRes；`Clear()` 返回 void，清空缓存。
- 本页未明确历史缓存长度、允许外推范围和历史查询超界错误，不能把“任意历史时刻”视为无限缓存保证。

**接口清单：** `GetAllTfFromBaseLink`, `GetTfFromBaseLink`, `GetTfFromSensor`, `LookupTransformLatest`, `LookupTransform`, `CanTransform`, `GetAllFrameNames`, `GetLatestTimestamp`, `Clear`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > Robot
Page ID: `contents/reference/cpp/robot.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/robot.md)

SHA-256: `0fad03dbf2304acd099c6b1aa15425ecb1be643aecd31c3c8a3866128e3df6f1`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/robot.md)

16 个主方法全部已读：

- 六类查询：`GetJointStates(JointStates&)`、`GetEndState(DualEndState&)`、`GetWholeBodyStatus(WholeBodyStatus&)`、`GetMotionControlStatus(MotionControlStatus&)`、`GetChassisPowerState(ChassisPowerState&)`、`GetChestPowerState(ChestPowerState&)`。
- 当前关节位置/速度应使用 `motor_position`/`motor_velocity`，`position`/`velocity` 是低速电机预留字段。末端状态包含左右执行器类型、名称与电机电流/温度/故障；全身状态包含控制、急停、各部位错误和末端型号；运动状态包含末端位姿、碰撞对、模式、twist/wrench。电源页细列电池 SOC/SOH、电压电流温度、电源开关及故障。
- 规划控制：`JointControl(const JointControlReq&)` 与 `MoveHeadJoint(positions, velocities)`、`MoveWaistJoint(...)`、`MoveArmJoint(positions, velocities, control_group)` 都说明到达目标后返回。头部 3 关节、腰部 5、手臂每侧 7；arm 组为左 0/右 1/双 2。请求带生命周期、名称、位置、速度、uuid/detail。
- 伺服控制：`JointServoControl(req, enable_low_latency=false)`、`MoveHeadJointServo(positions, control_period, low_latency=false)`、`MoveWaistJointServo(...)`、`MoveArmJointServo(positions, control_period, control_group, low_latency=false)`。要求 100 Hz，控制周期单位秒，关节角单位弧度，必须遵守逐关节限位；低延时模式**没有碰撞保护**。通用伺服可将机械臂和末端关节一起下发。
- `EndEffectorPoseControl(const EndEffectorPose&)`：50 Hz 连续平滑发布，不允许阶跃，无碰撞检测。位姿在 base_link 下；group 左 4/右 8/双 12（不同于关节控制 0/1/2），life_time 单位秒。
- `MoveEEPos(const JointStates&)`：group 必须 left_tool/right_tool/dual_tool；target_type 支持 omnipicker、dahuan、ctek90d、o10_t2、o12_t2；每侧关节数 1/1/1/10/12，dual 为两倍且左在前右在后；nums 等于 states.size()。夹爪范围分别为 [-0.785,0]、[0,0.025]、[-0.91,0]，开闭方向依型号不同；灵巧手必须按该版本逐关节表使用。

**文档内部疑点（静态阅读所得，尚未 SDK 编译验证）：**

1. GetJointStates 示例仍打印预留 position/velocity，与开头注意事项相反。
2. JointServoControl 对 velocities 既要求三数组等长且非空，又称预留可空；示例确实省略它。
3. 多处错误写作 `ErrorCode::kInvalidInput/kRuntimeError`，方法返回却声明 `GDKRes`。
4. MoveEEPos 使用的 JointStates 带 group/target_type，前面展示的同名结构定义缺这两项。
5. 头/腰低延时注释示例额外传入未定义 target_velocities，与参数表不符；“周期比控制频率稍大”量纲也不准确。
6. EndEffectorPoseControl 示例 main 缺初始化/释放；步数可能为 1，却计算 i/(n_steps-1)；SLERP dot<0 时通用球面公式仍使用未取反 q1，可能产生错误插值。
7. MoveArmJoint 参数表渲染破损；双臂伺服示例固定循环 14 项，不能直接改 group 就当成单臂 7 项示例。

**接口清单：** `GetJointStates`, `GetEndState`, `GetWholeBodyStatus`, `GetMotionControlStatus`, `GetChassisPowerState`, `GetChestPowerState`, `JointControl`, `MoveHeadJoint`, `MoveWaistJoint`, `MoveArmJoint`, `JointServoControl`, `MoveHeadJointServo`, `MoveWaistJointServo`, `MoveArmJointServo`, `EndEffectorPoseControl`, `MoveEEPos`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** Robot/Common及ROS2 Control是后续真实后端候选证据；当前没有厂商API调用，映射与阻塞见gdk_api_mapping.md。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

**本轮补充核对：** C++/Python MotionControlStatus模式含0停止、1 G1伺服、2规划、5 G2伺服；ROS2 Control页仅列0/1/2，存在跨页缺项，不能凭模式数字授权运动。规划MoveArmJoint只展示完整14元素/双臂示例；7或14的明确长度约束属于MoveArmJointServo，不可移植到规划接口当已证实单臂语义。

## 接口文档 > C++ > PNC
Page ID: `contents/reference/cpp/pnc.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/pnc.md)

SHA-256: `1ecb535b6e310dc87ec3ce6e12e6154af9625021be70617b8962279b81cfbc1e`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/pnc.md)

- `GetTaskState(PNCTaskState&)` 输出 id/state/type/message；状态 0 空闲、1 启动、2 运行、3 暂停中、4 已暂停、5 恢复、6 取消中、7 已取消、8 失败、9 成功；任务类型 0 空闲/1 导航/2 远控。
- `NormalNavi`、`HighPrecisionNavi`、`RelativeMove` 都接收 `const NaviReq&`（Pose + timestamp_ns），都要求事先在 G02 Pad 重定位；相对移动仅简单停障，无避障。
- `CancelTask/PauseTask/ResumeTask(uint32_t task_id)` 管理任务。导航请求成功后仍应查询任务状态确认完成。
- `RequestChassisControl(int32_t control_mode)` 表中控制请求为 0；之后 `MoveChassis(const Twist&)` 下发速度。linear.x 前后，linear.y 蟹行左右，angular.z 正为逆时针；单位 m/s、rad/s。
- 需可用地图，确认目标坐标系，等待初始化和控制权生效。
- 疑点：多数示例省略 GDKInit/Release；MoveChassis 示例使用未列出的 `get_task_state`、未声明 task_state、同作用域重复声明 twist/task_id，不能直接照抄编译。模式说明介绍阿克曼/蟹行，但未给明确的模式选择参数映射或速度指令有效期。

**接口清单：** `GetTaskState`, `NormalNavi`, `HighPrecisionNavi`, `RelativeMove`, `CancelTask`, `PauseTask`, `ResumeTask`, `RequestChassisControl`, `MoveChassis`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > SLAM
Page ID: `contents/reference/cpp/slam.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/slam.md)

SHA-256: `dca3ed1036b5180478397c19847acf098d0d43b9b3bf2889acaa7227b1375873`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/slam.md)

- `GetSlamState(uint32_t&)`：1 开始建图、2 停止、0 取消。
- `StartMapping()` 开始；`StopMapping()` **停止并保存**；`CancelMapping()` 取消；`RecordSpecLoc()` 记录当前位置，均无参返回 GDKRes。
- `GetOdomInfo(OdomInfo&)` 输出带协方差的位姿/速度、静止/打滑、定位状态/置信度、世界与本体速度、加速度、角速度、欧拉角；`GetCurrPose(Pose&)` 输出当前位姿。
- 获取里程计需要 SLAM 或 PNC 运行；全局重定位需要已完成地图。
- 疑点：Twist 结构代码显示 `struct Twist {minear{};`，明显排版/代码损坏；协方差维度与排列、定位状态/置信度数值含义未解释。

**接口清单：** `GetSlamState`, `StartMapping`, `StopMapping`, `CancelMapping`, `GetOdomInfo`, `RecordSpecLoc`, `GetCurrPose`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > Map
Page ID: `contents/reference/cpp/map.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/map.md)

SHA-256: `355b7a0da541e481ae489fb1c3a246d7d6df723d6685660a968a7a272529c8d3`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/map.md)

- `GetCurrMap(MapName&)`、`GetAllMap(vector<MapName>&)` 返回 id/name/is_curr_map。
- `SwitchMap(const uint8_t map_id)`、`RemoveMap(const uint8_t map_id)`，均返回 GDKRes；切图时应没有正在导航的任务。
- 疑点：MapName.id 标为 uint32_t，切换和删除参数却标为 uint8_t，需以 2.6.3 SDK 头文件核对。应用场景提到添加/更新/区域标记，但本页没有对应 API，不能据此推断已提供。

**接口清单：** `GetCurrMap`, `GetAllMap`, `SwitchMap`, `RemoveMap`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > Interaction
Page ID: `contents/reference/cpp/interaction.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/interaction.md)

SHA-256: `c3412d89a70526ced023f38b9aaf79e97bb490a8ee8191bd773c50a421f8982a`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/interaction.md)

- `SetLanguage(Language)` 支持中文 0、英文 1；`SetCallMode(bool)` 开启即进入唤醒、关闭退出，无需唤醒词/结束词。
- `SetVolume(const int32_t&)` 范围写作“通常 0–500”；`SetWakeupSwitch`、`SetAudioSwitch`、`SetDisplaySwitch` 接 bool。
- `PlayTts(const string& text)`、`PlayAudio(const string& path)`、`PlayVideo(path, const int32_t& loop_count)`；视频 -1 表示无限循环。
- `GetFuncStatus(VoiceFuncStatus&)` 含功能/唤醒状态、请求者、开关、中英文语音设置（音量、语速、音色、当前标记）、时间戳。功能状态 0 空闲/1 电话/2 唤醒自由问答/3 唤醒 ASR/4 播报/5 多轮/6 音频/9 异常；唤醒状态 0 未唤醒/1 倾听/2 思考/4 播报。
- `GetAsrText(string&)`；`RegisterCallback(type, function<void(const any&)>)`、`UnregisterCallback(type)`，当前只支持 `get_asr_text`，any 内承载 string；在已唤醒并识别新输入时调用。
- 页面说明跨网段通信依赖，在隔离容器场景建议 privileged；本任务仅记录，未更改任何权限或网络。
- 疑点：章节序号 10 重复；回调说明称参数 const string&，实际函数接 const any& 再 any_cast；回调线程/重入/生命周期未说明；媒体文件路径属于哪台主机和停止无限视频的明确 API 未说明。

**接口清单：** `SetLanguage`, `SetCallMode`, `SetVolume`, `SetWakeupSwitch`, `SetAudioSwitch`, `SetDisplaySwitch`, `PlayTts`, `PlayAudio`, `PlayVideo`, `GetFuncStatus`, `GetAsrText`, `RegisterCallback`, `UnregisterCallback`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > C++ > UltrasonicRadar
Page ID: `contents/reference/cpp/uss.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/uss.md)

SHA-256: `dd99ce5ccb82d2f5cbce455375c56a9c10f262fcf27925e7c6c02dfd4b50dd52`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

[官方原文](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/cpp/uss.md)

- `GetLatestUltrasonicRadar(shared_ptr<UltrasonicRadars>&)`；`GetNearestUltrasonicRadar(uint64_t timestamp_ns, shared_ptr<UltrasonicRadars>&)`，没有类型或超时参数。
- 输出为底盘传感器纳秒时间戳，加多个传感器条目：id、distance_mm（毫米）、fault_state（0 正常，非 0 故障）。最近时间超缓存范围可能失败，无新数据也可能失败。
- `GetUltrasonicRadarFps(float&)` 建议积累至少 2 秒；`GetUltrasonicRadarLatency(window_seconds, LatencyStats&)` 建议至少 10 秒；`Close()` 关闭 DDS，均返回 GDKRes。
- 本页不像 IMU/Lidar 那样标注统计未实现，但没有实机验证可用性；传感器 id 与物理位置的映射、有效量程及故障数值未提供。

**接口清单：** `GetLatestUltrasonicRadar`, `GetNearestUltrasonicRadar`, `GetUltrasonicRadarFps`, `GetUltrasonicRadarLatency`, `Close`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > ROS2 > IMU
Page ID: `contents/reference/ROS2/imu_node.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/imu_node.md)

SHA-256: `12307d270e939f59a50f1d0940a10d4f8a3ede816555ab98113baf7b9771ceeb`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

来源：https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/imu_node.md

- 功能：将惯性测量数据转发为 ROS2 消息。
- 消息：`sensor_msgs::msg::Imu`。
- 话题：前雷达 `/imu/livox_front`、后雷达 `/imu/livox_back`。底盘名称有冲突：话题表写 `/imu_chassis`，默认列表及自定义示例写 `/imu/chassis`。
- 字段说明：`header` 包含时间和坐标系；`angular_velocity` 为三轴角速度，rad/s；`linear_acceleration` 为三轴线加速度，m/s²。
- 启动配置：包 `gdk_imu`、launch 文件 `imu.launch.py`；`imu_topics` 接受逗号分隔话题列表。
- 未交代：发布频率、QoS、实际 frame_id、轴方向、姿态及协方差是否填充。不能将表格只列出三个字段理解为标准 Imu 消息只有三个字段。

**接口清单：** `/imu/livox_front`, `/imu/livox_back`, `/imu_chassis`, `/imu/chassis`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > ROS2 > Camera
Page ID: `contents/reference/ROS2/camera_node.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/camera_node.md)

SHA-256: `032f69f34782884bf09f1c09860be551bbc364d66f23c41e83401c4e232ab4e1`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

来源：https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/camera_node.md

- 功能：转发未压缩图像。
- 头部话题：`/camera/head_back_fisheye`、`/camera/head_left_fisheye`、`/camera/head_right_fisheye`、`/camera/head_stereo_left`、`/camera/head_stereo_right`、`/camera/head_color`、`/camera/head_depth`。
- 手腕深度：`/camera/hand_left_depth`、`/camera/hand_right_depth`。
- 手腕另一组话题名称存在冲突：表格为 `/camera/hand_left`、`/camera/hand_right`，说明为腕部深度相机；默认列表及示例为 `/camera/hand_left_color`、`/camera/hand_right_color`。
- 消息标题原文为 `sensor::msgs::msg::Image`；压缩相机页对照表写 `sensor_msgs::msg::Image`，前者疑似排版/命名错误。
- 字段：`header`；像素行数 `height`、列数 `width`；`encoding`；字节序 `is_bigendian`；每行字节数 `step`；原始字节数组 `data`。
- 编码示例：mono8（1 字节/像素）、mono16（2）、bayer_bggr8/bayer_rggb8（1）、bgr8/rgb8（3）、bgra8/rgba8（4）。这些是文档列举的格式，未给逐相机实际编码映射。
- 启动配置：包 `gdk_camera`、`camera.launch.py`、`camera_topics` 逗号列表；默认示例的环境脚本参数写 `gdk_camera_compress`，但自定义示例写 `gdk_camera`，需核对安装包。
- 未交代：QoS、帧率、分辨率、实际 frame_id、光学坐标约定、内参话题、深度数值单位。

**接口清单：** `/camera/head_back_fisheye`, `/camera/head_left_fisheye`, `/camera/head_right_fisheye`, `/camera/head_stereo_left`, `/camera/head_stereo_right`, `/camera/hand_left`, `/camera/hand_right`, `/camera/head_color`, `/camera/head_depth`, `/camera/hand_left_depth`, `/camera/hand_right_depth`, `/camera/hand_left_color`, `/camera/hand_right_color`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > ROS2 > Camera Compress
Page ID: `contents/reference/ROS2/camera_compress_node.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/camera_compress_node.md)

SHA-256: `4b96ec0d89f4d9b5d03a50419f1aaf0e6c7e9a86d20773ad33b28ea55d484d97`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

来源：https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/camera_compress_node.md

- 功能：转发压缩图像，消息 `sensor_msgs::msg::CompressedImage`。
- 话题共 11 个：上述 Camera 头部 7 个，另 `/camera/hand_left_color`、`/camera/hand_right_color`、`/camera/hand_left_depth`、`/camera/hand_right_depth`。文档没有为压缩消息添加 `/compressed` 后缀。
- 字段：时间/坐标头 `header`、压缩格式 `format`、压缩字节 `data`。
- 格式表列 jpeg 与 png，但正文明确当前所有压缩图像均使用 JPEG，`format = "jpeg"`。不能因表格出现 png 就宣称当前支持 PNG 输出。
- 启动配置：包 `gdk_camera_compress`、`camera_compress.launch.py`、`camera_topics` 逗号列表。
- 官方选择建议：原始分析处理使用 Camera；希望降低网络传输带宽使用 Camera Compress。
- 待核对：原始与压缩节点列出的同名话题使用不同消息类型；文档未说明能否同时运行、命名空间或 remap 方式。深度话题也在“全部 JPEG”陈述范围内，但未说明深度转换、精度和数值恢复方式。
- 未交代：QoS、帧率、JPEG 质量参数、实际 frame_id、压缩深度单位/编码。

**接口清单：** `/camera/head_back_fisheye`, `/camera/head_left_fisheye`, `/camera/head_right_fisheye`, `/camera/head_stereo_left`, `/camera/head_stereo_right`, `/camera/hand_left_color`, `/camera/hand_right_color`, `/camera/head_color`, `/camera/head_depth`, `/camera/hand_left_depth`, `/camera/hand_right_depth`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > ROS2 > Lidar
Page ID: `contents/reference/ROS2/lidar_node.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/lidar_node.md)

SHA-256: `cdb723d1ba520c30dd2700bc38a1f7968caf40a21f5337063e4dcd1772a5f7dd`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

来源：https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/lidar_node.md

- 话题：`/lidar/livox_front`、`/lidar/livox_back`；消息 `sensor_msgs::msg::PointCloud2`。
- 结构：`header` 提供时间/坐标；`height`、`width` 表示云布局；`fields` 说明每点字段；`is_bigendian`、`point_step`、`row_step`、`data` 用于解码；`is_dense` 表示是否所有点有效。
- `PointField` 包含 `name`、字节偏移 `offset`、`datatype`、元素数 `count`。类型编号 1–8 分别对应 INT8、UINT8、INT16、UINT16、INT32、UINT32、FLOAT32、FLOAT64。
- 启动配置：包 `gdk_lidar`、`lidar.launch.py`、`lidar_topics` 逗号列表。
- 文档仅以 x/y/z/rgb 举例字段名，没有承诺实际字段集合、字段偏移、点步长、坐标单位、frame_id 或时间戳细节；不应硬编码这些值。
- 未交代：QoS、发布频率、点频率、每点时间信息、去畸变处理。

**接口清单：** `/lidar/livox_front`, `/lidar/livox_back`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** 该模块已纳入全站阅读；当前mock不依赖也不实现该厂商模块。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 接口文档 > ROS2 > Control
Page ID: `contents/reference/ROS2/control_node.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/control_node.md)

SHA-256: `0e7fe905233dbea8df8491a0811b9a24b83a982e352e1edae4949d48064d7063`

Read status: READ_COMPLETE
**功能、约束、数据结构、示例和未解决问题（前序全文阅读笔记，本轮对照）：**

来源：https://support.agibot.com/?gdk_version=2.6.3#contents/reference/ROS2/control_node.md

### 末端状态

- 话题 `/wbc/motion_control_status`；类型标为 `genie_msgs::msg::MotionControlStatus.msg`。
- `header.frame_id` 默认 `base_link`，时间戳为发送时间。
- 末端名称与位姿：`frame_names`、`frame_poses`；名称由运控参数配置定义。
- 自碰撞对：`collision_pairs_1` 与 `collision_pairs_2` 对应组成 frame 名称对。
- 模式：STOP=0、SERVO=1、PLANNING=2；`error_code` 中 0 表示无错误，另有 `error_msg`。
- 还提供 `frame_twists`、`frame_wrenchs`；本页未说明其单位、参考系、数组对应规则。

### 关节状态

- 话题 `/hal/joint_state`；类型 `genie_msgs::msg::JointState`。
- 按名称数组 `name` 提供 `mode`、`position`、`velocity`、`effort`、`motor_position`、`motor_velocity`、`motor_current`、`error_code`，并带 `header`。
- 模式注释：csp=0、cst=1。
- 旋转/平移关节的位置单位 rad/m，速度 rad/s 或 m/s，关节力矩/力 Nm/N；电机电流 A。
- 错误码说明在该消息注释中仍为 TODO，不能自行解释非零码。

### 关节角控制与反馈

- 请求话题 `/MotionControlService/JointPosition/request`。正文列 `header`、`lifetime`、`joint_names`、`joint_positions`、`joint_velocities`、`uuid`、`details`。
- 请求消息标题却标为 `genie_msg::msg::CommonResponse.msg`，与请求字段明显不相符，不能据此可靠确定真实请求类型。
- 响应话题 `/MotionControlService/JointPosition/response`，类型也标为 `genie_msg::msg::CommonResponse.msg`；字段 `header`、`uint8 data`、`uuid`、`detail`。
- 请求/响应 header 注释均表示 frame_id 无用、时间戳为发送时间。
- 文档命名存在 `genie_msg` 与 `genie_msgs` 单复数不一致，且类型标题混入 `.msg` 后缀。
- 本页把 request/response 列为 Topic；名称含 Service 不能据此断定是 ROS2 service。
- 未说明：`lifetime` 单位/默认值、请求位置速度单位、`data` 状态码含义、uuid 匹配规则、超时/重试/抢占、控制频率、QoS、数组长度要求。
- 启动配置：混合部署使用 `gdk_controller` 包的 `controller.launch.py`。

**接口清单：** `/wbc/motion_control_status`, `/hal/joint_state`, `/MotionControlService/JointPosition/request`, `/MotionControlService/JointPosition/response`

**相关依赖：** 官方GDK 2.6.3部署包及对应机器人运行时；ROS2页另依赖各官方转发包及消息定义。未取得包，不推断安装或ABI成功。

**本项目关系：** Robot/Common及ROS2 Control是后续真实后端候选证据；当前没有厂商API调用，映射与阻塞见gdk_api_mapping.md。

**阅读证据：** 同会话前序全文阅读＋本轮已缓存来源/方法清单/关键约束交叉核对；SDK/实机未验证。

## 附录 > 关节错误码
Page ID: `contents/appendices/joint_error_code.md`

Source: [official GDK 2.6.3 page](https://support.agibot.com/?gdk_version=2.6.3#contents/appendices/joint_error_code.md)

SHA-256: `08b65787c9f84167be7a34d29d4607b249408068451b4b2d468aecb56dba6f00`

Read status: READ_COMPLETE
- **功能摘要**：全文覆盖头腰位式故障码和手臂驱动故障/告警原因表，包括通信、跟随误差、限位、过流温、STO和急停。
- **重要约束**：头腰与手臂采用不同码表，不能混解；附录对应列出的22关节。只解释错误，不授予清故障或解除急停权限。
- **相关依赖**：准确型号、对应固件、实际error_code与错误归属。
- **示例要点**：无控制代码。头腰0x4欠压原因却写超过阈值；0xF000通信丢帧与其他位区间重叠需厂商解释。手臂0xFF32急停、0xFFFF通信丢失；告警0xE007急停。
- **与本项目关系**：错误时fail-closed与现场硬件清单参考；绝不自动恢复运动。
- **未解决问题**：组合位/错误优先级、实际固件兼容、解除流程、停止保证NOT DOCUMENTED。
- **接口清单**：无独立SDK方法声明；具体引用见本页摘要及API inventory。
- **阅读证据**：本轮完整阅读原始Markdown，覆盖至文件末尾；不是下载成功即计已读。

## Focused acquisition continuation, 2026-09-08

The existing 43-page reading record is retained; this continuation did not claim
another full 43-page read. Deployment, hybrid deployment, Python quick start and
Python usage were reread in full for acquisition. Python Common and Robot/Types
state and planning sections were rechecked for the implementation (Robot §7,
Types JointControlReq, full field tables and examples); PNC cancellation was
checked only to exclude navigation cancellation as an arm-stop substitute.
The newly checked facts and unresolved semantics are detailed in
[gdk_acquisition.md](gdk_acquisition.md) and the continuation section of
[gdk_api_mapping.md](gdk_api_mapping.md).

Actual installer GETs from Mac and VM all timed out. The official public CoRobot
page was later retrieved normally and read; it is an announcement, not another
GDK API page or SDK distribution, and is not added to the 43-page denominator.
Inventory remains 282 entries. Two Python entries now explicitly distinguish
request-field contract construction from blocked real motion dispatch.
