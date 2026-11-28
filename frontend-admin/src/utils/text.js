// One-line text of an exam timing ({reporting, last_entry, duration}), as
// printed in the three admit card timetable columns.
export function timingLabel(t) {
  return t ? [t.reporting, t.last_entry, t.duration].join(" / ") : "";
}

export function truncate(str, maxLen = 42) {
  if (!str || str.length <= maxLen) return str;
  return `${str.slice(0, maxLen - 1)}…`;
}
