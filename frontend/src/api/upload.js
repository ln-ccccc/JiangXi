import { requestfile } from "@/api/requestfile.js"
import {request} from "@/api/request.js"
// options 透传 axios 配置（F2：onUploadProgress 进度 / signal 取消）
export function createSrc(formdata, options = {}) {
    return requestfile({
        method: 'POST',
        url: '/api/file/upload',
        data:formdata,
        transformRequest: [function(data, headers) {
            delete headers.post['Content-Type']
            return data
        }],
        headers:{
            'Content-Type':'multipart/form-data'
        },
        ...options,
    })
}
export function imgUpload(data,funUrl){
    return request({
        method:'POST',
        url:`/api/analysis/${funUrl}`,
        data
    })
}

export function prePhotoHandle(data){
    return request({
        method:'POST',
        url:'/api/analysis/image_pre',
        data
    })
}

export function getCustomModel(model_type){
    return request({
        method:'GET',
        url:`/api/model/list/${model_type}`
    })
}

export function kmlRoiInfer(data){
    return request({
        method:'POST',
        url:'/api/analysis/kml_roi_inference',
        data
    })
}
