# wildcard trick is taken from pythongossss's
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False
any_typ = AnyType("*")

class BundleType(str):
    def __ne__(self, __value: object) -> bool:
        return False
bundle_typ = BundleType("linsooBundleType")

LINSOO_DEFAULT_STRING_NOTE = 'Recommended Links\ninput_0:MODEL\ninput_1:Positive\ninput_2:Negative\ninput_3:CLIP\ninput_4:VAE\ninput_5:ETC...'
# ---------------------------------------------------------------------------
class LinsooMultiInputs:

    @classmethod    
    def INPUT_TYPES(s):
        return {
            "optional": {
                "model": ('MODEL', {"default": None , "tooltip": "Connect anything."}),
                "positive": ('CONDITIONING', {"default": None , "tooltip": "Connect anything."}),
                "negative": ('CONDITIONING', {"default": None , "tooltip": "Connect anything."}),
                "clip": ('CLIP', {"default": None , "tooltip": "Connect anything."}),
                "vae": ('VAE', {"default": None , "tooltip": "Connect anything."}),
                "input_0": (any_typ, {"default": None , "tooltip": "Connect anything."}),
                "input_1": (any_typ, {"default": None , "tooltip": "Connect anything."}),
                "input_2": (any_typ, {"default": None , "tooltip": "Connect anything."}),
            }
        }

    RETURN_TYPES = (bundle_typ,)
    RETURN_NAMES = ('bundle_output',)
    OUTPUT_TOOLTIPS = ("Combine multiple inputs into one output", )
    FUNCTION = "multi_inputs"

    CATEGORY = "linsoo"
    DESCRIPTION = "Combine multiple inputs into one output"

    def multi_inputs(self,model=None, positive=None,negative=None,clip=None,vae=None,input_0=None,input_1=None,input_2=None):
        return ([model,positive,negative,clip,vae,input_0,input_1,input_2],)
    
# ---------------------------------------------------------------------------
class LinsooMultiOutputs:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "bundle_input": (bundle_typ, {"tooltip": "Receives signals received through Linsoo Multi Inputs."}),
            }
        }
    RETURN_TYPES = ('MODEL','CONDITIONING','CONDITIONING','CLIP','VAE',any_typ,any_typ,any_typ)
    RETURN_NAMES = ('model','positive','negative','clip','vae','output_0','output_1','output_2')
    OUTPUT_TOOLTIPS = ("Split one input into multiple outputs")
    FUNCTION = "multi_outputs"

    CATEGORY = "linsoo"
    DESCRIPTION = "Split one input into multiple outputs"

    def multi_outputs(self,bundle_input, tmp_note=None):
        _=tmp_note
        return (bundle_input[0],bundle_input[1],bundle_input[2],bundle_input[3],bundle_input[4],bundle_input[5],bundle_input[6],bundle_input[7])