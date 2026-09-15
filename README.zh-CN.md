# G2 Gazebo 与 RViz2 仿真：逐步操作说明

[English delivery README](README.md)

## 克隆与验收入口

```bash
git clone https://github.com/langchengg/g2-gazebo.git
cd g2-gazebo
```

本文档与英语版一致，仓库根目录均为 `g2-gazebo`。

## 简介

这是 Agibot G2 **仿真**应用。Gazebo Fortress 负责物理运算；RViz2 通过同一份
机器人描述与 TF 显示同一组真实仿真关节状态。两个业务节点为 Python/rclpy：

| 原题要求 | 对应实现 |
|---|---|
| 源码仓库 | 通过 Git clone 获取：`https://github.com/langchengg/g2-gazebo.git` |
| Docker / ROS 2 / 构建 | Ubuntu 22.04；原生 ARM64 已验收，原生 x86_64/amd64 可通过预检但运行尚未测试；ROS 2 Humble、普通 colcon 安装 |
| sayHello | `/g2/sayHello` 请求仿真左臂小幅往返轨迹 |
| telemetry | `/g2/telemetry` 将 Gazebo 关节测量发布到 `/g2/joint_states` |
| 安装执行文档 | 本中文说明及命令完全一致的英文 README |

真实 GDK、实机网络和实体机器人运动不在范围内。`docs/test_report_gazebo.md`
是历史验收报告，**不能作为新归档通过的证据**。包外 release receipt 才将实际
测试绑定到具体归档、源码、模型和镜像。本文不预填本轮成功，也不以 GUI 进程
存在代替真实可见和可操作的画面。

## 1. 公开前置条件与命令执行位置

本次提交的验收摘要见 [docs/validation.md](docs/validation.md)。


主机要求为 **Ubuntu 22.04 Linux**，并安装 Python 3.10、Docker Engine、
Docker Compose V2、Buildx 与 GNU Make。

对于 **Headless 验收**，不需要 X11 会话即可执行核心步骤：
`make doctor`、`make fetch-model`、`make prepare-model`、`make build-sim`、`make verify-sim`。

对于 **GUI 可视化校验**，需要有可用的图形会话：Linux 下 X11/Xorg 登录，
并满足 `XDG_SESSION_TYPE=x11`、可读 `XAUTHORITY`、`/tmp/.X11-unix`。
项目不安装桌面。

开发 VM 约有 6 GiB 内存，本轮开始时约 8 GiB 可用磁盘。这些是环境观测，
不是经测定的最低配置。首次构建建议预留 **15 GiB 磁盘**；OpenUSD 编译与 Docker
缓存还需要临时空间。构建限制为两个并行编译任务。真实峰值、耗时以本轮 receipt 为准。
`doctor` 只检查前置条件，不授予运行验收状态，因此两种架构的预检都会显示
`validation_status=NOT_TESTED`。本轮 ARM64 实际运行结果单独记录在
[docs/validation.md](docs/validation.md)；原生 amd64 仍为 **NOT TESTED**。

下面所有项目命令都在 **Ubuntu 终端**中运行，工作目录是克隆或解压后的
`g2-gazebo`；只有 GUI 路径要求从图形会话的终端启动。`sudo` 使用正常交互授权；已有获准 Docker 权限时可以省略。
不要为此修改 docker.sock 权限、sudoers、防火墙或网络。

缺少基本工具时，只安装必要工具：

```bash
sudo apt-get update
sudo apt-get install -y make python3 xauth x11-xserver-utils ca-certificates curl
```

