import os
import datetime
import hashlib
import re
import json
import numpy
from comfy.cli_args import args
import folder_paths
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import piexif
import piexif.helper
from .LinsooCommon import *
import comfyui_version

class LinsooSaveImage:

    FILE_TYPE_PNG = ".png"
    FILE_TYPE_WEBP = ".webp"
    FILE_TYPE_JPG = ".jpg"
    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "linsoo"

    SAVE_TYPE_NONE  = 'None'    #저장 안함
    SAVE_TYPE_A1111 = 'A1111 WebUI (webp,png)'
    SAVE_TYPE_COMFYUI = 'ComfyUI (webp,png)'
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "%date:YYYYMMDD_hhmmss%_LinsooSaveImage"}),
                "file_type": ([s.FILE_TYPE_WEBP, s.FILE_TYPE_PNG,s.FILE_TYPE_JPG ], 
                              {'default': s.FILE_TYPE_WEBP,'tooltip': "Recommend webp"}),
                "quality": ("INT", {"default": 90, "min": -1, "max": 100, 'tooltip': ""}, ),
                "meta_save_type": ([s.SAVE_TYPE_NONE, 
                                    s.SAVE_TYPE_A1111,
                                    s.SAVE_TYPE_COMFYUI,],
                                    {'default': s.SAVE_TYPE_COMFYUI,'tooltip': ""}),
                "save_all_meta_to_txt":("BOOLEAN",{"default": False, 'tooltip': ""})
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    # 절취선
    # ------------------------------------------------------------------------
    def __init__(self):
        self.__m_ckpt_name = []
        self.__m_samplers = []
        self.__m_prompt = {}
        self.__m_clip_skip = []
        self.__m_loras = []
        # 단부루 캐릭터명 변수
        self.__danbooru_characters = {}
    # ------------------------------------------------------------------------
    def __parse_date_time(self, time_now, date_str: str):
        date_str = date_str.replace("YYYY", "%Y")
        date_str = date_str.replace("YY", "%y")
        date_str = date_str.replace("MM", "%m")
        date_str = date_str.replace("DD", "%d")
        date_str = date_str.replace("hh", "%H")
        date_str = date_str.replace("mm", "%M")
        date_str = date_str.replace("ss", "%S")

        return time_now.strftime(date_str)

    # https://docs.python.org/3.8/library/datetime.html#strftime-and-strptime-format-codes
    def __parse_filename_prefix(self, filename_prefix: str):
        # 맨앞에 / 들어가면 루트 경로로 인식해서 문제됨
        filename_prefix = filename_prefix.lstrip("/")

        # 일단 날짜  %date:yyyy-MM-dd hh-mm-ss%
        # YYYY -> %Y
        # YY -> %y
        # MM -> %m
        # DD -> %d
        # hh -> %H
        # mm -> %M
        # ss -> %S
        now = datetime.datetime.now()
        reg_date = r"%date:([^%]*)%"
        matches = re.finditer(reg_date, filename_prefix)
        for match in matches:
            match_str = match.group()
            group_str = match.groups()
            tmp_str = self.__parse_date_time(now, group_str[0])
            if tmp_str:
                filename_prefix = filename_prefix.replace(match_str, tmp_str)

        # -------------------------------------------------------------------------
        # 체크포인트는 첫번째껄 사용함.
        for ckpt in self.__m_ckpt_name:
            # 체크포인트 이름
            filename_prefix = filename_prefix.replace("%ckpt%", str(ckpt[0]))
            # 체크포인트 해시
            filename_prefix = filename_prefix.replace("%ckpt_hash%", str(ckpt[1]))
            break

        # 샘플러에 있는 정보
        for sampler in self.__m_samplers:
            seed = sampler.get("seed")
            steps = sampler.get("steps")
            cfg = sampler.get("cfg")
            sampler_name = sampler.get("sampler_name")
            scheduler = sampler.get("scheduler")

            filename_prefix = filename_prefix.replace("%seed%", str(seed))
            filename_prefix = filename_prefix.replace("%steps%", str(steps))
            filename_prefix = filename_prefix.replace("%cfg%", str(cfg))
            filename_prefix = filename_prefix.replace("%sampler_name%", sampler_name)
            filename_prefix = filename_prefix.replace("%scheduler%", scheduler)
            break
        # -------------------------------------------------------------------------
        if '%character_name%' in filename_prefix:
            found_char_names = set()
            #단부루 캐릭터 이름 목록을 안 읽었다면 읽어들임
            if len(self.__danbooru_characters) <=0:
                curdir = os.path.dirname(__file__)
                with open(curdir+"/danbooru_character.txt", "r", encoding="utf-8") as file:
                    while True:
                        danbooru_character_name = file.readline()
                        if not danbooru_character_name:
                            break
                        danbooru_character_name = danbooru_character_name.rstrip('\n')
                        self.__danbooru_characters[danbooru_character_name] = True

            for tmp_prompt in self.__m_prompt.values():
                tmp_text = tmp_prompt.get('text')
                tmp_text = str(tmp_text).replace('\n','')
                tmp_text = str(tmp_text).replace('\r','')
                tmp_text = str(tmp_text).replace('\\', '')
                sp = tmp_text.split(',')
                for prom in sp:
                    prom = prom.strip()
                    found_tmp_name = self.__danbooru_characters.get(prom)
                    if found_tmp_name:
                        found_char_names.add(prom)

            tmp_char_name = ''
            for char_name in found_char_names:
                tmp_char_name = tmp_char_name + char_name + ','
            tmp_char_name = tmp_char_name.rstrip(',')

            if len(tmp_char_name) > 0:
                filename_prefix = filename_prefix.replace('%character_name%', tmp_char_name)
            else:
                filename_prefix = filename_prefix.replace('%character_name%', '')
        return filename_prefix

    # ------------------------------------------------------------------------
    # https://github.com/AUTOMATIC1111/stable-diffusion-webui 에서 exif 이미지 저장 하는 방식으로 저장하기 
    def __make_a1111_meta_format(self, width:int=0, height:int=0):
        ckpt_name, ckpt_hash = None, None
        for ckpt in self.__m_ckpt_name:
            ckpt_name = str(ckpt[0])
            ckpt_hash = str(ckpt[1])
            break

        tmp_seed,tmp_steps,tmp_steps,tmp_cfg,tmp_sampler_name,tmp_scheduler,tmp_denoise= None,None,None,None,None,None,None
        for sampler in self.__m_samplers:
            tmp_seed = sampler.get("seed")
            tmp_steps = sampler.get("steps")
            tmp_cfg = sampler.get("cfg")
            tmp_sampler_name = sampler.get("sampler_name")
            tmp_scheduler = sampler.get("scheduler")
            tmp_denoise = sampler.get("denoise")
            break  # 나중에 나오는 샘플러는 일단 배제...

        tmp_clip = None
        for clip in self.__m_clip_skip:
            tmp_clip = clip * -1
            break

        tmp_positive = ""
        tmp_negative = ""
        prompt_list = self.__m_prompt.values()
        for tmp_prompt in prompt_list:
            positive = tmp_prompt.get("positive")
            text = tmp_prompt.get("text")
            if positive is True:
                tmp_positive = tmp_positive + str(text) + ','
            else:
                tmp_negative = tmp_negative + str(text) + ','
        tmp_positive = tmp_positive.rstrip(',')
        tmp_negative = tmp_negative.rstrip(',')

        # ------------------------------------------------------------------------
        # Lora hashes: "로라이름: 로라해쉬, 로라이름: 로라해쉬, SousouNoFrieren_FernXL: bd2d6c174fe7"
        tmp_lora_str = None
        if len(self.__m_loras)>0:
            tmp_lora_str = ''
            for lora in self.__m_loras:
                name = lora[0]
                if isinstance(name, dict):
                    name = name.get("content")
                elif isinstance(name, list):
                    name = os.path.basename(name)
                tmp_lora_str = tmp_lora_str + f'{name}: {lora[2]}, '
            tmp_lora_str = tmp_lora_str.rstrip(", ")

        # ------------------------------------------------------------------------
        #"stable-diffusion-webui\modules\processing.py, def create_infotext"
        generation_params = {
            "Steps": tmp_steps,
            "Sampler": tmp_sampler_name,
            "Schedule type": tmp_scheduler,
            "CFG scale": tmp_cfg,
            # "Image CFG scale": getattr(p, 'image_cfg_scale', None),
            "Image CFG scale": None, 
            "Seed": tmp_seed,
            # "Face restoration": opts.face_restoration_model if p.restore_faces else None,
            "Face restoration": None,
            "Size": f"{width}x{height}",
            "Model hash": ckpt_hash if ckpt_hash else None,
            "Model": ckpt_name if ckpt_name else None,
            # "FP8 weight": opts.fp8_storage if devices.fp8 else None,
            "FP8 weight": None,
            # "Cache FP16 weight for LoRA": opts.cache_fp16_weight if devices.fp8 else None,
            "Cache FP16 weight for LoRA": None,
            # "VAE hash": p.sd_vae_hash if opts.add_vae_hash_to_info else None,
            "VAE hash": None,
            # "VAE": p.sd_vae_name if opts.add_vae_name_to_info else None,
            "VAE": None,
            # "Variation seed": (None if p.subseed_strength == 0 else (p.all_subseeds[0] if use_main_prompt else all_subseeds[index])),
            "Variation seed": None,
            # "Variation seed strength": (None if p.subseed_strength == 0 else p.subseed_strength),
            "Variation seed strength": None,
            # "Seed resize from": (None if p.seed_resize_from_w <= 0 or p.seed_resize_from_h <= 0 else f"{p.seed_resize_from_w}x{p.seed_resize_from_h}"),
            "Seed resize from": None,
            "Denoising strength": tmp_denoise,
            # "Conditional mask weight": getattr(p, "inpainting_mask_weight", shared.opts.inpainting_mask_weight) if p.is_using_inpainting_conditioning else None,
            "Conditional mask weight": None,
            "Clip skip": None if tmp_clip is not None and tmp_clip <= 1 else tmp_clip,
            # "ENSD": opts.eta_noise_seed_delta if uses_ensd else None,
            "ENSD": None,
            # "Token merging ratio": None if token_merging_ratio == 0 else token_merging_ratio,
            "Token merging ratio": None,
            # "Token merging ratio hr": None if not enable_hr or token_merging_ratio_hr == 0 else token_merging_ratio_hr,
            "Token merging ratio hr": None,
            # "Init image hash": getattr(p, 'init_img_hash', None),
            "Init image hash": None,
            # "RNG": opts.randn_source if opts.randn_source != "GPU" else None,
            "RNG": None,
            # "Tiling": "True" if p.tiling else None,
            "Tiling": None,
            # **p.extra_generation_params,  # 여기서 로라
            "Lora hashes": tmp_lora_str,
            # "Version": program_version() if opts.add_version_to_infotext else None,
            "Version": f'ComfyUI version: {comfyui_version.__version__}',
            # "User": p.user if opts.add_user_name_to_info else None,
            "User": None,
        }
        generation_params_text = ", ".join([k if k == v else f'{k}: {self.__quote(v)}' for k, v in generation_params.items() if v is not None])
        negative_prompt_text = f"\nNegative prompt: {tmp_negative}" if tmp_negative else ""
        return f"{tmp_positive}{negative_prompt_text}\n{generation_params_text}".strip()

    # ------------------------------------------------------------------------
    def __quote(self,text):
        if ',' not in str(text) and '\n' not in str(text) and ':' not in str(text):
            return text
        return json.dumps(text, ensure_ascii=False)
    # ------------------------------------------------------------------------
    # 절취선

    def save_images(self, images, filename_prefix, file_type, quality, meta_save_type, save_all_meta_to_txt=False, exif_format=None, unique_id=None, prompt=None, extra_pnginfo=None):
        output_dir = folder_paths.get_output_directory()
        # https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py
        loras_path = folder_paths.folder_names_and_paths['loras']
        ckpt_path = folder_paths.folder_names_and_paths['checkpoints']
        #-------------------------------------------------------------------
        # 디버깅용
        # 이건 프롬프트
        if prompt is not None:
            jfile = "prompt.json"
            outfile = open(os.path.join(output_dir, jfile), 'w', encoding="utf-8")
            json.dump(prompt, outfile, indent=4)
            outfile.close()

        # 이건 워크플로
        if extra_pnginfo is not None:
            jfile = "extra_pnginfo.json"
            outfile = open(os.path.join(output_dir, jfile), 'w', encoding="utf-8")
            json.dump(extra_pnginfo, outfile, indent=4)
            outfile.close()
        # -------------------------------------------------------------------
        # 프롬프트랑 워크플로 파싱해서 정보 챙긴다.
        self.__m_ckpt_name = []
        self.__m_samplers = []
        self.__m_prompt = {}
        self.__m_clip_skip = []
        self.__m_loras = []
        self.__m_ckpt_name, self.__m_samplers, self.__m_prompt, self.__m_clip_skip, self.__m_loras = linsoo_parse_prompt(prompt,extra_pnginfo,unique_id,ckpt_path, loras_path)
        # -------------------------------------------------------------------
        results = []
        for image in images:
            array = 255. * image.cpu().numpy()
            img = Image.fromarray(numpy.clip(array, 0, 255).astype(numpy.uint8))

            kwargs = dict()
            exif_dict = {"0th": {}, "Exif": {} }
            a1111_data = None

            if meta_save_type != self.SAVE_TYPE_NONE and not args.disable_metadata:

                match file_type:
                    case self.FILE_TYPE_PNG:
                        kwargs["compress_level"] = 4
                        metadata = PngInfo()
                        if prompt is not None:
                            metadata.add_text("prompt", json.dumps(prompt))
                        if extra_pnginfo is not None:
                            for x in extra_pnginfo:
                                metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                        kwargs["pnginfo"] = metadata
                    
                    case self.FILE_TYPE_JPG:
                        kwargs["quality"] = 0 if quality<0 else quality
                        a1111_data = self.__make_a1111_meta_format(img.width, img.height)
                        exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(a1111_data, encoding='unicode')
                        kwargs["exif"] = piexif.dump(exif_dict)
                    
                    case self.FILE_TYPE_WEBP:
                        if quality == -1:
                            kwargs["lossless"] = True
                        else:
                            kwargs["quality"] = quality

                        match meta_save_type:
                            case self.SAVE_TYPE_COMFYUI:
                                if extra_pnginfo is not None:
                                    tmp_data = extra_pnginfo.get('workflow')
                                    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = "workflow: " + json.dumps(tmp_data)
                                if prompt is not None:
                                    exif_dict["0th"][piexif.ImageIFD.Make] = "prompt: " + json.dumps(prompt)
                            case self.SAVE_TYPE_A1111:
                                a1111_data = self.__make_a1111_meta_format(img.width, img.height)
                                exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(a1111_data, encoding='unicode')
                        kwargs["exif"] = piexif.dump(exif_dict)
            # ---------------------------------------------------------------------------
            # filename_prefix에 암것도 안쓰면 이렇게
            if  len(filename_prefix) <= 0:
                filename_prefix = 'Linsoo_%date:YYYYMMDD_hhmmss%'
            ret = self.__parse_filename_prefix(filename_prefix)

            subfolder = os.path.dirname(ret)
            filename = f"{os.path.basename(ret)}{file_type}"
            abs_path = os.path.join(output_dir, subfolder)

            if not os.path.isdir(abs_path):
                os.makedirs(abs_path)
            # ---------------------------------------------------------------------------
            if save_all_meta_to_txt:
                if a1111_data is None:
                    a1111_data = self.__make_a1111_meta_format(img.width, img.height)
                tmp_filename = f"{os.path.basename(ret)}{'_a1111_prompt.txt'}"
                with open(os.path.join(abs_path, tmp_filename), 'w', encoding="utf-8") as outfile:
                    outfile.write(a1111_data)
            
                if extra_pnginfo is not None:
                    tmp_filename = f"{os.path.basename(ret)}{'_workflow.json'}"
                    tmp_data = extra_pnginfo.get('workflow')
                    with open(os.path.join(abs_path, tmp_filename), 'w', encoding="utf-8") as outfile:
                        json.dump(tmp_data, outfile, indent=4)
                if prompt is not None:
                    tmp_filename = f"{os.path.basename(ret)}{'_prompt.json'}"
                    # tmp_data = "Prompt: " + json.dumps(prompt)
                    with open(os.path.join(abs_path, tmp_filename), 'w', encoding="utf-8") as outfile:
                        json.dump(prompt, outfile, indent=4)
            # ---------------------------------------------------------------------------
            img.save(os.path.join(abs_path, filename), **kwargs)
            results.append({
                "filename": filename,
                "subfolder": subfolder,
                "type": "output",
            })

        return { "ui": { "images": results } }