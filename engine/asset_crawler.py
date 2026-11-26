#!/usr/bin/env python3
"""Download high-resolution product images from product pages or search results."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import deque
from http.cookiejar import CookieJar
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, quote_plus, urlencode, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

import numpy as np
from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parent.parent
MAX_PAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 40 * 1024 * 1024
MAX_SEARCH_PAGES = 10
MAX_IMAGE_CANDIDATES = 50
USER_AGENT = (
    "Mozilla/5.0 (compatible; AutoBannerAssetCrawler/1.0)"
)
REJECTED_IMAGE_PATH = re.compile(
    r"(?:^|[/_-])(?:icon|logo|sprite|pixel|tracking|banner|placeholder)(?:[/_.-]|$)",
    re.IGNORECASE,
)
GSSHOP_PRODUCT_TERMS = {
    "니트": ("니트", "스웨터", "가디건", "풀오버"),
    "패딩": ("패딩", "다운", "점퍼", "파카", "자켓", "재킷"),
    "귤": ("귤", "감귤", "만다린"),
    "롤화장지": ("화장지", "휴지", "롤"),
}
GSSHOP_PRODUCT_EXCLUSIONS = {
    "니트": ("뜨개실", "실타래", "코바늘", "편직기", "뜨개질 바늘", "수세미"),
    "패딩": ("옷걸이", "옷커버", "행거", "옷장", "의류덮개"),
}
GSSHOP_CONTEXT_QUERIES = {
    "니트": "여성",
    "패딩": "여성",
}


def _request(url: str, *, referer: str | None = None) -> Request:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    return Request(url, headers=headers)


def _fetch(url: str, *, limit: int, referer: str | None = None) -> tuple[bytes, str, str]:
    with urlopen(_request(url, referer=referer), timeout=20) as response:
        final_url = response.geturl()
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError(f"Response exceeds {limit} bytes: {url}")
        return data, response.headers.get_content_charset() or "utf-8", final_url


def _host_matches(url: str, domain: str) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    expected = domain.strip().lower().rstrip(".")
    if "://" in expected:
        expected = (urlparse(expected).hostname or "").lower().rstrip(".")
    return bool(host and expected and (host == expected or host.endswith(f".{expected}")))


def _validated_web_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Only absolute http(s) URLs are supported: {url}")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded credentials are not supported.")
    return url


def _srcset_urls(value: str) -> list[str]:
    urls: list[str] = []
    for item in value.split(","):
        parts = item.strip().split()
        if parts and not parts[0].startswith("data:"):
            urls.append(parts[0])
    return urls


class ProductPageParser(HTMLParser):
    """Collect likely full-size image URLs and product metadata from static HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[tuple[int, str]] = []
        self.title = ""
        self._in_title = False
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []
        self.json_ld: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._in_title = True
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_parts = []

        if tag == "meta":
            key = values.get("property", "").lower() or values.get("name", "").lower()
            if key in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
                self.images.append((0, values.get("content", "")))

        if tag in {"img", "source"}:
            for name in ("data-zoom-image", "data-large_image", "data-large", "data-original"):
                if values.get(name):
                    self.images.append((1, values[name]))
            for name in ("srcset", "data-srcset"):
                if values.get(name):
                    self.images.extend((2, item) for item in _srcset_urls(values[name]))
            for name in ("data-src", "data-lazy-src", "src"):
                if values.get(name):
                    self.images.append((3, values[name]))

        # Some commerce themes expose zoom images on non-img elements.
        for name in ("data-zoom-image", "data-large_image", "data-large"):
            if values.get(name):
                self.images.append((1, values[name]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_ld_parts))
            self._json_ld_parts = []
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self._json_ld_parts.append(data)


def _product_json_ld_images(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, list):
        for item in value:
            found.extend(_product_json_ld_images(item))
    elif isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(str(item).lower() == "product" for item in types):
            images = value.get("image", [])
            if isinstance(images, (str, dict)):
                images = [images]
            if isinstance(images, list):
                for image in images:
                    if isinstance(image, str):
                        found.append(image)
                    elif isinstance(image, dict) and isinstance(image.get("url"), str):
                        found.append(image["url"])
        for child in value.values():
            if isinstance(child, (dict, list)):
                found.extend(_product_json_ld_images(child))
    return found


