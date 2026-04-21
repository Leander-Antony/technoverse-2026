from __future__ import annotations

import argparse
import io
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import ExifTags, Image, ImageChops, ImageFilter


CAMERA_SOFTWARE_HINTS = {
	"iphone",
	"android",
	"samsung",
	"pixel",
	"xiaomi",
	"huawei",
}

EDITING_SOFTWARE_HINTS = {
	"photoshop",
	"lightroom",
	"snapseed",
	"gimp",
	"canva",
	"pixlr",
	"faceapp",
}

AI_SOFTWARE_HINTS = {
	"midjourney",
	"stable diffusion",
	"dall-e",
	"firefly",
	"dreamstudio",
	"generative fill",
	"img2img",
}


@dataclass
class ForensicSignals:
	has_exif: bool
	camera_make: str | None
	camera_model: str | None
	software_tag: str | None
	ela_mean: float
	ela_std: float
	edge_density: float
	noise_std: float
	local_inconsistency: float


def _parse_exif_datetime(value: Any) -> datetime | None:
	if not value:
		return None
	text = str(value).strip()
	for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
		try:
			return datetime.strptime(text, fmt)
		except ValueError:
			continue
	return None


def _average_hash(image: Image.Image, hash_size: int = 16) -> int:
	gray = image.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
	arr = np.asarray(gray, dtype=np.float32)
	avg = float(np.mean(arr))
	bits = (arr > avg).flatten()
	hash_value = 0
	for bit in bits:
		hash_value = (hash_value << 1) | int(bit)
	return int(hash_value)


def _hamming_distance(a: int, b: int) -> int:
	return (a ^ b).bit_count()


def _extract_exif(image: Image.Image) -> dict[str, Any]:
	raw = image.getexif()
	if not raw:
		return {}
	readable: dict[str, Any] = {}
	for key, value in raw.items():
		tag_name = ExifTags.TAGS.get(key, str(key))
		readable[str(tag_name)] = value
	return readable


def _to_grayscale_array(image: Image.Image) -> np.ndarray:
	arr = np.asarray(image.convert("L"), dtype=np.float32)
	return arr


def _edge_density(image: Image.Image) -> float:
	edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
	arr = np.asarray(edges, dtype=np.float32)
	strong_edges = np.mean(arr > 40.0)
	return float(strong_edges)


def _noise_std(image: Image.Image) -> float:
	gray = _to_grayscale_array(image)
	blurred = np.asarray(image.convert("L").filter(ImageFilter.GaussianBlur(radius=1.2)), dtype=np.float32)
	residual = gray - blurred
	return float(np.std(residual))


def _local_inconsistency(image: Image.Image, block_size: int = 32) -> float:
	gray = _to_grayscale_array(image)
	h, w = gray.shape
	if h < block_size or w < block_size:
		return 0.0

	block_stds: list[float] = []
	for y in range(0, h - block_size + 1, block_size):
		for x in range(0, w - block_size + 1, block_size):
			patch = gray[y : y + block_size, x : x + block_size]
			block_stds.append(float(np.std(patch)))

	if not block_stds:
		return 0.0
	return float(np.std(np.array(block_stds, dtype=np.float32)))


def _error_level_analysis(image: Image.Image, quality: int = 90) -> tuple[float, float]:
	# ELA compares the image with a re-compressed version to highlight inconsistent edits.
	buffer = io.BytesIO()
	image.convert("RGB").save(buffer, "JPEG", quality=quality)
	buffer.seek(0)
	recompressed = Image.open(buffer).convert("RGB")
	original = image.convert("RGB")
	diff = ImageChops.difference(original, recompressed)
	arr = np.asarray(diff, dtype=np.float32)
	return float(np.mean(arr)), float(np.std(arr))


def extract_signals(image_path: Path) -> ForensicSignals:
	with Image.open(image_path) as img:
		exif = _extract_exif(img)
		ela_mean, ela_std = _error_level_analysis(img)
		return ForensicSignals(
			has_exif=bool(exif),
			camera_make=str(exif.get("Make", "")).strip() or None,
			camera_model=str(exif.get("Model", "")).strip() or None,
			software_tag=str(exif.get("Software", "")).strip() or None,
			ela_mean=ela_mean,
			ela_std=ela_std,
			edge_density=_edge_density(img),
			noise_std=_noise_std(img),
			local_inconsistency=_local_inconsistency(img),
		)


