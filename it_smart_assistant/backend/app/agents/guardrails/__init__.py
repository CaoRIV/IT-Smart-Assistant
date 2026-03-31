"""Image quality guardrail for validating image attachments.

Checks image quality before sending to LLM to avoid hallucination from poor images.
"""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageStat

logger = logging.getLogger(__name__)


@dataclass
class ImageQualityResult:
    """Result of image quality check."""

    is_acceptable: bool
    issues: list[str]
    brightness: float
    blur_score: float
    resolution: tuple[int, int]
    suggestion: str | None = None


class ImageQualityGuardrail:
    """Guardrail to check image quality before LLM processing."""

    # Thresholds for quality checks
    MIN_BRIGHTNESS = 30  # Out of 255
    MAX_BRIGHTNESS = 240  # Out of 255
    MIN_BLUR_SCORE = 100  # Laplacian variance threshold
    MIN_RESOLUTION = (640, 480)  # Minimum acceptable resolution
    MAX_DIMENSION = 4096  # Maximum dimension to prevent huge images

    def __init__(
        self,
        min_brightness: float = MIN_BRIGHTNESS,
        max_brightness: float = MAX_BRIGHTNESS,
        min_blur_score: float = MIN_BLUR_SCORE,
        min_resolution: tuple[int, int] = MIN_RESOLUTION,
    ):
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_blur_score = min_blur_score
        self.min_resolution = min_resolution

    def _decode_image(self, data_url: str) -> Image.Image:
        """Decode base64 data URL to PIL Image."""
        # Remove data URL prefix
        if ";base64," in data_url:
            base64_data = data_url.split(";base64,")[1]
        else:
            base64_data = data_url

        image_data = base64.b64decode(base64_data)
        return Image.open(io.BytesIO(image_data))

    def _check_brightness(self, image: Image.Image) -> tuple[bool, float]:
        """Check if image brightness is acceptable."""
        stat = ImageStat.Stat(image)
        if stat.mean is None:
            return False, 0.0

        # Calculate average brightness across all bands
        brightness = sum(stat.mean) / len(stat.mean)
        is_ok = self.min_brightness <= brightness <= self.max_brightness
        return is_ok, brightness

    def _check_blur(self, image: Image.Image) -> tuple[bool, float]:
        """Check if image is too blurry using Laplacian variance."""
        try:
            import cv2

            # Convert PIL to OpenCV format
            if image.mode != "RGB":
                image = image.convert("RGB")
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

            # Calculate Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            is_ok = laplacian_var >= self.min_blur_score
            return is_ok, float(laplacian_var)
        except ImportError:
            # Fallback if OpenCV not available
            logger.warning("OpenCV not available, skipping blur check")
            return True, 0.0
        except Exception as e:
            logger.warning(f"Blur check failed: {e}")
            return True, 0.0

    def _check_resolution(self, image: Image.Image) -> tuple[bool, tuple[int, int]]:
        """Check if image resolution is acceptable."""
        width, height = image.size
        is_ok = (
            width >= self.min_resolution[0]
            and height >= self.min_resolution[1]
            and width <= self.MAX_DIMENSION
            and height <= self.MAX_DIMENSION
        )
        return is_ok, (width, height)

    def check_image(self, data_url: str | None) -> ImageQualityResult:
        """Check image quality from base64 data URL.

        Args:
            data_url: Base64 encoded image data URL

        Returns:
            ImageQualityResult with quality assessment
        """
        if not data_url:
            return ImageQualityResult(
                is_acceptable=False,
                issues=["No image provided"],
                brightness=0.0,
                blur_score=0.0,
                resolution=(0, 0),
                suggestion="Vui lòng tải lên một hình ảnh.",
            )

        try:
            image = self._decode_image(data_url)
            issues: list[str] = []

            # Check brightness
            brightness_ok, brightness = self._check_brightness(image)
            if not brightness_ok:
                if brightness < self.min_brightness:
                    issues.append(f"Ảnh quá tối (độ sáng: {brightness:.1f}/255)")
                else:
                    issues.append(f"Ảnh quá sáng (độ sáng: {brightness:.1f}/255)")

            # Check blur
            blur_ok, blur_score = self._check_blur(image)
            if not blur_ok:
                issues.append(f"Ảnh bị mờ (độ nét: {blur_score:.1f}, cần > {self.min_blur_score})")

            # Check resolution
            resolution_ok, resolution = self._check_resolution(image)
            if not resolution_ok:
                if resolution[0] > self.MAX_DIMENSION or resolution[1] > self.MAX_DIMENSION:
                    issues.append(f"Ảnh quá lớn ({resolution[0]}x{resolution[1]})")
                else:
                    issues.append(f"Ảnh độ phân giải thấp ({resolution[0]}x{resolution[1]})")

            is_acceptable = len(issues) == 0

            suggestion = None
            if not is_acceptable:
                suggestion = self._generate_suggestion(issues)

            return ImageQualityResult(
                is_acceptable=is_acceptable,
                issues=issues,
                brightness=brightness,
                blur_score=blur_score,
                resolution=resolution,
                suggestion=suggestion,
            )

        except Exception as e:
            logger.error(f"Image quality check failed: {e}")
            return ImageQualityResult(
                is_acceptable=False,
                issues=[f"Lỗi kiểm tra ảnh: {str(e)}"],
                brightness=0.0,
                blur_score=0.0,
                resolution=(0, 0),
                suggestion="Không thể kiểm tra chất lượng ảnh. Vui lòng thử lại với ảnh khác.",
            )

    def _generate_suggestion(self, issues: list[str]) -> str:
        """Generate user-friendly suggestion based on issues."""
        suggestions = []

        for issue in issues:
            if "tối" in issue.lower():
                suggestions.append("chụp lại với ánh sáng tốt hơn")
            elif "sáng" in issue.lower():
                suggestions.append("tránh ánh sáng quá mạnh hoặc phản chiếu")
            elif "mờ" in issue.lower():
                suggestions.append("giữ máy ảnh ổn định, chụp lại rõ nét hơn")
            elif "độ phân giải" in issue.lower() or "lớn" in issue.lower():
                suggestions.append("đảm bảo ảnh rõ ràng và không bị cắt xén")

        if suggestions:
            return f"Hình ảnh chưa đạt yêu cầu. Bạn có thể {', '.join(suggestions)} để mình hỗ trợ chính xác nhất."

        return "Hình ảnh chưa đạt yêu cầu. Vui lòng thử lại với ảnh khác."


# Singleton instance
guardrail = ImageQualityGuardrail()


def check_image_quality(data_url: str | None) -> ImageQualityResult:
    """Convenience function to check image quality."""
    return guardrail.check_image(data_url)