def _page_image_urls(html: str, page_url: str) -> tuple[list[str], str]:
    parser = ProductPageParser()
    parser.feed(html)
    candidates = list(parser.images)
    for block in parser.json_ld:
        try:
            candidates.extend((1, item) for item in _product_json_ld_images(json.loads(block)))
        except (json.JSONDecodeError, TypeError):
            continue

    urls: list[str] = []
    seen: set[str] = set()
    for _, candidate in sorted(candidates, key=lambda item: item[0]):
        candidate = candidate.strip()
        if not candidate or candidate.startswith(("data:", "javascript:")):
            continue
        absolute = urljoin(page_url, candidate)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        if REJECTED_IMAGE_PATH.search(parsed.path):
            continue
        product_image = re.fullmatch(r"/prod/(\d+)/(\d+)/\d+", parsed.path)
        if parsed.hostname == "asset.m-gs.kr" and product_image:
            product_id = product_image.group(1)
            for image_index in range(1, 7):
                high_resolution = (
                    f"https://asset.m-gs.kr/prod/{product_id}/{image_index}/2000"
                )
                if high_resolution not in seen:
                    seen.add(high_resolution)
                    urls.append(high_resolution)
        if absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls, " ".join(parser.title.split())


class SearchResultsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page_urls: list[str] = []
        self.image_urls: list[tuple[str, str]] = []
        self._in_bing_result = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if tag == "li" and "b_algo" in classes:
            self._in_bing_result = True
        if tag == "a" and self._in_bing_result and values.get("href"):
            href = values["href"]
            encoded_url = parse_qs(urlparse(href).query).get("u", [])
            if encoded_url and encoded_url[0].startswith("a1"):
                payload = encoded_url[0][2:]
                try:
                    href = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
                except (ValueError, UnicodeDecodeError):
                    pass
            self.page_urls.append(href)
        if tag == "a" and "result__a" in classes and values.get("href"):
            self.page_urls.append(values["href"])
        if tag == "a" and "iusc" in classes and values.get("m"):
            try:
                metadata = json.loads(values["m"])
            except json.JSONDecodeError:
                return
            image_url = metadata.get("murl")
            page_url = metadata.get("purl", "")
            if isinstance(image_url, str) and isinstance(page_url, str):
                self.image_urls.append((image_url, page_url))

    def handle_endtag(self, tag: str) -> None:
        if tag == "li" and self._in_bing_result:
            self._in_bing_result = False


def _search_results(keyword: str, domain: str | None) -> tuple[list[str], list[str]]:
    search_keyword = _append_single_product_term(keyword)
    if domain and _host_matches("https://m.gsshop.com/", domain):
        pages = _gsshop_product_pages(search_keyword)
        if not pages:
            category = next((name for name in GSSHOP_CONTEXT_QUERIES if name in keyword), None)
            context = GSSHOP_CONTEXT_QUERIES.get(category or "")
            if context and context not in keyword.split():
                contextual_query = _append_single_product_term(f"{context} {keyword}")
                print(
                    f"GS SHOP found no category-matched products; retrying with: {contextual_query}",
                    file=sys.stderr,
                )
                pages = _gsshop_product_pages(contextual_query)
        if not pages:
            raise RuntimeError(
                f"GS SHOP returned no relevant products for packshot query: {search_keyword}"
            )
        return pages[:MAX_SEARCH_PAGES], []

    query = f"{search_keyword} site:{domain}" if domain else search_keyword
    encoded = quote_plus(query)
    pages: list[str] = []
    images: list[str] = []
    errors: list[str] = []

    endpoints = (
        ("DuckDuckGo", f"https://html.duckduckgo.com/html/?q={encoded}"),
        ("Bing", f"https://www.bing.com/search?q={encoded}"),
        ("Bing Images", f"https://www.bing.com/images/search?q={encoded}"),
    )
    for name, endpoint in endpoints:
        try:
            content, charset, _ = _fetch(endpoint, limit=MAX_PAGE_BYTES)
            parser = SearchResultsParser()
            parser.feed(content.decode(charset, errors="replace"))
            if name in {"DuckDuckGo", "Bing"}:
                for url in parser.page_urls:
                    redirect_target = parse_qs(urlparse(url).query).get("uddg", [])
                    if redirect_target:
                        url = redirect_target[0]
                    if urlparse(url).scheme in {"http", "https"} and (
                        not domain or _host_matches(url, domain)
                    ):
                        pages.append(url)
            else:
                for image_url, product_url in parser.image_urls:
                    if domain and not _host_matches(product_url, domain):
                        continue
                    if not domain or product_url:
                        images.append(image_url)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"{name}: {exc}")

    if domain and not pages:
        try:
            pages.extend(_shopify_product_pages(keyword, domain))
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"Official domain product search: {exc}")

    if not pages and not images and errors:
        raise RuntimeError("Search providers failed: " + "; ".join(errors))
    return pages[:MAX_SEARCH_PAGES], images[:MAX_IMAGE_CANDIDATES]


