// Image CDN helpers. Wikimedia's thumbnailer only renders a fixed size
// ladder, so requested widths snap to the nearest allowed size. Cards get
// 500px instead of multi-hundred-KB originals; detail pages get 960px.
const LADDER = [250, 330, 500, 960, 1280];
const CARD_WIDTH = 500;
const DETAIL_WIDTH = 960;

function snap(width) {
  return LADDER.reduce((best, size) =>
    Math.abs(size - width) < Math.abs(best - width) ? size : best,
  LADDER[0]);
}

function wikimediaThumb(url, width) {
  const px = `${snap(width)}px-`;
  // Existing thumb URL: .../thumb/a/ab/File.jpg/1280px-File.jpg -> swap size
  const thumb = url.match(/^(.*\/thumb\/.+?\/)(\d+)px-([^/?]+)/);
  if (thumb) {
    const query = url.includes("?") ? url.slice(url.indexOf("?")) : "";
    return `${thumb[1]}${px}${thumb[3]}${query}`;
  }
  // Direct file URL: synthesise a thumb path
  const direct = url.match(
    /^(https:\/\/upload\.wikimedia\.org\/wikipedia\/commons\/)([^/]+\/[^/]+)\/([^/?]+)$/,
  );
  if (direct) {
    return `${direct[1]}thumb/${direct[2]}/${px}${direct[3]}`;
  }
  return url;
}

function unsplashParams(url, width) {
  if (url.includes("images.unsplash.com")) {
    return url.includes("?")
      ? `${url}&w=${width}&q=70&auto=format&fit=crop`
      : `${url}?w=${width}&q=70&auto=format&fit=crop`;
  }
  return url;
}

export function cdnImage(url, variant = "card") {
  if (!url) return url;
  const width = variant === "detail" ? DETAIL_WIDTH : CARD_WIDTH;
  return unsplashParams(wikimediaThumb(url, width), width);
}
