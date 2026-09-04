import clickSound from "./sounds/star-click.mp3";

// One shared element instead of a new Audio per click. Browsers refuse
// playback until the page has been interacted with, and the rejection must
// stay quiet rather than reaching the console as an unhandled rejection.
let element;

export function playClick() {
  try {
    if (!element) {
      element = new Audio(clickSound);
      element.preload = "auto";
    }
    element.currentTime = 0;
    const played = element.play();
    if (played && typeof played.catch === "function") played.catch(() => {});
  } catch {
    // No audio device, or a format this browser will not decode.
  }
}
