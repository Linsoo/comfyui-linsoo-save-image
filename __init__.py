from .LinsooSaveImage import LinsooSaveImage
from .LinsooEmptyLatentImage import LinsooEmptyLatentImage

NODE_CLASS_MAPPINGS = {
    "LinsooSaveImage": LinsooSaveImage,
    "LinsooEmptyLatentImage": LinsooEmptyLatentImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LinsooSaveImage": "Linsoo Save Image",
    "LinsooEmptyLatentImage": "Linsoo Empty Latent Image",
    "LinsooLoraLoader": "Linsoo Lora Loader - not work... In development",
}
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']