def _append_single_product_term(keyword: str) -> str:
    keyword = " ".join(keyword.split())
    if "단품" in keyword.split():
        return keyword
    return f"{keyword} 단품"


def _gsshop_product_pages(keyword: str) -> list[str]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://m.gsshop.com/",
    }
    search_url = (
        "https://m.gsshop.com/search/searchSect.gs?"
        + urlencode({"tq": keyword, "mseq": "401172"})
    )
    with opener.open(Request(search_url, headers=headers), timeout=20) as response:
        page_data = response.read(MAX_PAGE_BYTES + 1)
        if len(page_data) > MAX_PAGE_BYTES:
            raise ValueError(f"GS SHOP search page exceeds {MAX_PAGE_BYTES} bytes.")
        if not _host_matches(response.geturl(), "gsshop.com"):
            raise ValueError(f"GS SHOP search redirected outside its domain: {response.geturl()}")

    params = {
        "tq": keyword,
        "applyTypoProcess": "true",
        "sortType": "PURCHASE_QTY",
        "viewTyp": "view-type2",
        "cls": "",
        "categorys": "",
        "brand": "",
        "clothSize": "",
        "benefit": "",
        "tvBenefit": "",
        "color": "",
        "print": "",
        "reviewScore": "",
        "pagePrdSize": "100",
        "detailSearch": "true",
        "mseq": "440523",
        "dyn_filter": "",
        "ajaxGbn": "nochk",
        "button_click": "",
        "filterlayer": "true",
        "dlv": "",
        "part": "",
        "tomArr": "",
        "fantasy": "",
        "gsOnly": "",
        "searchMode": "SEMANTIC",
        "appendVectorResults": "true",
        "format": "json",
    }
    api_url = "https://m.gsshop.com/search/searchJson.gs?" + urlencode(params)
    api_headers = {**headers, "Referer": search_url}
    with opener.open(Request(api_url, headers=api_headers), timeout=20) as response:
        data = response.read(MAX_PAGE_BYTES + 1)
        if len(data) > MAX_PAGE_BYTES:
            raise ValueError(f"GS SHOP search results exceed {MAX_PAGE_BYTES} bytes.")
        if not _host_matches(response.geturl(), "gsshop.com"):
            raise ValueError(f"GS SHOP search redirected outside its domain: {response.geturl()}")

    payload = json.loads(data)
    products = (
        payload.get("_CONTENT_KEY", {})
        .get("genieSearchResultProduct", {})
        .get("prdList", [])
    )
    if not isinstance(products, list):
        return []

    category = next(
        (name for name in GSSHOP_PRODUCT_TERMS if name in keyword),
        None,
    )
    pages: list[str] = []
    seen: set[str] = set()
    for product in products:
        if not isinstance(product, dict):
            continue
        title = str(product.get("productName") or "")
        if category:
            if not any(term in title for term in GSSHOP_PRODUCT_TERMS[category]):
                continue
            if any(term in title for term in GSSHOP_PRODUCT_EXCLUSIONS.get(category, ())):
                continue
        product_url = product.get("linkUrl")
        if not isinstance(product_url, str):
            continue
        page_url = urljoin("https://m.gsshop.com/", product_url)
        parsed_url = urlparse(page_url)
        page_url = parsed_url._replace(
            path=quote(parsed_url.path, safe="/%:@"),
            query=quote(parsed_url.query, safe="=&%/:@+,-._~"),
        ).geturl()
        if _host_matches(page_url, "gsshop.com") and page_url not in seen:
            seen.add(page_url)
            pages.append(page_url)
    return pages


