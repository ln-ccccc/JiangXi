import { createSrc, prePhotoHandle } from '@/api/upload'
import global from '@/global'

// 预处理状态值与后端 /api/analysis/semantic_segmentation 的校验保持一致：
// prehandle：0=无、2=CLAHE、4=锐化（图像增强，两态互斥）
// denoise：0=无、3=平滑、5=高斯滤波（降噪，两态互斥）
// 本文件方法挂在 Segmentation 实例 methods 上，勾选态一律以 this.uploadSrc
// 的状态值为唯一数据源，不再读写 $refs（拆分后 ref 已不在本实例上）。
const PREHANDLE_CLAHE = 2;
const PREHANDLE_SHARPEN = 4;
const DENOISE_SMOOTH = 3;
const DENOISE_FILTER = 5;

// 受控复选框被拒绝勾选时（状态未变化、不触发重渲染），需手动回弹 DOM 勾选态
function rejectCheckbox(event) {
  if (event?.target && event.target.checked) {
    event.target.checked = false;
  }
}

// 上传原图生成预处理预览。type 是业务类型（中文，如「地物分类」），
// /api/file/upload 按 str_to_type(type) 入库，传数字字符串会得到 None 而失败。
function requestPrehandlePreview(type, prehandleValue, previewField) {
  const formData = new FormData();
  for (const item of this.fileList) {
    formData.append("files", item?.raw || item);
  }
  formData.append("type", type);

  createSrc(formData).then((res) => {
    this.uploadSrc.list = res.data.data.map((item) => {
      return global.BASEURL + item.src;
    });
    this.before = this.uploadSrc.list.splice(0, 3);

    this.prePhoto.list = this.before;
    this.prePhoto.prehandle = prehandleValue;

    prePhotoHandle(this.prePhoto).then((res) => {
      this[previewField] = res.data.data.map((item) => {
        return global.BASEURL + item
      })
    }).catch(() => {
      // 预览失败必须可见：此前静默吞掉，勾选成功但预览区永远空白
      this?.$message?.warning?.('预处理预览生成失败')
    })
  }).catch(() => {
    // 原图上传失败同样静默过：预览区空白且无任何解释
    this?.$message?.warning?.('预处理原图上传失败，无法生成预览')
  })
}

function selectSharpen(type, event) {
  if (this.fileList.length === 0) {
    if (this.uploadSrc.prehandle === PREHANDLE_SHARPEN) {
      this.uploadSrc.prehandle = 0
    } else {
      rejectCheckbox(event);
      this.$message.error('请先上传图片')
    }
    return;
  }
  if (this.uploadSrc.prehandle === PREHANDLE_SHARPEN) {
    this.$message.success("取消锐化处理");
    this.uploadSrc.prehandle = 0
    return;
  }
  this.$message.success("锐化处理");
  // 状态驱动互斥：prehandle 置 4 后 CLAHE 复选框经 :checked 自动取消
  this.uploadSrc.prehandle = PREHANDLE_SHARPEN
  requestPrehandlePreview.call(this, type, PREHANDLE_SHARPEN, 'sharpenImg')
}

function selectClahe(type, event) {
  if (this.fileList.length === 0) {
    if (this.uploadSrc.prehandle === PREHANDLE_CLAHE) {
      this.uploadSrc.prehandle = 0
    } else {
      rejectCheckbox(event);
      this.$message.error('请先上传图片')
    }
    return;
  }
  if (this.uploadSrc.prehandle === PREHANDLE_CLAHE) {
    this.$message.success("取消CLAHE处理");
    this.uploadSrc.prehandle = 0
    return;
  }
  this.$message.success("CLAHE处理");
  // 状态驱动互斥：prehandle 置 2 后锐化复选框经 :checked 自动取消
  this.uploadSrc.prehandle = PREHANDLE_CLAHE
  requestPrehandlePreview.call(this, type, PREHANDLE_CLAHE, 'claheImg')
}

function selectFilter() {
  if (this.uploadSrc.denoise === DENOISE_FILTER) {
    this.$message.success("取消高斯滤波处理");
    this.uploadSrc.denoise = 0
    return;
  }
  this.$message.success("高斯滤波处理");
  this.uploadSrc.denoise = DENOISE_FILTER
}

function selectSmooth() {
  if (this.uploadSrc.denoise === DENOISE_SMOOTH) {
    this.$message.success("取消平滑处理");
    this.uploadSrc.denoise = 0
    return;
  }
  this.$message.success("平滑处理");
  this.uploadSrc.denoise = DENOISE_SMOOTH
}

export { selectSharpen, selectFilter, selectSmooth, selectClahe }
