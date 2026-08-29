// Logical canvas size and the HUD bands. Everything draws in these units;
// main.ts scales the backing store by devicePixelRatio.
export const W = 1280;
export const H = 720;
// Arcade/GBA layout: status bar on top, the map filling the middle, the hand as
// a row of slots along the bottom, with a two-line log between them.
export const TOP_H = 64;
export const LOG_H = 40;
export const CARDBAR_H = 88;
export const MAP_X = 0;
export const MAP_Y = TOP_H;
export const MAP_W = W;
export const MAP_H = H - TOP_H - CARDBAR_H - LOG_H;

export const UI_FONT = "ui-monospace, monospace";
export const EMOJI_FONT = '"Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif';