def _shopify_product_pages(keyword: str, domain: str) -> list[str]:
    host = domain.strip()
    if "://" in host:
        host = urlparse(host).hostname or ""
    host = host.split("/")[0].strip().lower()
    if not host:
        return []

    endpoint = (
        f"https://{host}/search/suggest.json?q={quote_plus(keyword)}"
        "&resources%5Btype%5D=product&resources%5Blimit%5D=10"
    )
    data, charset, final_url = _fetch(endpoint, limit=2 * 1024 * 1024)
    if not _host_matches(final_url, domain):
        raise ValueError(f"Official domain search redirected outside --domain-filter: {final_url}")
    payload = json.loads(data.decode(charset, errors="replace"))
    products = payload.get("resources", {}).get("results", {}).get("products", [])
    pages: list[str] = []
    if isinstance(products, list):
        for product in products:
            if not isinstance(product, dict) or not isinstance(product.get("url"), str):
                continue
            page_url = urljoin(final_url, product["url"])
            if _host_matches(page_url, domain):
                pages.append(page_url)
    return pages


def _image_dimensions(data: bytes, min_width: int) -> tuple[Image.Image, int, int]:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            ratio = width / height if height else 0
            if width < min_width:
                raise ValueError(f"image width {width}px is below minimum {min_width}px")
            if not 0.7 <= ratio <= 1.4:
                raise ValueError(f"aspect ratio {ratio:.3f} is outside 0.7–1.4")
            return image.convert("RGBA" if "A" in image.getbands() else "RGB"), width, height
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"download is not a valid image: {exc}") from exc


def _packshot_rejection_reason(image: Image.Image) -> str | None:
    if "A" in image.getbands():
        rgba = image.convert("RGBA")
        rgb_image = Image.new("RGB", rgba.size, "white")
        rgb_image.paste(rgba, mask=rgba.getchannel("A"))
    else:
        rgb_image = image.convert("RGB")

    pixels = np.asarray(rgb_image, dtype=np.uint8)
    height, width = pixels.shape[:2]
    corner_size = max(8, min(height, width) // 20)
    corners = (
        pixels[:corner_size, :corner_size],
        pixels[:corner_size, -corner_size:],
        pixels[-corner_size:, :corner_size],
        pixels[-corner_size:, -corner_size:],
    )
    for corner in corners:
        if np.min(corner.mean(axis=(0, 1))) < 240 or float(corner.std()) > 18:
            return "corners do not show a solid white studio backdrop"

    white_fraction = float(np.all(pixels >= 238, axis=2).mean())
    if white_fraction < 0.3:
        return "less than 30% of the image is near-white backdrop"

    foreground = np.any(pixels < 230, axis=2)
    ys, xs = np.where(foreground)
    if xs.size < width * height * 0.05:
        return "no dominant product silhouette was detected"

    small_mask = Image.fromarray(np.uint8(foreground) * 255).resize(
        (120, 120), Image.Resampling.NEAREST
    )
    component_mask = np.asarray(small_mask) > 0
    visited = np.zeros_like(component_mask)
    significant_components = 0
    for y, x in zip(*np.where(component_mask & ~visited)):
        if visited[y, x]:
            continue
        size = 0
        queue = deque([(int(y), int(x))])
        visited[y, x] = True
        while queue:
            current_y, current_x = queue.popleft()
            size += 1
            for neighbor_y in range(max(0, current_y - 1), min(120, current_y + 2)):
                for neighbor_x in range(max(0, current_x - 1), min(120, current_x + 2)):
                    if component_mask[neighbor_y, neighbor_x] and not visited[neighbor_y, neighbor_x]:
                        visited[neighbor_y, neighbor_x] = True
                        queue.append((neighbor_y, neighbor_x))
        if size >= 120 * 120 * 0.025:
            significant_components += 1
    if significant_components != 1:
        return "image does not contain exactly one dominant product silhouette"

    x0, x1 = np.percentile(xs, (1, 99))
    y0, y1 = np.percentile(ys, (1, 99))
    box_width = (x1 - x0 + 1) / width
    box_height = (y1 - y0 + 1) / height
    center_x = (x0 + x1) / (2 * width)
    center_y = (y0 + y1) / (2 * height)
    if not 0.45 <= box_width <= 0.92 or not 0.45 <= box_height <= 0.92:
        return "product does not occupy a centered, packshot-sized area"
    if abs(center_x - 0.5) > 0.08 or abs(center_y - 0.5) > 0.08:
        return "product silhouette is not centered"

    return None


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip().lower()
    slug = re.sub(r"[^\w.-]+", "-", normalized, flags=re.UNICODE).strip("-.")
    return slug or "product"


def _filename(base: str, index: int) -> str:
    return f"{base}.png" if index == 1 else f"{base}_{index:02d}.png"


def _save_png(image: Image.Image, destination: Path) -> None:
    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        image.save(temporary_path, format="PNG", optimize=True)
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def _run_pipeline(image_path: Path, output_dir: Path) -> None:
    cutout_dir = output_dir / "cutouts"
    shadow_dir = output_dir / "shadows"
    cutout_path = cutout_dir / f"{image_path.stem}_alpha.png"
    cutout_dir.mkdir(parents=True, exist_ok=True)
    shadow_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "engine" / "bg_remover.py"),
            "--input",
            str(image_path),
            "--output",
            str(cutout_path),
        ],
        check=True,
        cwd=ROOT,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "engine" / "shadow_engine.py"),
            "--input",
            str(cutout_path),
            "--output",
            str(shadow_dir / f"{cutout_path.stem}_shadow.png"),
            "--export-layers",
        ],
        check=True,
        cwd=ROOT,
    )