def verify_metadata_chain(image_path: Path) -> dict[str, Any]:
	with Image.open(image_path) as img:
		exif = _extract_exif(img)

	captured = _parse_exif_datetime(exif.get("DateTimeOriginal"))
	digitized = _parse_exif_datetime(exif.get("DateTimeDigitized"))
	last_exif_edit = _parse_exif_datetime(exif.get("DateTime"))
	fs_mtime = datetime.fromtimestamp(image_path.stat().st_mtime)

	issues: list[str] = []
	checks: list[str] = []

	if captured:
		checks.append("DateTimeOriginal present.")
	if digitized:
		checks.append("DateTimeDigitized present.")
	if last_exif_edit:
		checks.append("EXIF DateTime present.")

	if captured and digitized and digitized < captured:
		issues.append("Digitized time is earlier than original capture time.")
	if captured and last_exif_edit and last_exif_edit < captured:
		issues.append("EXIF DateTime is earlier than original capture time.")
	if captured and fs_mtime and fs_mtime < captured:
		issues.append("Filesystem modified time is earlier than EXIF capture time.")

	software_tag = str(exif.get("Software", "")).lower().strip()
	if software_tag and any(hint in software_tag for hint in EDITING_SOFTWARE_HINTS):
		checks.append("Software tag indicates an editing tool was used.")

	has_timeline = any([captured, digitized, last_exif_edit])
	if not has_timeline:
		status = "insufficient_evidence"
	elif issues:
		status = "inconsistent"
	else:
		status = "verified"

	return {
		"status": status,
		"capture_time": captured.isoformat(sep=" ") if captured else None,
		"digitized_time": digitized.isoformat(sep=" ") if digitized else None,
		"exif_datetime": last_exif_edit.isoformat(sep=" ") if last_exif_edit else None,
		"filesystem_modified_time": fs_mtime.isoformat(sep=" "),
		"checks": checks,
		"issues": issues,
	}


def reverse_image_search_local(
	image_path: Path,
	reference_dir: Path | None,
	top_k: int = 5,
	similarity_threshold: float = 0.90,
) -> dict[str, Any]:
	if reference_dir is None:
		return {
			"status": "skipped",
			"reason": "No reference directory provided. Use --reference-dir for reverse-image matching.",
			"matches": [],
		}

	if not reference_dir.exists() or not reference_dir.is_dir():
		return {
			"status": "error",
			"reason": f"Reference directory not found: {reference_dir}",
			"matches": [],
		}

	extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
	with Image.open(image_path) as query_img:
		query_hash = _average_hash(query_img)

	bit_length = 16 * 16
	matches: list[dict[str, Any]] = []

	for candidate in reference_dir.rglob("*"):
		if not candidate.is_file() or candidate.suffix.lower() not in extensions:
			continue
		if candidate.resolve() == image_path.resolve():
			continue

		try:
			with Image.open(candidate) as cand_img:
				cand_hash = _average_hash(cand_img)
		except Exception:
			continue

		distance = _hamming_distance(query_hash, cand_hash)
		similarity = 1.0 - (distance / bit_length)
		if similarity >= similarity_threshold:
			matches.append(
				{
					"path": str(candidate),
					"similarity": round(similarity, 4),
					"hamming_distance": distance,
				}
			)

	matches.sort(key=lambda item: item["similarity"], reverse=True)
	trimmed = matches[:top_k]

	return {
		"status": "matches_found" if trimmed else "no_matches",
		"reference_dir": str(reference_dir),
		"matches": trimmed,
	}


