import { flashHistoryGetPage, historyGetPage } from "@/api/history";
import global from "@/global";
import { ElNotification } from "element-plus";
import { showFullScreenLoading } from "@/utils/loading";
import { kmlRoiInfer } from "@/api/upload";

const JIANGXI_INFERENCE_DEVICE = String(
  process.env.VUE_APP_JIANGXI_INFERENCE_DEVICE || "cpu"
)
  .trim()
  .toLowerCase();

// P1-4（2026-09-19 审查）：整图推理为同步长请求，跨 VPN/反代/系统休眠断链时
// axios 错误无 response，而后端子进程仍在执行并最终落盘——不得与真实推理
// 失败混为「未生成任何结果」，否则用户按提示重试只会撞跨进程锁
const DISCONNECT_MESSAGE =
  "连接已中断，任务可能仍在后端执行，请稍后刷新历史查看结果";

// F2（2026-09-19 审查）：与后端 P1-3 同口径的上传预检上限
const MAX_PER_FILE_BYTES = 8 * 1024 ** 3; // 单文件 8GB（后端 MAX_UPLOAD_TIFF_SIZE_MB=8192MB）
const MAX_TOTAL_BYTES = Math.floor(8.5 * 1024 ** 3); // 请求体 8.5GiB（后端 MAX_CONTENT_LENGTH）

// 上传取消控制器（模块级：路由切换不失效，与 F5 running 守卫同源思想）
let activeUploadAbort = null;

function notifyCancellableUpload(onCancel) {
  try {
    const notification = ElNotification({
      title: "影像上传中",
      message: "点击本通知取消本次上传",
      type: "info",
      duration: 0,
      onClick() {
        onCancel();
        notification.close();
      },
    });
  } catch (_) {
    // 通知组件不可用时降级为不可取消（上传本身不受影响）
  }
}

