import { flashHistoryGetPage, historyGetPage } from "@/api/history"
import global from '@/global'
import { showFullScreenLoading } from "@/utils/loading";
import { kmlRoiInfer } from "@/api/upload";

function getUploadImg(type) {
  if (type === '地物分类') {
    flashHistoryGetPage(1, 20).then((res) => {
      this.imgArr = (res.data.data || []).map((item, idx) => ({
        ...item,
        display_index: idx + 1,
        before_img: global.BASEURL + String(item.before_img || '').replace(/^\//, ''),
        after_img: global.BASEURL + String(item.after_img || '').replace(/^\//, '')
      }));
      this.isUpload = this.imgArr.length !== 0;
    }).catch(() => { });
    return;
  }
  historyGetPage(1, 20, type).then((res) => {
    this.imgArr = (res.data.data || []).map((item, idx) => ({
      ...item,
      display_index: idx + 1,
      before_img: global.BASEURL + item.before_img,
      after_img: global.BASEURL + item.after_img
    }));
    this.isUpload = this.imgArr.length !== 0;
  }).catch(() => { })
}

function goCompress(type, num) {
  this.historyGetPage(1, num, type).then((res) => {
    this.atchDownload(
      res.data.data.map((item) => {
        return { after_img: item.after_img, id: item.id };
      })
    );
  }).catch(() => { });
}

function upload(type, funUrl) {
  if (this.fileList.length === 0) {
    this.$message.error("请上传图片！");
    return;
  }

  const formData = new FormData();
  const isSegmentation = funUrl === 'semantic_segmentation';
  const roiYear = isSegmentation ? String(this.roiYear || '').trim() : '';
  if (isSegmentation) {
    if (!/^\d{4}$/.test(roiYear)) {
      this.$message.error("请先填写4位年份（YYYY），用于KML ROI结果命名");
      return;
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

  if (isSegmentation) formData.append("keepRawTiff", 'true');

  this.createSrc(formData).then((res) => {
    const uploadItems = res.data.data || [];
    this.uploadSrc.list = uploadItems.map((item) => item.src);

    const rawTiffPaths = Array.from(new Set(
      uploadItems
        .map((item) => item.raw_tiff_path)
        .filter((p) => typeof p === 'string' && p.length > 0)
    ));

    if (isSegmentation) {
      if (rawTiffPaths.length === 0) {
        this.$message.error("地物分类仅支持 tif/tiff 影像，请重新上传");
        return;
      }
      Promise.all(
        rawTiffPaths.map((tifPath) =>
          kmlRoiInfer({
            old_tif_path: tifPath,
            new_tif_path: tifPath,
            year: roiYear,
            device: 'cpu'
          })
        )
      ).then((results) => {
        const flashCards = [];
        let seq = 1;
        let failedCount = 0;
        const errorMessages = [];
        results.forEach((resp) => {
          const payload = resp?.data?.data || {};
          const failedTiles = payload.failed_tiles || [];
          if (Array.isArray(failedTiles) && failedTiles.length > 0) {
            failedCount += failedTiles.length;
            const errors = payload.tile_errors || {};
            const firstKey = Object.keys(errors)[0];
            if (firstKey && errors[firstKey]) {
              errorMessages.push(String(errors[firstKey]));
            }
          }
          const fids = payload.written_fid_list || payload.matched_fid_list || [];
          fids.forEach((fid) => {
            const name = `${fid}+${roiYear}.png`;
            const afterUrl = `${global.BASEURL}api/analysis/kml_roi_output/${fid}/${name}`;
            const beforeUrl = `${global.BASEURL}api/analysis/kml_roi_output/${fid}/${fid}+${roiYear}_src.png`;
            flashCards.push({
              id: seq++,
              record_id: `${fid}|${name}`,
              type: '地物分类',
              before_img: beforeUrl,
              after_img: afterUrl,
              data: {}
            });
          });
        });
        const total = flashCards.length;
        flashCards.forEach((item, idx) => {
          item.id = total - idx;
        });
        if (flashCards.length > 0) {
          this.imgArr = flashCards;
          if (failedCount > 0) {
            this.$message.warning(`Flash 部分成功：${flashCards.length} 条结果，${failedCount} 个切片失败`);
          } else {
            this.$message.success("Flash 推理完成");
          }
        } else {
          const detail = errorMessages[0] ? `：${errorMessages[0].slice(0, 120)}` : "";
          this.$message.error(`Flash 推理失败，未生成任何结果${detail}`);
        }
        this.fileList = [];
        this.getMore();
      }).catch((err) => {
        const msg = err?.response?.data?.msg || "Flash 推理失败";
        this.$message.error(msg);
      });
    } else {
      this.imgUpload(this.uploadSrc, funUrl).then(() => {
        this.fileList = [];
        this.$message.success("Pro 推理完成");
        this.getMore();
      }).catch(() => { });
    }

    if (!isSegmentation && this.uploadSrc.list.length >= 10 && type !== '场景分类') {
      this.$confirm("上传图片过多，是否压缩?", "提示", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      })
        .then(() => {
          showFullScreenLoading('#load', '压缩中')
          this.goCompress(type, this.uploadSrc.list.length)
        }).catch(() => { })
    }
    this.$refs.upload?.clearFiles?.();
  }).catch(() => { })
}

export { getUploadImg, goCompress, upload }
