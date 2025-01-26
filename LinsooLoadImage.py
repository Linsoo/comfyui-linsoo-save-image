import os
import hashlib
import torch
from PIL import Image, ImageOps, ImageSequence
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from PIL.PngImagePlugin import PngInfo
import piexif
import piexif.helper
from comfy.cli_args import args
import folder_paths
import node_helpers
import numpy as np
import safetensors.torch
from .LinsooCommon import *

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False
any_typ = AnyType("*")

class LinsooLoadImage:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {"image": (sorted(files), {"image_upload": True})},
        }
    

    CATEGORY = "linsoo"
    FUNCTION = "load_image"
    RETURN_TYPES = ('IMAGE','MASK','STRING','STRING','INT','INT','FLOAT','INT','INT', LinsooCustomDataType("prompt"), LinsooCustomDataType("workflow"))
    RETURN_NAMES = ('image','mask','positive','negative','seed','step','cfg','width','height', 'prompt', 'workflow')
    def load_image(self, image):
        image_path = folder_paths.get_annotated_filepath(image)

        img = node_helpers.pillow(Image.open, image_path)

        output_images = []
        output_masks = []
        positive, negative, prompt, workflow = '', '', None, None

        seed,step,cfg, width, height = None,None,None,None,None

        excluded_formats = ['MPO']

        # -----------------------------------------------------------------------------------------------
        # 메타 정보
        metadata = img.info
        tmp_exif = None
        exif_dict = None

        for tag, value in metadata.items():
            if 'prompt' == tag.lower():
                prompt = value
            if 'workflow' == tag.lower():
                workflow = value
            if 'exif' == tag.lower():
                tmp_exif = value

        if tmp_exif:
            exif_dict = piexif.load(tmp_exif)
            # user_comment = exif_dict["Exif"][piexif.ExifIFD.UserComment]
            if exif_dict:
                tmp_0th=exif_dict.get('0th')

                if prompt is None and tmp_0th is not None:
                    prompt = tmp_0th.get(piexif.ImageIFD.Make)
                if workflow is None and tmp_0th is not None:
                    workflow = tmp_0th.get(piexif.ImageIFD.ImageDescription)
        
        if prompt is not None and workflow is not None:
            # ret_ckpt, ret_sampler, ret_prompt, ret_clip, ret_loras = linsoo_parse_prompt(prompt,workflow)
            _, _, ret_prompt, _, _ = linsoo_parse_prompt(prompt,workflow)
            for tmp in ret_prompt.items():
                text =tmp[1].get('text')
                chk_positive = tmp[1].get('positive')
                if chk_positive:
                    positive = positive+text+','
                else:
                    negative = negative+text+','

        # -----------------------------------------------------------------------------------------------

        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                width = image.size[0]
                height = image.size[1]

            if image.size[0] != width or image.size[1] != height:
                continue

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]
        return (output_image, output_mask, positive, negative, seed,step,cfg, width,height,prompt,workflow)

NODE_CLASS_MAPPINGS = {
    "LinsooLoadImage": LinsooLoadImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LinsooLoadImage": "Linsoo Load Image"
}
    