def classify_image(
	signals: ForensicSignals,
	metadata_chain: dict[str, Any],
	reverse_search: dict[str, Any],
) -> dict[str, Any]:
	camera_score = 0.1
	ai_score = 0.1
	edited_score = 0.1
	reasons: list[str] = []

	make_model_text = f"{signals.camera_make or ''} {signals.camera_model or ''}".lower().strip()
	software_text = (signals.software_tag or "").lower()

	if signals.has_exif:
		camera_score += 0.2
		reasons.append("EXIF metadata is present.")
	else:
		ai_score += 0.15
		edited_score += 0.05
		reasons.append("No EXIF metadata found (common in exported/AI images).")

	if make_model_text:
		camera_score += 0.3
		reasons.append(f"Camera make/model tag detected: {make_model_text}.")

	if any(hint in software_text for hint in CAMERA_SOFTWARE_HINTS):
		camera_score += 0.1
		reasons.append(f"Software tag looks camera-native: {signals.software_tag}.")

	if any(hint in software_text for hint in EDITING_SOFTWARE_HINTS):
		edited_score += 0.35
		reasons.append(f"Editing software tag detected: {signals.software_tag}.")

	if any(hint in software_text for hint in AI_SOFTWARE_HINTS):
		ai_score += 0.5
		reasons.append(f"AI-generation software tag detected: {signals.software_tag}.")

	if signals.ela_mean > 12.0 or signals.ela_std > 18.0:
		edited_score += 0.2
		reasons.append("ELA indicates stronger compression inconsistency (possible edits).")
	else:
		camera_score += 0.1

	if signals.noise_std < 4.5:
		ai_score += 0.2
		reasons.append("Image has unusually smooth noise profile (common in AI outputs).")
	elif signals.noise_std > 8.5:
		camera_score += 0.15

	if signals.local_inconsistency > 7.0:
		edited_score += 0.2
		reasons.append("Local texture inconsistency is high (possible manipulated regions).")

	if signals.edge_density < 0.05 and signals.noise_std < 5.0:
		ai_score += 0.1

	meta_status = metadata_chain.get("status")
	if meta_status == "inconsistent":
		edited_score += 0.25
		reasons.append("Metadata chain is inconsistent.")
	elif meta_status == "verified":
		camera_score += 0.15
		reasons.append("Metadata chain timeline is consistent.")

	if reverse_search.get("status") == "matches_found":
		matches = reverse_search.get("matches", [])
		best_similarity = float(matches[0].get("similarity", 0.0)) if matches else 0.0
		if best_similarity >= 0.985:
			ai_score += 0.1
			edited_score += 0.1
			reasons.append("Near-identical image match found by reverse search.")
		elif best_similarity >= 0.95:
			edited_score += 0.08
			reasons.append("Highly similar image match found by reverse search.")

	scores = {
		"camera": max(camera_score, 0.0),
		"ai_generated": max(ai_score, 0.0),
		"edited": max(edited_score, 0.0),
	}

	total = sum(scores.values()) or 1.0
	normalized = {k: v / total for k, v in scores.items()}
	predicted_label = max(normalized, key=normalized.get)
	confidence = normalized[predicted_label]

	return {
		"prediction": predicted_label,
		"confidence": round(confidence, 4),
		"scores": {k: round(v, 4) for k, v in normalized.items()},
		"signals": {
			"has_exif": signals.has_exif,
			"camera_make": signals.camera_make,
			"camera_model": signals.camera_model,
			"software_tag": signals.software_tag,
			"ela_mean": round(signals.ela_mean, 4),
			"ela_std": round(signals.ela_std, 4),
			"edge_density": round(signals.edge_density, 4),
			"noise_std": round(signals.noise_std, 4),
			"local_inconsistency": round(signals.local_inconsistency, 4),
		},
		"reasons": reasons,
		"metadata_chain_verification": metadata_chain,
		"reverse_image_search": reverse_search,
		"note": (
			"This is a heuristic forensic estimate, not a legal-grade proof. "
			"Use this with reverse-image search and metadata chain verification."
		),
	}


def run(image_path: Path, reference_dir: Path | None = None) -> dict[str, Any]:
	if not image_path.exists() or not image_path.is_file():
		raise FileNotFoundError(f"Image not found: {image_path}")
	signals = extract_signals(image_path)
	metadata_chain = verify_metadata_chain(image_path)
	reverse_search = reverse_image_search_local(image_path, reference_dir)
	return classify_image(signals, metadata_chain, reverse_search)


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Heuristic detector for camera vs AI-generated vs edited images."
	)
	parser.add_argument("image", type=Path, help="Path to image file")
	parser.add_argument(
		"--reference-dir",
		type=Path,
		default=None,
		help="Folder of known images used for local reverse-image matching.",
	)
	parser.add_argument(
		"--pretty",
		action="store_true",
		help="Pretty-print JSON output",
	)
	args = parser.parse_args()

	result = run(args.image, args.reference_dir)
	if args.pretty:
		print(json.dumps(result, indent=2))
	else:
		print(json.dumps(result))


if __name__ == "__main__":
	main()
