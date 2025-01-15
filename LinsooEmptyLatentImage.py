import re
import torch
import comfy.model_management


class LinsooEmptyLatentImage:
    RECOMMEND_RESOLUTION=['512x512 (1:1)', '640x1536 (5:12)','768x1344 (4:7)','832x1216 (13:19)','896x1152 (7:9)','1024x1024 (1:1)','1152x896 (9:7)','1216x832 (19:13)','1344x768 (7:4)','1536x640 (12:5)']

    def __init__(self):
        self.device = comfy.model_management.intermediate_device()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "recommend_resolution": (s.RECOMMEND_RESOLUTION,{'default': s.RECOMMEND_RESOLUTION[4],'tooltip': "Select the recommended resolution."}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4096, "tooltip": "The number of latent images in the batch."})
            }
        }
    RETURN_TYPES = ("LATENT",)
    OUTPUT_TOOLTIPS = ("The empty latent image batch.",)
    FUNCTION = "generate"

    CATEGORY = "linsoo"
    DESCRIPTION = "Create a new batch of empty latent images to be denoised via sampling."

    def generate(self, recommend_resolution:str = None, batch_size=1):

        regex = r"(\d{2,})x(\d{2,})"
        matches = re.search(regex, recommend_resolution, re.IGNORECASE)
        if matches:
            gr = matches.groups()
            latent = torch.zeros([batch_size, 4, int(gr[1]) // 8, int(gr[0]) // 8], device=self.device)
        else:
            latent = torch.zeros([batch_size, 4, 512 // 8, 512 // 8], device=self.device)
        return ({"samples":latent}, )
