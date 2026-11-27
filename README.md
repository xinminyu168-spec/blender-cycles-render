# Blender Cycles 云端渲染

P21 科幻能量场景的真实物理渲染工程。

## 部署
渲染工作流及校验文件已提交。将 `payload.part00`、`payload.part01`、`payload.part02` 上传至仓库根目录（不上传外层 ZIP）。工作流将拼接并校验 ZIP，再安装 Blender 5.0.1。

## 渲染
Actions → P21 Cycles physical rendering → Run workflow → smoke。首次仅渲染第150帧，640×360、16采样。通过后再进行三帧测试及分段高画质渲染。

注意：当前仓库为公开仓库。上传前确认愿意公开模型。工作流需手动触发，不会自动消耗渲染配额。Cycles 真实成片尚未验证。
