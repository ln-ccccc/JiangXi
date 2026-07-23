function validateIdentifier(value, label, pattern) {
  const text = String(value ?? '').trim();
  if (!pattern.test(text)) {
    throw new Error(`${label}必须为合法整数`);
  }
  return text;
}

export function parsePositiveIdentifier(value, label = '标识') {
  return validateIdentifier(value, label, /^[1-9]\d*$/);
}

export function parseTileCoordinate(value, label) {
  return validateIdentifier(value, label, /^(0|[1-9]\d*)$/);
}
