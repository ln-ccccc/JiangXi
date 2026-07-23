import fs from 'node:fs';
import path from 'node:path';

export class ManagedPathError extends Error {}

export function resolvePathInRoots(value, roots, label, allowedSuffixes) {
  const text = String(value || '').trim();
  if (!text) throw new ManagedPathError(`${label}不能为空`);
  if (path.isAbsolute(text) || path.basename(text) !== text || /[\\/]/.test(text)) {
    throw new ManagedPathError(`${label}只能是受控目录内的文件名`);
  }
  if (!allowedSuffixes?.includes(path.extname(text).toLowerCase())) {
    throw new ManagedPathError(`${label}文件类型不被允许`);
  }

  const allowed = (roots || []).map((root) => path.resolve(root));
  if (!allowed.length) throw new ManagedPathError(`${label}没有配置受控数据目录`);

  const existingCandidate = allowed
    .map((root) => path.resolve(root, text))
    .find((candidate) => fs.existsSync(candidate));
  if (!existingCandidate) return path.resolve(allowed[0], text);

  const resolvedCandidate = fs.realpathSync(existingCandidate);
  const resolvedRoots = allowed
    .filter((root) => fs.existsSync(root))
    .map((root) => fs.realpathSync(root));
  const isAllowed = resolvedRoots.some(
    (root) => resolvedCandidate === root || resolvedCandidate.startsWith(`${root}${path.sep}`)
  );
  if (!isAllowed) throw new ManagedPathError(`${label}必须位于受控数据目录`);
  return resolvedCandidate;
}