Docker、Compose 或 Buildx 未安装时，按
[Docker 官方 Ubuntu 安装说明](https://docs.docker.com/engine/install/ubuntu/)
配置适用于 Ubuntu 22.04 和主机架构的官方软件源，安装 `docker-ce`、`docker-ce-cli`、
`containerd.io`、`docker-buildx-plugin`、`docker-compose-plugin`。先检查已有
安装再处理冲突，不直接删除别的环境。主机初始化是公开前置步骤，不代表本轮
从归档实验重新做过。ROS、RViz、Gazebo、OpenUSD 都安装在项目镜像内；
不要 `pip install rclpy`，不要更换 ROS 使用的 Python。

本次 Mac/Parallels 场景：打开 **Parallels Desktop → Ubuntu Linux → 显示**，
在 Ubuntu 图形桌面打开终端。三个仿真窗口出现在同一个可见 Ubuntu 桌面上。
普通 Linux 工作站直接使用自己的桌面。不需要浏览器 URL、SSH 隧道、noVNC
或 TCP 端口。代码中的可选无桌面 VNC 路径为 **NOT TESTED**，不是本交付主路径，
也不能代替已有可见桌面的前置条件。

## 2. 克隆、校验与进入源码目录

优先路径为 Git Clone。若另行提供了项目自定义源码归档，则应同时接收
`.tar.gz`、`.tar.gz.sha256` 和 `.tar.gz.manifest.json` 三个文件；本文档不宣称已有 Release 资产。
外部 SHA-256 验证与给定清单一致，不独立证明发布者身份。把示例路径替换成
实际收到的归档路径：

```bash
ARCHIVE='/path/to/g2-gazebo-source-<source-id>.tar.gz'
cd "$(dirname "$ARCHIVE")"
sha256sum -c "$(basename "$ARCHIVE").sha256"
tar -tzf "$ARCHIVE"
mkdir -p "$HOME/g2 simulation workspace"
tar -xzf "$ARCHIVE" -C "$HOME/g2 simulation workspace"
cd "$HOME/g2 simulation workspace/g2-gazebo"
```

使用**新的空目标目录**。归档应只有 `g2-gazebo/` 下的普通文件，不应出现绝对
路径、链接或 `..`。不要覆盖别的工程。自动 `verify-release` 会进一步检查每个
条目和文件内容后再解压。父目录包含空格是支持并纳入实验的情况。
不需要 `.git`、作者 HOME、预转换模型或作者成品镜像。

## 3. 最短完整 Quick Start（无头 + 可选 GUI）

执行 `ACCEPT_MODEL_LICENSE=yes` 前先读第 4 节模型许可。
在 Ubuntu 终端 1 中**逐行**执行；下载、工具链构建、镜像构建会占用当前终端。
无界面核验建议运行：
`make doctor` -> `make fetch-model` -> `make prepare-model` -> `make build-sim` -> `make verify-sim`，
不需要桌面环境。

如需要可视化，请额外运行：`demo-visual`，最多等待 200 秒就绪，打印 READY 后返回，但交互会话保持运行。

<!-- BEGIN QUICKSTART: docs/quickstart.commands.sh -->
```bash
# Command checklist, not an unattended demo. Run one line at a time.
# Working directory is the cloned or extracted g2-gazebo folder.
sudo make doctor
sudo make fetch-model ACCEPT_MODEL_LICENSE=yes
sudo make prepare-model
sudo make build-sim
sudo make verify-sim

# Optional visible desktop mode
sudo make sim-doctor
sudo --preserve-env=DISPLAY,XAUTHORITY,XDG_SESSION_TYPE make demo-visual
sudo make ui-info
# Look at the Ubuntu desktop first; startup has not sent any motion.
sudo make sim-hello
sudo make telemetry
sudo make check-visual
# Wait for this run_id to reach SUCCEEDED before recording another explicit motion.
sudo make record-visual
sudo make ui-down
```
<!-- END QUICKSTART -->

以上命令清单也在 `docs/quickstart.commands.sh`，它是逐步检查表，不是无人值守
动画脚本。英文和中文使用同一块命令。`verify-sim` 是无头验收步骤。`record-visual` 会明确请求**另一次**动作，
请先等待上一 run_id 结束。`ui-down` 只停止这个解压目录对应的可视化会话。

## 4. 从固定官方来源获取模型，并自行确认许可

官方 Hugging Face 数据集为 `agibot-world/GenieSimAssets`，类型 `dataset`，
固定 revision 为 **`a0813aad7c16165daffbe6c2737754e0344809ee`**，变体为
`G2_omnipicker_fixed_dual.urdf`。`model_sources/g2.lock.json` 列出 11 个输入文件，
总大小 **59,390,249 bytes**，包括 URDF/config、USD 入口与引用的配置 layers、
来源 README 和 LICENSE。只下载该固定小子集，不下载整个 Genie Sim 数据集，
也不采用 GitHub 中许可不同的 G2 资产。

先读[固定版本来源许可](https://huggingface.co/datasets/agibot-world/GenieSimAssets/blob/a0813aad7c16165daffbe6c2737754e0344809ee/LICENSE)
及 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)。
**接收者本人**需要确认用途合规，包括非商业限制；作者或先前用户的确认不能
替你确认。参数 `ACCEPT_MODEL_LICENSE=yes` 将对当前 lock 的确认保存到本地缓存。
分发改编资产时保留署名及适用 ShareAlike 条件；不要未经核查公开包含模型的镜像。

```bash
sudo make fetch-model ACCEPT_MODEL_LICENSE=yes
```

首次输出 `FETCHED` 和每个固定相对路径，原文件在 `.artifacts/gazebo-model/raw/`，
`acquisition.json` 记录大小/hash。校验过的缓存重跑输出 `CACHED`。
损坏缓存会先隔离再重新下载；错误大小/hash、HTML/LFS 指针和授权错误明确失败，
网络重试有界。正常公开 HTTPS 不依赖作者 token 或浏览器会话。若提供方改变
访问规则，按实际授权要求处理，不绕过。首次耗时取决于网络及构建速度，不承诺
固定几分钟完成。

## 5. 在 Linux 自动转换和验证

```bash
sudo make prepare-model
python3 scripts/prepare_model.py --help
sudo python3 scripts/prepare_model.py --check-only
```

`prepare-model` 自动构建独立 `Dockerfile.model-tools`，使用固定官方 OpenUSD
源码及锁定转换依赖。不需要 Linux ARM64 wheel，不需要 Mac 代转。镜像构建中
执行真实 Python import 与内存 USD 最小模型检查。转换容器无网络，只读挂载
源码/原始输入，写入新的输出目录；ROS Humble Python 不被更换。
`make model-tools` 可先独立构建工具镜像，不依赖成品仿真镜像或生成模型，
因此没有构建顺序循环。

默认生成 `.artifacts/gazebo-model/generated/`，包含 `g2.urdf`、106 个 OBJ 及
配套 MTL、`joint_inventory.json`、`conversion.json`、来源署名和
`generated_manifest.json`。验证文件集合/hash、converter/lock 身份、准确的左臂七关节、
以 world 为根的连通关节树、非任务关节冻结方式和 URDF/OBJ/MTL 引用闭合性。
流程保留源法线、惯性和碰撞，自动应用记录的同源附件变换，把未使用的渲染器
专用着色系统简化为常量漫反射 MTL。

在另一个空输出目录重复转换：

```bash
sudo python3 scripts/prepare_model.py --output "$PWD/.artifacts/gazebo-model/generated-second"
sudo cmp .artifacts/gazebo-model/generated/generated_manifest.json \
  .artifacts/gazebo-model/generated-second/generated_manifest.json
```

manifest 不同应排查，不能随意忽略几何差异。确实改变源码/converter 时保留旧
输出，使用 `--output` 选择新目录。不能从旧镜像复制网格来冒充冷转换。
两次转换可能字节一致，这不意味着 Docker 镜像或不同主机的物理轨迹每个浮点数
都一致。

## 6. 构建、安装验证及离线边界

```bash
sudo make build-sim
sudo make sim-doctor
```

`Dockerfile.sim` 用 digest 固定 Humble/Jammy 基础镜像，按官方固定 commit 构建
缺失的集成组件，实际执行普通 `colcon build` 及安装后的入口/share 资源检查。
RViz2 和图形依赖在构建阶段安装，保留软件包清单与源码 hash。
镜像名和常驻项目身份由解压目录派生，使多个副本互相隔离；镜像源码不匹配会
明确拒绝，不能悄悄用旧版本。

首次下载及工具/仿真镜像构建需要连接官方依赖来源。完成后，可视化会话与
`verify-sim` 使用 Docker `--network none`、本地安装的 world 和只读模型挂载
`/opt/g2-model`；不再向 HF、Fuel 或私人端点取模型。模型不包含在源码归档，
也不公开推送含模型镜像。build context 仅为解压目录，不 COPY 父目录。

`sudo make rebuild-sim` 为明确无缓存重建，可能消耗较多磁盘和时间。
不要清理其他项目来凑空间。诊断 Docker 命令时使用本次构建/会话报告的镜像名，
不要使用历史固定 tag。

## 7. 看见真正的 Gazebo、RViz 和实时状态

先在 **Ubuntu 图形终端**检查：

```bash
printf 'DISPLAY=%s\nXAUTHORITY=%s\n' "$DISPLAY" "$XAUTHORITY"
test -r "$XAUTHORITY"
xauth -f "$XAUTHORITY" info
xrandr --current
sudo --preserve-env=DISPLAY,XAUTHORITY,XDG_SESSION_TYPE make demo-visual
sudo make ui-info
```

已有桌面至少设为 1280×800，建议 1600×900。启动器只复制所选 display 的
认证 cookie 到权限 0600 的会话文件，并挂载该文件与 X11 socket；不打印 cookie，
不关闭 X 访问控制，不挂整个 HOME，不发布端口，不改网络。
秘密文件不进入源码归档，`ui-down` 删除会话副本。

应同时看到左侧 Gazebo、右侧 RViz、底部 **G2 Live State**。Gazebo 显示完整固定
底座 G2；RViz Fixed Frame 为 `world`，RobotModel 订阅
`/g2/sim/robot_description`，默认视角显示同一模型。Grid/TF 已配置，无需手工添加。
状态区包含 backend、仿真时间、源数据年龄、目标关节名、实际位置、run_id、终态。
它是可选观察工具，不是第三个业务控制节点。

Mac 用户在 Parallels 的 **Ubuntu Linux 可见窗口**中操作；Linux 工作站直接操作
桌面。在 Gazebo 中，左键拖动平移；Shift＋左键拖动或中键拖动旋转；滚轮缩放，
右键拖动也可缩放。在预配置的 RViz Orbit 视角中，左键拖动旋转，滚轮缩放。
拖动前把鼠标移到场景内部。参见
[Gazebo 相机操作说明](https://gazebosim.org/docs/fortress/gui/)。
不使用 Gazebo 模型编辑或传送功能。
相机变化不应改变关节测量。关闭/重新打开 Parallels 的显示窗口不重建容器、不
发送动作。停止整个会话请用 `ui-down`，不要单独关闭被监督的 GUI 窗口。
重新启动会话会恢复打包的默认视角/布局，并建立新世界。

READY 只证明进程/服务就绪；真实非黑屏 G2、交互和同世界同步还需肉眼检查及
`check-visual`/录屏证据。启动时不自动执行唯一一次演示动作。

## 8. 触发动作与查看真实关节测量

使用终端 1，或打开 Ubuntu 终端 2 并进入**同一解压目录**。
点击 G2 Live State 的 **Say hello**，或运行：

```bash
sudo make sim-hello
sudo make telemetry
sudo make check-visual
```

同一次动作选一种触发方式，不要按钮/命令同时发。响应给出 accepted/run_id；
accepted 只是接受请求。应看到同一 run_id 的 RUNNING，然后 SUCCEEDED：约
**0.05 rad** 偏移，再用约 **6 秒仿真时间**返回，其余受控关节保持测量基线。
VM 慢时墙钟时间更长，应查看仿真/墙钟频率和实时因子，不能仅看秒表。
执行中重复请求被拒绝，不累计队列。

`make telemetry` 输出当前状态快照及一条真实公开 JointState，然后返回；桌面
状态区持续更新。`check-visual` 只读比对 raw/public 同时间样本、实际描述和 TF/FK，
本身不能替代像素可见证明。查看同一容器中的 ROS 原始接口：

```bash
CONTAINER=$(sudo python3 -c 'import json; print(json.load(open(".artifacts/visual-session.json"))["container"])')
sudo docker exec "$CONTAINER" /opt/demo/docker/sim-entrypoint.sh ros2 topic info -v /g2/sim/joint_states
sudo docker exec "$CONTAINER" /opt/demo/docker/sim-entrypoint.sh ros2 topic echo /g2/sim/joint_states --once
sudo docker exec "$CONTAINER" /opt/demo/docker/sim-entrypoint.sh ros2 topic echo /g2/hello_status --once --qos-durability transient_local
```

唯一 robot_state_publisher 消费 Gazebo broadcaster，不启动 mock 或
joint_state_publisher_gui。应用、RSP、控制器、RViz、观察器均为
`use_sim_time=true`，唯一 Gazebo→ROS 桥接发布 `/clock`。

| 接口 | 类型 / QoS / 含义 |
|---|---|
| `/g2/say_hello` | `std_srvs/srv/Trigger`，仅表示接受请求 |
| `/g2/hello_status` | String JSON，reliable/transient-local；run_id、状态、原因、实际命令及结果 |
| `/g2/sim/arm_controller/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` |
| `/g2/sim/joint_states` | `sensor_msgs/msg/JointState`，真实 broadcaster；订阅 best-effort/volatile |
| `/g2/joint_states` | JointState，reliable/volatile；保留源 stamp，目标 10 Hz 仿真频率 |
| `/g2/telemetry_health` | String JSON，来源健康状态、仿真/墙钟频率及 RTF |
| `/g2/sim/robot_description` | String，reliable/transient-local，同一生成 URDF |
| `/tf`、`/tf_static` | 动态/静态变换，连通 world；静态 TF transient-local |
| `/clock` | 唯一 Gazebo 来源的单向仿真时钟 |

角度单位 rad，速度 rad/s。目标为左臂七关节中的 `idx22_arm_l_joint2`，按 JointState
`name` 查找，不猜数组索引。关键参数仅启动时配置，`sim-hello` 不修改启用参数。
成功需要控制器结果与独立反馈的偏移、返回和稳定性判定。0.05-rad 测试要求
峰值 0.04–0.06 rad、返回/其他关节误差小于 0.002 rad，并保留平滑性检查；
双 GUI 的负载不能放宽这些阈值。

## 9. 录屏、测试与独立归档复现

```bash
sudo make record-visual
sudo make ui-down
sudo make test-sim
sudo make verify-sim
```

`record-visual` 录制**当前已有同屏桌面**，保持原始墙钟播放速度，明确通过
已有服务请求另一次动作，并运行 TF/运动关联检查，不启动第二个 simulator。
录制时不要让无关或私密窗口出现在该桌面。命令在录制/检查后返回，会话仍需
`ui-down` 停止。输出目录由 `ui-info` 提供，包含
`record-*/gazebo-rviz-state.mp4`、截图、`media.json`、`tf-correlation.json`、
`motion/result.json`、源 CSV、目标轨迹 CSV、JUnit 和录制/清理日志。
全程近黑的录像会失败，并留下 `capture-quality.json`；请唤醒/解锁 Ubuntu 桌面，
在新的输出目录重新录制。该检查在录制后执行，因此请求的动作可能已经发生。
非黑录像仍须实际检查模型、运动和交互，不能仅凭非黑就记 GUI PASS。

`test-sim` 包含原软件回归和真实物理故障检查。`verify-sim` 创建新容器、世界状态、
Transport partition 和 run_id，外网隔离，不占用常驻 UI 的会话。证据在
`.artifacts/gazebo/<execution-id>/`。小 VM 测量 headless 性能前先停 UI。
所有等待都有截止时间，错误保留非零退出码。`sim-hello` 被服务拒绝时退出 **2**；
普通禁用运动的 `sim-up` 下这是预期拒绝，不是动作被接受的证据。

打包并运行冷复现实验：

```bash
sudo make package-source
# Set ARCHIVE to the exact path printed above; keep its two sidecar files beside it.
ARCHIVE='/absolute/path/to/g2-gazebo-source-<source-id>.tar.gz'
sudo make verify-release ARCHIVE="$ARCHIVE" ACCEPT_MODEL_LICENSE=yes
```

打包收录 allowlist 内尚未提交/未跟踪的源码及两份 README；排除 `.git`、原始/
生成模型、成品镜像、构建产物、凭据、旧 `.artifacts`。生成外置 checksum/manifest，
拒绝覆盖已有归档。`verify-release` 在系统临时目录下创建新的
`g2 release .../g2-gazebo`（含空格），使用新的 HOME、Docker 客户端配置及
model/XDG/HF/pip cache；选择本地 Unix Docker daemon 和系统安装的 CLI 插件，
不复制作者凭据。执行冷
下载、Linux 双转换、无缓存仿真镜像构建、回归和独立 verify。
公开 Docker 基础/工具链缓存可复用；不得挂载旧模型、生成输出或旧工程。
这是已有 Linux 主机上的隔离复现，不是重装操作系统。

包外 `acceptance/receipt.json` 绑定归档与解压源码 hash。
`SOFTWARE_PASS_GUI_PENDING` **不是完整可视化通过**。进入输出的新解压目录，
继续 demo-visual、真实交互、record-visual、ui-down 和校验缓存重启，在冻结源码
包外追加同一 hash 的实际验收记录。代码或 README 若需要修复，应重新打包，并
对新包复核受影响流程；不能改名套用旧 receipt。随包另给的 README 应与归档内
字节一致。

## 10. 停止和重启

```bash
sudo make ui-down
sudo --preserve-env=DISPLAY,XAUTHORITY,XDG_SESSION_TYPE make demo-visual
sudo make ui-info
# No action has been sent by restart. Trigger explicitly when ready.
sudo make ui-down
```

`ui-down` 只停止/移除记录的本项目容器，检查所拥有进程的清理，删除显示 cookie
副本。本模式不暴露端口；不会关闭用户桌面、删除模型、镜像或证据。
即使没有剩余进程，组件异常退出仍会报错；停止返回非零时，请查看本次证据目录
中的 `cleanup.json`。RViz 从会话内的默认配置副本启动，窗口尺寸在渲染前设置；
Gazebo 使用 Mesa `llvmpipe`，仅 RViz 使用 Mesa `softpipe`。开发过程中，
llvmpipe 出现退出崩溃；单独使用 softpipe 虽通过短诊断，随后仍在较长会话退出时卡住。
因此，已安装的 `agibot_g2_visual_tools/rviz2_close_order` 入口会在处理 Qt Close
事件之前及应用退出之前停止 RViz 更新定时器。它仍使用官方 RViz 应用、显示组件、
ROS 信号与渲染库，不替换关节数据、不动画驱动机器人，也不掩盖异常退出码。
Mesa/Xorg 底层故障尚未完全确定；与归档绑定的验收和退出结果写在包外 receipt。
小型入口改造及上游 BSD 署名包含在 `src/agibot_g2_visual_tools`。
本 VM 先前双 GUI 测量中，RViz 约 1 fps（约每 1–1.6 秒可见一次姿态更新），
动作实时因子为 0.81–0.89。画面存在可见滞后，能够交互但不是流畅动画；
该归档的实际测量请查看最终 receipt。控制、TF 和动作容差保持不变。
实际能力分别记录在 `rviz-opengl.txt` 和 `opengl.txt`，不使用 OpenGL 版本覆盖。
已安装的默认配置保持不变，重启恢复默认视角。
日常启动复用校验过的模型/镜像，不必重新下载构建。没有会话时再次 ui-down 会
明确报错，不能作为清理成功测试。普通 `make sim-up` 仍是禁用运动的 headless
模式，以 `make sim-down` 停止。历史 make up/test/verify 保持数值 mock 的原含义，
mock PASS 不能当成 Gazebo PASS。

## 11. 故障排查

| 症状 | 检查命令/位置 | 原因与修复 |
|---|---|---|
| 模型大小/hash 错误 | 下载错误、lock；重跑 make fetch-model | 查看隔离的坏缓存；保留固定版本和 TLS，不改 main/latest |
| 下载超时/403 | 官方来源的实际 HTTP 错误 | 仅有界重试；需要时正常授权，不猜 token |
| OpenUSD 编译/import/ABI 失败 | make model-tools 的首个错误、解释器/模块路径 | 使用固定原生工具镜像；不改 wheel 标签、不改为 Mac 代转 |
| 空格路径/挂载不存在 | 检查日志中的模型/镜像；变量加双引号 | 在解压目录运行，不手拆 Docker mount 字符串 |
| Docker 权限不足 | sudo docker version；sudo make doctor | 正常 sudo；不把 docker.sock 改为全局可写 |
| 内存/磁盘不足 | free -h；df -h .；sudo docker system df | 停本项目会话/构建；只清理审阅过的可再生产物，不删旧成果 |
| DISPLAY/XAUTHORITY 缺失 | printf、test -r、xauth info | 从已有 Ubuntu 图形终端启动，sudo 只保留这两个变量 |
| 无 clock/controller 未 active | ui-info 的证据目录、simulation.log | 检查 plugin/spawner/命名；等实际 READY，不能固定 sleep 代替 |
| RViz 无模型/TF | make check-visual；rviz2.log；robot_description topic | 使用打包配置、world frame、正确命名空间/QoS，不加假状态发布器 |
| 黑屏/空画面 | opengl.txt、gazebo-gui.log、rviz2.log | 验证 Mesa/OpenGL 与 X 授权；窗口 PID 不证明渲染成功 |
| 动作较慢 | 仿真时间、源年龄、墙钟速率/RTF | 软件渲染有开销；减轻无关负载，不能放宽动作正确性 |
| 服务未就绪/重复请求 | ui-info；等待 READY/终态 | 不另起世界，不自动重试结果不明确的动作 |
| 存在已停止会话 | ui-info 后 ui-down | 先清理记录的会话，再启动；工具核验归属 |
| noVNC/WebSocket/localhost 混淆 | 主路径不发布任何 TCP 端口 | 打开 Parallels Ubuntu 桌面，不访问浏览器 localhost；VNC 未验收 |
| 单独关闭某个 GUI | 查看 container 日志；ui-down | GUI 受监督；重启整个会话恢复默认布局 |

## 12. 仿真假设和参考资料

底座在 world 上固定并抬高 0.04 m，左臂七关节保留控制；非任务活动关节冻结在
已记录源姿态。保留原惯性和碰撞；同源附件变换、法线接缝、退化面处理均有转换
记录，渲染器专用材质简化为漫反射。标准 Gazebo 位置控制是仿真近似，不是经
标定的 G2 电机模型。不实现全身平衡、导航、抓取规划，也不据此宣称 GDK 兼容
或实体机器人碰撞安全。

Gazebo 场景和太阳光阴影默认关闭，用于缓解 Ogre 1 / Mesa 下实测的间歇性表面
渲染异常。该显示设置保留网格几何、照明、重力和碰撞。底层渲染原因尚未确定；
此缓解措施的验收结果另行记录，并绑定最终源码归档。

详见 `docs/model_sources.md`、`docs/simulation_assumptions.md`、
`docs/reproduction_gap_audit.md`。旧仅录屏流程保留在
`docs/README_gazebo_recording_historical.md`，不是本轮新手主流程。
本次增量实现核对的官方参考：
[Humble/Fortress 配套](https://gazebosim.org/docs/fortress/ros_installation/)、
[Fortress 图形排错](https://gazebosim.org/docs/fortress/troubleshooting/)、
[Humble robot_state_publisher](https://github.com/ros/robot_state_publisher/blob/humble/README.md)、
[OpenUSD 源码](https://github.com/PixarAnimationStudios/OpenUSD)、
[Docker Ubuntu 安装](https://docs.docker.com/engine/install/ubuntu/)。
