import { style } from "@vanilla-extract/css";

export const container = style({
  display: "grid",
  placeItems: "center",
  alignContent: "center",
  gap: "0.5rem",
  minHeight: "100vh",
  padding: "1rem",
  fontFamily: "system-ui, sans-serif",
  backgroundColor: "#ffffff",
  color: "#1f1f1f",
});

export const title = style({
  margin: 0,
  fontSize: "2.5rem",
});

export const subtitle = style({
  margin: 0,
  color: "#4a4a4a",
});