def _collect_candidates(
    *, url: str | None, keyword: str | None, domain: str | None
) -> list[str]:
    if url:
        page_url = _validated_web_url(url)
        if domain and not _host_matches(page_url, domain):
            raise ValueError(f"Product page is outside --domain-filter: {page_url}")
        pages, image_urls = [page_url], []
    else:
        assert keyword is not None
        pages, image_urls = _search_results(keyword, domain)

    candidates = list(image_urls)
    for page_url in pages:
        try:
            html, charset, final_url = _fetch(page_url, limit=MAX_PAGE_BYTES)
            if domain and not _host_matches(final_url, domain):
                print(f"Skipping redirected page outside domain filter: {final_url}", file=sys.stderr)
                continue
            page_images, _ = _page_image_urls(html.decode(charset, errors="replace"), final_url)
            candidates.extend(page_images)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            print(f"Could not inspect product page {page_url}: {exc}", file=sys.stderr)

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            unique.append(candidate)
            seen.add(candidate)
        if len(unique) >= MAX_IMAGE_CANDIDATES:
            break
    return unique


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find and download validated high-resolution e-commerce product images."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--keyword", help="Product search keyword or SKU.")
    source.add_argument("--url", help="Direct product detail page URL.")
    parser.add_argument("--domain-filter", help="Restrict product pages to this domain.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Destination for downloaded PNG masters.")
    parser.add_argument("--min-width", type=int, default=800, help="Minimum accepted image width in pixels.")
    parser.add_argument("--limit", type=int, default=1, help="Maximum number of matching images to download.")
    parser.add_argument(
        "--packshot-only",
        action="store_true",
        help="Require a centered product silhouette on a solid white studio backdrop.",
    )
    parser.add_argument(
        "--auto-process",
        action="store_true",
        help="Run bg_remover.py and shadow_engine.py --export-layers on downloaded images.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.min_width < 1:
        parser.error("--min-width must be at least 1")
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.domain_filter:
        filter_host = args.domain_filter.strip()
        if not filter_host or not urlparse(f"https://{filter_host}").hostname:
            parser.error("--domain-filter must be a hostname such as 'example.com'")
        args.domain_filter = filter_host

    output_dir = args.output_dir.expanduser().resolve()
    try:
        candidates = _collect_candidates(url=args.url, keyword=args.keyword, domain=args.domain_filter)
        if not candidates:
            raise RuntimeError("No candidate product images were found.")

        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = _slug(args.keyword or Path(urlparse(args.url).path).stem or urlparse(args.url).hostname or "product")
        downloaded = 0
        for candidate in candidates:
            if downloaded >= args.limit:
                break
            try:
                data, _, _ = _fetch(candidate, limit=MAX_IMAGE_BYTES, referer=args.url)
                image, width, height = _image_dimensions(data, args.min_width)
                if args.packshot_only:
                    rejection = _packshot_rejection_reason(image)
                    if rejection:
                        raise ValueError(rejection)
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                print(f"Skipping image {candidate}: {exc}", file=sys.stderr)
                continue

            destination = output_dir / _filename(base_name, downloaded + 1)
            _save_png(image, destination)
            print(f"Downloaded {width}x{height}: {destination}")
            downloaded += 1
            if args.auto_process:
                _run_pipeline(destination, output_dir)

        if downloaded == 0:
            reason = "format, minimum-width, and aspect-ratio"
            if args.packshot_only:
                reason += ", and packshot"
            raise RuntimeError(f"No image passed {reason} validation.")
        return 0
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
        print(f"asset_crawler: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"asset_crawler: processing pipeline failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
