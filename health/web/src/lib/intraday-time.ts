import type { Intraday } from "./types";

function clock(value: number) {
  const seconds = Math.floor(value / 1000000);
  return `${String(Math.floor(seconds / 3600)).padStart(2, "0")}:${String(Math.floor((seconds % 3600) / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
export function inputTime(data: Intraday, value: number) {
  return data.timeBasis === "physical"
    ? new Date(value / 1000).toISOString().slice(0, 19) : clock(value);
}
export function axisTime(data: Intraday, value: number) {
  return data.timeBasis === "physical"
    ? `${inputTime(data, value).slice(5).replace("T", " ")} UTC` : clock(value);
}
export function parseInputTime(data: Intraday, value: string) {
  if (data.timeBasis === "physical") {
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(value)) return NaN;
    const millis = Date.parse(`${value}Z`);
    return Number.isFinite(millis) && new Date(millis).toISOString().slice(0, 19) === value
      ? millis * 1000 : NaN;
  }
  if (!/^\d{2}:\d{2}(:\d{2})?$/.test(value)) return NaN;
  const [h, m, s = 0] = value.split(":").map(Number);
  return h < 24 && m < 60 && s < 60 ? (h * 3600 + m * 60 + s) * 1000000 : NaN;
}
function offsetText(offset: number | null) {
  if (offset === null) return "UTC offset 不明";
  const total = Math.abs(offset);
  const h = String(Math.floor(total / 3600)).padStart(2, "0");
  const m = String(Math.floor(total % 3600 / 60)).padStart(2, "0");
  const s = total % 60;
  const seconds = s ? `:${String(Math.floor(s)).padStart(2, "0")}${s % 1 ? String(s % 1).slice(1) : ""}` : "";
  return `UTC${offset < 0 ? "-" : "+"}${h}:${m}${seconds}`;
}
export function observationTime(data: Intraday, value: number) {
  if (data.timeBasis === "civil") return `${data.date} ${clock(value)}（現地時計・UTC offset 不明）`;
  const index = data.points.findIndex(([x]) => x === value);
  return index < 0 ? axisTime(data, value)
    : `${data.date} ${clock(data.civilTimes[index])}（${offsetText(data.utcOffsets[index])}）`;
}