function getUploadImg(type) {
  const requestId = (this._flashHistoryRequestId || 0) + 1;
  if (type === "地物分类") this._flashHistoryRequestId = requestId;

  if (type === "地物分类") {
    return flashHistoryGetPage(1, 20)
      .then((res) => {
        if (requestId !== this._flashHistoryRequestId)
          return { status: "stale" };
        this.imgArr = (res.data.data || []).map((item, idx) => ({
          ...item,
          display_index: idx + 1,
          before_img:
            global.BASEURL + String(item.before_img || "").replace(/^\//, ""),
          after_img:
            global.BASEURL + String(item.after_img || "").replace(/^\//, ""),
        }));
        this.isUpload = this.imgArr.length !== 0;
        return { status: "success", resultCount: this.imgArr.length };
      })
      .catch((err) => {
        if (requestId !== this._flashHistoryRequestId)
          return { status: "stale" };
        const msg =
          err?.message || err?.response?.data?.msg || "地物分类历史加载失败";
        setAnalysisRunState(this, "error", msg);
        this.$message?.error?.(msg);
        return { status: "error", error: err };
      });
  }
  return historyGetPage(1, 20, type)
    .then((res) => {
      this.imgArr = (res.data.data || []).map((item, idx) => ({
        ...item,
        display_index: idx + 1,
        // F7（2026-09-19 审查）：与 flash 分支同款守卫——字段异常不出
        // "undefined" URL，前导斜杠去掉避免跨代理多一跳 308
        before_img:
          global.BASEURL + String(item.before_img || "").replace(/^\//, ""),
        after_img:
          global.BASEURL + String(item.after_img || "").replace(/^\//, ""),
      }));
      this.isUpload = this.imgArr.length !== 0;
      return { status: "success", resultCount: this.imgArr.length };
    })
    .catch((err) => {
      const msg =
        err?.message || err?.response?.data?.msg || "分析历史加载失败";
      this.$message?.error?.(msg);
      return { status: "error", error: err };
    });
}

function goCompress(type, num) {
  this.historyGetPage(1, num, type)
    .then((res) => {
      this.atchDownload(
        res.data.data.map((item) => {
          return { after_img: item.after_img, id: item.id };
        })
      );
    })
    .catch(() => {});
}

// F5（2026-09-19 审查）：running 守卫提升为模块级单例——实例字段随路由
// 切换丢失，旧页面的 8GB 上传未结束即可从新页面再发起一组并发上传
let moduleRunState = "idle";

function setAnalysisRunState(context, state, message) {
  moduleRunState = state;
  if (!context || !("analysisRunState" in context)) return;
  context.analysisRunState = state;
  context.analysisRunMessage = message;
}

function upload(type, funUrl) {
  // 运行中重入守卫：上传阶段走 requestfile 无全屏锁，可再次点击按钮，
  // 会并发起两组推理子进程并交叉写共享产物目录。
  // F5：同时检查模块级状态，防止路由切换后实例字段丢防守卫失效
  if (
    this.analysisRunState === "running" ||
    moduleRunState === "running"
  ) {
    this.$message.warning("当前已有分析任务在执行，请等待完成。");
    return Promise.resolve({ status: "error", reason: "busy" });
  }
  if (this.fileList.length === 0) {
    setAnalysisRunState(this, "error", "请先选择 tif / tiff 影像。");
    this.$message.error("请上传图片！");
    return Promise.resolve({ status: "error", reason: "missing_files" });
  }

  const formData = new FormData();
  const isSegmentation = funUrl === "semantic_segmentation";
  const roiYear = isSegmentation ? String(this.roiYear || "").trim() : "";
  if (isSegmentation) {
    if (!/^\d{4}$/.test(roiYear)) {
      setAnalysisRunState(
        this,
        "error",
        "请先填写四位年份（YYYY），用于 KML ROI 结果命名。"
      );
      this.$message.error("请先填写4位年份（YYYY），用于KML ROI结果命名");
      return Promise.resolve({ status: "error", reason: "invalid_year" });
    }
  }

  formData.append("type", type);
  // 地物分类默认开启大图切分，不再提供按钮
  if (isSegmentation) {
    formData.append("isSlice", true);
  } else if (this.isSlice) {
    formData.append("isSlice", this.isSlice);
  }

  for (const item of this.fileList) {
    const rawFile = item?.raw || item;
    if (!rawFile) continue;
    formData.append("files", rawFile, rawFile.name);
  }

  if (isSegmentation) formData.append("keepRawTiff", "true");

  // F2：上传前本地预检——选 9GB 文件此前要整包传完才被后端拒（file.size 现成没用）
  const sizedFiles = this.fileList.map((item) => item?.raw || item).filter(Boolean);
  const oversized = sizedFiles.find((f) => Number(f.size) > MAX_PER_FILE_BYTES);
  if (oversized) {
    const oversizeGb = (Number(oversized.size) / 1024 ** 3).toFixed(1);
    setAnalysisRunState(
      this,
      "error",
      `单个文件 ${oversizeGb}GB 超过 8GB 硬上限，请拆分或裁剪后重试。`
    );
    this.$message.error(`单个文件超过 8GB 硬上限（${oversizeGb}GB）`);
    return Promise.resolve({ status: "error", reason: "file_too_large" });
  }
  const totalBytes = sizedFiles.reduce((sum, f) => sum + (Number(f.size) || 0), 0);
  if (totalBytes > MAX_TOTAL_BYTES) {
    setAnalysisRunState(this, "error", "文件总大小超过单次上传上限 8.5GB，请分批上传。");
    this.$message.error("文件总大小超过单次上传上限 8.5GB，请分批上传");
    return Promise.resolve({ status: "error", reason: "total_too_large" });
  }

  if (typeof AbortController !== "undefined") {
    // 新上传开始前取消上一轮残留请求（模块级控制器，路由切换不失效）
    activeUploadAbort?.abort();
    activeUploadAbort = new AbortController();
  }
  const abortController = activeUploadAbort;
  const onUploadProgress = (event) => {
    if (!event?.total) return;
    const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
    setAnalysisRunState(
      this,
      "running",
      `正在上传影像（${percent}%），完成后执行同步 ${JIANGXI_INFERENCE_DEVICE.toUpperCase()} 地物分类；点击页面上方通知可取消上传。`
    );
  };
  notifyCancellableUpload(() => abortController?.abort());

  setAnalysisRunState(
    this,
    "running",
    `正在上传影像（0%），完成后执行同步 ${JIANGXI_INFERENCE_DEVICE.toUpperCase()} 地物分类；点击页面上方通知可取消上传。`
  );

  return this.createSrc(formData, {
    signal: abortController?.signal,
    onUploadProgress,
  })
    .then((res) => {
      const uploadItems = res.data.data || [];
      this.uploadSrc.list = uploadItems.map((item) => item.src);

      const rawTiffPaths = Array.from(
        new Set(
          uploadItems
            .map((item) => item.raw_tiff_path)
            .filter((p) => typeof p === "string" && p.length > 0)
        )
      );

      if (isSegmentation) {
        if (rawTiffPaths.length === 0) {
          setAnalysisRunState(
            this,
            "error",
            "地物分类仅支持 tif / tiff 影像，请重新选择。"
          );
          this.$message.error("地物分类仅支持 tif/tiff 影像，请重新上传");
          return { status: "error", reason: "missing_raw_tiff" };
        }
        this.$refs.upload?.clearFiles?.();
        return (async () => {
          const settledResults = [];
          for (const tifPath of rawTiffPaths) {
            try {
              const value = await kmlRoiInfer({
                old_tif_path: tifPath,
                new_tif_path: tifPath,
                year: roiYear,
                device: JIANGXI_INFERENCE_DEVICE,
                // 契约冻结：后端按这两个状态值执行预处理（0/2/4 与 0/3/5）
                prehandle: this.uploadSrc.prehandle,
                denoise: this.uploadSrc.denoise,
              });
              settledResults.push({ status: "fulfilled", value });
            } catch (reason) {
              settledResults.push({ status: "rejected", reason });
            }
          }

          const flashCards = [];
          let seq = 1;
          let failedCount = 0;
          let failedRequestCount = 0;
          let disconnectedCount = 0;
          const errorMessages = [];
          const backendMessages = [];
          settledResults.forEach((settled) => {
            if (settled.status === "rejected") {
              failedRequestCount += 1;
              // P1-4：无 response = 网络层断链，后端任务可能仍在执行
              if (!settled.reason?.response) {
                disconnectedCount += 1;
                errorMessages.push(DISCONNECT_MESSAGE);
                return;
              }
              errorMessages.push(
                settled.reason?.message ||
                  settled.reason?.response?.data?.msg ||
                  "影像推理失败"
              );
              return;
            }
            const resp = settled.value;
            const payload = resp?.data?.data || {};
            // no_features 语义透传：后端对该状态返回 success_api 且携带 message
            // （如 "No usable polygons in KML"），必须拼进失败提示，
            // 让用户能区分「KML 无可用图斑」与推理异常
            if (payload.message) {
              backendMessages.push(String(payload.message));
            }
            const failedTiles = payload.failed_tiles || [];
            if (Array.isArray(failedTiles) && failedTiles.length > 0) {
              failedCount += failedTiles.length;
              const errors = payload.tile_errors || {};
              const firstKey = Object.keys(errors)[0];
              if (firstKey && errors[firstKey]) {
                errorMessages.push(String(errors[firstKey]));
              }
            }
            const writtenResults = payload.written_results || [];
            writtenResults.forEach((result) => {
              if (result.unlinked) {
                // 未联动结果：清单外图斑，仅解译平台展示，无 miner 历史可删
                const fid = String(result.fid || "");
                if (!/^U[1-9][0-9]*$/.test(fid)) return;
                const files = result.files || [];
                const resultFile =
                  files.find((f) => f.endsWith("_new.png")) ||
                  files.find(
                    (f) =>
                      !f.endsWith("_mask.png") &&
                      !f.endsWith("_src.png") &&
                      !f.endsWith("_old.png")
                  );
                if (!resultFile) return;
                // 左侧固定为原始影像；_src 缺失（如拼接失败）时回退前一期分类再回退结果图
                const beforeFile =
                  files.find((f) => f.endsWith("_src.png")) ||
                  files.find((f) => f.endsWith("_old.png")) ||
                  resultFile;
                const urlBase =
                  global.BASEURL +
                  "api/analysis/kml_roi_unlinked_output/" +
                  fid;
                flashCards.push({
                  id: seq++,
                  record_id: null,
                  unlinked: true,
                  type: "地物分类",
                  before_img: urlBase + "/" + encodeURIComponent(beforeFile),
                  after_img: urlBase + "/" + encodeURIComponent(resultFile),
                  data: { fid, note: "未联动：不在江西348清单，仅此处展示" },
                });
                return;
              }
              const tbbh = String(result.tbbh || "").trim();
              const mapFid = Number(result.map_fid);
              if (!tbbh || !Number.isInteger(mapFid) || mapFid <= 0) return;
              const name = `${mapFid}+${roiYear}.png`;
              const identityPath = encodeURIComponent(tbbh);
              const afterUrl = `${global.BASEURL}api/analysis/kml_roi_output/${identityPath}/${name}`;
              const beforeUrl = `${global.BASEURL}api/analysis/kml_roi_output/${identityPath}/${mapFid}+${roiYear}_src.png`;
              flashCards.push({
                id: seq++,
                // 契约冻结：record_id 为 2 段式 `${tbbh}|${name}`，与后端
                // /api/analysis/kml_roi_history/item 删除接口的 split("|", 1) 对齐
                record_id: `${tbbh}|${name}`,
                type: "地物分类",
                before_img: beforeUrl,
                after_img: afterUrl,
                data: { tbbh, map_fid: mapFid },
              });
            });
          });
          const total = flashCards.length;
          const totalFailureCount = failedCount + failedRequestCount;
          flashCards.forEach((item, idx) => {
            item.id = total - idx;
          });
          if (flashCards.length > 0) {
            this.imgArr = flashCards;
            if (totalFailureCount > 0) {
              const partialMessage = `Flash 部分成功：${flashCards.length} 条结果，${failedCount} 个切片失败，${failedRequestCount} 个影像失败`;
              setAnalysisRunState(this, "partial", partialMessage);
              this.$message.warning(partialMessage);
            } else {
              setAnalysisRunState(
                this,
                "success",
                "Flash 推理完成，结果已加入历史记录。"
              );
              this.$message.success("Flash 推理完成");
            }
          } else {
            // 后端语义 message（no_features）优先于切片错误，帮用户区分
            // 「KML 无可用图斑」与推理异常
            const detailSource = backendMessages[0] || errorMessages[0];
            const detail = detailSource
              ? `：${String(detailSource).slice(0, 120)}`
              : "";
            // P1-4：全部失败均为断链时改用「可能仍在后端执行」提示，避免误报
            const failureMessage =
              disconnectedCount > 0 && disconnectedCount === failedRequestCount
                ? DISCONNECT_MESSAGE
                : `Flash 推理失败，未生成任何结果${detail}`;
            this.$message.error(failureMessage);
            setAnalysisRunState(this, "error", failureMessage);
          }
          this.fileList = [];
          await this.getMore();
          return {
            status:
              flashCards.length === 0
                ? "error"
                : totalFailureCount > 0
                ? "partial"
                : "success",
            resultCount: flashCards.length,
            failedCount: totalFailureCount,
          };
        })();
      } else {
        const inferencePromise = this.imgUpload(this.uploadSrc, funUrl)
          .then(() => {
            this.fileList = [];
            this.$message.success("Pro 推理完成");
            this.getMore();
          })
          .catch(() => {});

        if (this.uploadSrc.list.length >= 10 && type !== "场景分类") {
          this.$confirm("上传图片过多，是否压缩?", "提示", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          })
            .then(() => {
              showFullScreenLoading("#load", "压缩中");
              this.goCompress(type, this.uploadSrc.list.length);
            })
            .catch(() => {});
        }
        this.$refs.upload?.clearFiles?.();
        return inferencePromise;
      }
    })
    .catch((err) => {
      // F2：用户主动取消——不落入「上传失败」错误分支
      if (
        abortController?.signal.aborted ||
        err?.code === "ERR_CANCELED" ||
        err?.name === "CanceledError"
      ) {
        activeUploadAbort = null;
        setAnalysisRunState(this, "idle", "上传已取消，可重新选择影像执行分析。");
        this.$message.info("上传已取消");
        return { status: "error", reason: "upload_cancelled" };
      }
      throw err;
    })
    .catch((err) => {
      const msg = err?.message || err?.response?.data?.msg || "影像上传失败";
      setAnalysisRunState(this, "error", msg);
      return { status: "error", error: err };
    })
    .finally(() => {
      if (this.analysisRunState === "running") {
        const fallbackState = this.fileList.length > 0 ? "ready" : "idle";
        const fallbackMessage =
          this.fileList.length > 0
            ? `已就绪 ${this.fileList.length} 个文件；可重新执行同步分析。`
            : "请先选择 tif / tiff 影像。";
        setAnalysisRunState(this, fallbackState, fallbackMessage);
      }
    });
}

export { getUploadImg, goCompress, upload };
