import fs from 'fs';
import path from 'path';

export function saveKmlUpload({ uploadRoot, filename, content }) {
  const originalName = String(filename || '').trim();
  const safeName = path.basename(originalName);
  if (!safeName.toLowerCase().endsWith('.kml')) {
    throw new Error('只支持 .kml 文件');
  }

  const text = String(content || '');
  if (!text.trim()) {
    throw new Error('KML 内容不能为空');
  }

  const resolvedRoot = path.resolve(uploadRoot);
  fs.mkdirSync(resolvedRoot, { recursive: true });
  const target = path.resolve(resolvedRoot, safeName);
  if (!target.startsWith(resolvedRoot + path.sep) && target !== resolvedRoot) {
    throw new Error('KML 文件名非法');
  }

  fs.writeFileSync(target, text, 'utf-8');
  // 返回裸文件名：提交推理走 inferencePathPolicy，只接受受控目录内的裸文件名，
  // 绝对路径会被 400「kml_path 只能是受控目录内的文件名」拒掉（上传→提交链路必断）
  return { kml_path: safeName, kml_path_absolute: target };
}
