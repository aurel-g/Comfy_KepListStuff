from typing import Any, Dict, List, Tuple, Union, Optional

import torch
from PIL import ImageFont, ImageDraw, Image
import matplotlib.font_manager as fm
from torch import Tensor

from custom_nodes.Comfy_KepListStuff.utils import (
    zip_with_fill,
    tensor2pil,
    pil2tensor,
)

class ImageLabelOverlay:
    def __init__(self) -> None:
        pass

    @classmethod
    def INPUT_TYPES(s) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "images": ("IMAGE",),
            },
            "optional": {
                "float_labels": ("FLOAT", {"forceInput": True}),
                "int_labels": ("INT", {"forceInput": True}),
                "str_labels": ("STR", {"forceInput": True}),
            },
        }

    RELOAD_INST = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("Images",)
    INPUT_IS_LIST = (True,)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "put_overlay"

    CATEGORY = "List Stuff"

    def put_overlay(
            self,
            images: List[Tensor],
            float_labels: Optional[List[float]] = None,
            int_labels: Optional[List[int]] = None,
            str_labels: Optional[List[str]] = None,
    ) -> Tuple[List[Tensor]]:
        batches = images

        labels_to_check: Dict[str, Union[List[float], List[int], List[str], None]] = {
            "float": float_labels if float_labels is not None else None,
            "int": int_labels if int_labels is not None else None,
            "str": str_labels if str_labels is not None else None
        }

        for l_type, labels in labels_to_check.items():
            if labels is None:
                continue
            if len(batches) != len(labels) and len(labels) != 1:
                raise Exception(
                    f"Non-matching input sizes got {len(batches)} Image Batches, {len(labels)} Labels for label type {l_type}"
                )

        image_h, image_w, _ = batches[0][0].size()

        font = ImageFont.truetype(fm.findfont(fm.FontProperties()), 60)

        ret_images = []
        loop_gen = zip_with_fill(batches, float_labels, int_labels, str_labels)
        for b_idx, (img_batch, float_lbl, int_lbl, str_lbl) in enumerate(loop_gen):
            batch = []
            for i_idx, img in enumerate(img_batch):
                pil_img = tensor2pil(img)
                print(f"Batch: {b_idx} | img: {i_idx}")
                print(img.size())
                draw = ImageDraw.Draw(pil_img)

                draw.text((0, image_h - 60), f"B: {b_idx} | I: {i_idx}", fill="red", font=font)

                y_offset = 0
                for lbl_type, lbl in zip(["float", "int", "str"], [float_lbl, int_lbl, str_lbl]):
                    if lbl is None:
                        continue
                    draw.rectangle((0, 0 + y_offset, 512, 60 + y_offset), fill="#ffff33")
                    draw.text((0, 0 + y_offset), str(lbl), fill="red", font=font)
                    y_offset += 60
                batch.append(pil2tensor(pil_img))

            ret_images.append(torch.cat(batch))

        return (ret_images,)


