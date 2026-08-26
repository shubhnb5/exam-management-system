export function truncate(str, maxLen = 42) {
  if (!str || str.length <= maxLen) return str;
  return `${str.slice(0, maxLen - 1)}…`;
}
