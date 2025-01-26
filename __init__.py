from .LinsooSaveImage import LinsooSaveImage
from .LinsooLoadImage import LinsooLoadImage
from .LinsooEmptyLatentImage import LinsooEmptyLatentImage
from .LinsooMultiInputOutput import LinsooMultiOutputs, LinsooMultiInputs


NODE_CLASS_MAPPINGS = {
    "LinsooSaveImage": LinsooSaveImage,
    "LinsooLoadImage" : LinsooLoadImage,
    "LinsooEmptyLatentImage": LinsooEmptyLatentImage,
    "LinsooMultiInputs": LinsooMultiInputs,
    "LinsooMultiOutputs": LinsooMultiOutputs,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LinsooSaveImage": "Linsoo Save Image",
    "LinsooLoadImage" : "Linsoo Load Image (In development.. not working)",
    "LinsooEmptyLatentImage": "Linsoo Empty Latent Image",
    "LinsooMultiInputs": "Linsoo Multi Inputs",
    "LinsooMultiOutputs": "Linsoo Multi Outputs",
}
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']