class StackImages:
    def __init__(self) -> None:
        pass

    @classmethod
    def INPUT_TYPES(s) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "images": ("IMAGE",),
                "splits": ("INT", {"forceInput": True, "min": 1}),
                "stack_mode": (["horizontal", "vertical"], {"default": "horizontal"}),
                "batch_stack_mode": (["horizontal", "vertical"], {"default": "horizontal"}),
            },
        }

    RELOAD_INST = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("Image",)
    INPUT_IS_LIST = (True,)
    OUTPUT_IS_LIST = (False,)
    OUTPUT_NODE = True
    FUNCTION = "stack_images"

    CATEGORY = "List Stuff"

    def stack_images(
            self,
            images: List[Tensor],
            splits: List[int],
            stack_mode: List[str],
            batch_stack_mode: List[str],
    ) -> Tuple[Tensor]:
        if len(stack_mode) != 1:
            raise Exception("Only single stack mode supported.")
        if len(batch_stack_mode) != 1:
            raise Exception("Only single batch stack mode supported.")

        stack_direction = stack_mode[0]
        batch_stack_direction = batch_stack_mode[0]

        if len(splits) == 1:
            splits = splits * len(images)
        else:
            if sum(splits) != len(images):
                raise Exception("Sum of splits must equal number of images.")

        batches = images
        batch_size = len(batches[0])

        image_h, image_w, _ = batches[0][0].size()
        if batch_stack_direction == "horizontal":
            batch_h = image_h
            # stack horizontally
            batch_w = image_w * batch_size
        else:
            # stack vertically
            batch_h = image_h * batch_size
            batch_w = image_w

        if stack_direction == "horizontal":
            full_w = batch_w * len(splits)
            full_h = batch_h * max(splits)
        else:
            full_w = batch_w * max(splits)
            full_h = batch_h * len(splits)

        full_image = Image.new("RGB", (full_w, full_h))

        batch_idx = 0

        for split_idx, split in enumerate(splits):
            for idx_in_split in range(split):
                batch_img = Image.new("RGB", (batch_w, batch_h))
                batch = batches[batch_idx + idx_in_split]
                if batch_stack_direction == "horizontal":
                    for img_idx, img in enumerate(batch):
                        x_offset = image_w * img_idx
                        batch_img.paste(tensor2pil(img), (x_offset, 0))
                else:
                    for img_idx, img in enumerate(batch):
                        y_offset = image_h * img_idx
                        batch_img.paste(tensor2pil(img), (0, y_offset))

                if stack_direction == "horizontal":
                    x_offset = batch_w * split_idx
                    y_offset = batch_h * idx_in_split
                else:
                    x_offset = batch_w * idx_in_split
                    y_offset = batch_h * split_idx
                full_image.paste(batch_img, (x_offset, y_offset))

            batch_idx += split
        return (pil2tensor(full_image),)

class EmptyImages:
    def __init__(self) -> None:
        pass

    @classmethod
    def INPUT_TYPES(s) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {},
            "optional": {
                "num_images": ("INT", {"forceInput": True, "min": 1}),
                "splits": ("INT", {"forceInput": True, "min": 1}),
                "batch_size": ("INT", {"default": 1, "min": 1}),
            }
        }

    RELOAD_INST = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("Image",)
    INPUT_IS_LIST = (True,)
    OUTPUT_IS_LIST = (True,)
    OUTPUT_NODE = True
    FUNCTION = "generate_empty_images"

    CATEGORY = "List Stuff"

    def generate_empty_images(
            self,
            num_images: Optional[List[int]] = None,
            splits: Optional[List[int]] = None,
            batch_size: Optional[List[int]] = None,
    ) -> Tuple[List[Tensor]]:
        if batch_size is None:
            batch_size = [1]
        else:
            if len(batch_size) != 1:
                raise Exception("Only single batch size supported.")

        if num_images is None and splits is None:
            raise Exception("Must provide either num_images or splits.")

        if num_images is not None and len(num_images) != 1:
            raise Exception("Only single num_images supported.")

        if num_images is not None and splits is None:
            # If splits is None, then all images are in one split
            splits = [num_images[0]]

        if num_images is None and splits is not None:
            # If num_images is None, then it should be the sum of all splits
            num_images = [sum(splits)]

        if num_images is not None and splits is not None:
            if len(splits) == 1:
                # Fill splits with same value enough times to sum to num_images
                fills = int(num_images[0] / splits[0])
                splits = [splits[0]] * fills
                if sum(splits) != num_images[0]:
                    splits.append(num_images[0] - sum(splits))
            else:
                if sum(splits) != num_images[0]:
                    raise Exception("Sum of splits must match number of images.")

        ret_images = []
        for split in splits:
            # Rotate between fully dynamic range of colors
            color = (split * 10, split * 20, split * 30)
            for _ in range(split):
                batch_tensor = torch.zeros(batch_size[0], 512, 512, 3)
                for batch_idx in range(batch_size[0]):
                    batch_color = (color[0] + 75 * batch_idx, color[1], color[2])
                    image = Image.new("RGB", (512, 512), color=batch_color)
                    batch_tensor[batch_idx] = pil2tensor(image)
                ret_images.append(batch_tensor)
        return (ret_images,)