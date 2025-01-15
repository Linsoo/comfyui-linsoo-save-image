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

class LinsooSaveImage:

    FILE_TYPE_PNG = ".png"
    FILE_TYPE_WEBP = ".webp"
    FILE_TYPE_JPG = ".jpg"
    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "linsoo"

    SAVE_OPTION_NONE  = 'None'    #저장 안함
    SAVE_OPTION_IMAGE = 'Image(include meta)'
    SAVE_OPTION_IMAGE_AND_JSON = 'Image(include meta)+JSON'

    DEFAULT_STRING_EXIF ='%positive%\nNegative prompt:%negative%\nSteps: %steps%, Sampler: %sampler_name%, Schedule type: %scheduler%, CFG scale: %cfg%, Seed: %seed%, Size: %width%x%height%, Model hash: %ckpt_hash%, Model: %ckpt%, Denoising strength: %denoise%, Clip skip: %clipskip%, Lora hashes: "%loras%" Version: 1.10.1'

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "%date:YYYYMMDD_hhmmss%_LinsooSaveImage"}),
                "exif_format": ("STRING", {"default": s.DEFAULT_STRING_EXIF, "multiline": "TRUE" }, ),
                "file_type": ([s.FILE_TYPE_WEBP, s.FILE_TYPE_PNG,s.FILE_TYPE_JPG ], 
                              {'default': s.FILE_TYPE_WEBP,'tooltip': "webp : include exif_format+workflow\njpg : include exif_form \npng : ComfyUI original (include prompt+workflow)"}),
                "quality": ("INT", {"default": 90, "min": -1, "max": 100, 'tooltip': "Lossless : -1, \nQuality : 1~100 "}, ),
                "save_option": ([s.SAVE_OPTION_NONE, 
                               s.SAVE_OPTION_IMAGE,
                               s.SAVE_OPTION_IMAGE_AND_JSON],
                               {'default': s.SAVE_OPTION_IMAGE,'tooltip': "Where to store metadata?"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    # ------------------------------------------------------------------------
    def __init__(self):
        self.__reset()

        #단부루 캐릭터명을 읽어들임
        curdir = os.path.dirname(__file__)
        self.__danbooru_characters = {}
        with open(curdir+"/danbooru_character.txt", "r", encoding="utf8") as file:
            while True:
                danbooru_character_name = file.readline()
                if not danbooru_character_name:
                    break
                danbooru_character_name = danbooru_character_name.rstrip('\n')
                self.__danbooru_characters[danbooru_character_name] = True
    # ------------------------------------------------------------------------
    def __reset(self):
        self.__m_ckpt_name = []
        self.__m_samplers = []
        self.__m_prompt = {}
        self.__m_clip_skip = []
        self.__m_loras = []
    # ------------------------------------------------------------------------
    def __parse_prompt(self,unique_id:str, prompt, workflow, cpkts_path:str, loras_path:str):
        self.__reset()
        workflow = workflow.get("workflow")
        if workflow and prompt:

            # 링크가 있는 노드들만 일단 추려냄
            links = workflow.get("links")
            next_id = []
            next_id.append(unique_id)
            verified_nodes=set()
            while True:
                nolinkexit = True
                find_id = next_id.pop()

                found_node =  prompt.get(find_id)
                if found_node:
                    found_node_cls_type = found_node.get('class_type')
                    found_node_cls_type = found_node_cls_type.lower()
                    found_node_inputs = found_node.get('inputs')

                    # ----------------------------------------------------
                    if 'checkpoint' in found_node_cls_type:
                        sha256_str = None
                        ckpt_name = self.__get_first_item(found_node_inputs)

                        # Checkpoint 절대 경로를 구하고
                        ckpt_abs_path = None
                        for cpkt_path in cpkts_path[0]:
                            tmp_path = os.path.join(cpkt_path +'/'+ ckpt_name)
                            if os.path.exists(tmp_path):
                                ckpt_abs_path = tmp_path
                                break

                        if ckpt_abs_path:
                            sha256_str = self.__get_file_hash(ckpt_abs_path)

                        if sha256_str:
                            sha256_str = sha256_str[0:10] # 10자만 잘라냄..

                        tmp_name = None
                        if ckpt_abs_path:
                            # 파일 이름만 추출해서 넣음 (확장자 제외)
                            tmp_name = os.path.basename(ckpt_name)
                            tmp_name = os.path.splitext(tmp_name)[0]

                        self.__m_ckpt_name.append([tmp_name, sha256_str])
                    # ----------------------------------------------------
                    elif 'sampler' in found_node_cls_type:
                        sampler = dict()
                        sampler["seed"] = found_node_inputs.get("seed")
                        sampler["steps"] = found_node_inputs.get("steps")
                        sampler["cfg"] = found_node_inputs.get("cfg")
                        sampler["sampler_name"] = found_node_inputs.get("sampler_name")
                        sampler["scheduler"] = found_node_inputs.get("scheduler")
                        sampler["denoise"] = found_node_inputs.get("denoise")
                        positive_id = found_node_inputs.get("positive")
                        if positive_id:
                            sampler["positive"] = positive_id[0]
                        negative_id = found_node_inputs.get("negative")
                        if negative_id:
                            sampler["negative"] = negative_id[0]

                        self.__m_samplers.append(sampler)
                    # ----------------------------------------------------
                    elif 'cliptextencode' in found_node_cls_type:
                        prpt = dict()
                        prpt["text"] = found_node_inputs.get("text")
                        # clip = tmp_inputs.get('clip')
                        # if clip:
                        #     clip = clip[0]
                        # prpt['clip'] = clip
                        prpt["positive"] = None
                        self.__m_prompt[find_id] = prpt
                    # ----------------------------------------------------
                    elif 'clipsetlastlayer' in found_node_cls_type:
                        clipskip = found_node_inputs.get("stop_at_clip_layer")
                        self.__m_clip_skip.append(clipskip)
                    elif 'loraloader' in found_node_cls_type:
                        lora_abs_path   = None
                        lora_name       = found_node_inputs.get("lora_name")
                        strength_model  = found_node_inputs.get("strength_model")

                        lora_name = self.__get_first_item(lora_name)

                        # 우선 Lora 경로중에 어느 경로에 파일이 있는지 찾음.
                        for lora_path in loras_path[0]:
                            tmp_path = os.path.join(lora_path +'/'+ lora_name)
                            if os.path.exists(tmp_path):
                                lora_abs_path = tmp_path    #존재하는 절대 경로 찾음!
                                break

                        # 해시 파일이 있는지 확인한다.
                        if lora_abs_path:
                            sha256_str = self.__get_file_hash(lora_abs_path)

                        if sha256_str:
                            sha256_str = sha256_str[0:10] # 10자만 잘라냄..

                        tmp_name = None
                        if lora_abs_path:
                            # 파일 이름만 추출해서 넣음 (확장자 제외)
                            tmp_name = os.path.basename(lora_abs_path)
                            tmp_name = os.path.splitext(tmp_name)[0]

                        self.__m_loras.append([tmp_name, strength_model, sha256_str])
                # ----------------------------------------------------
                # 확인된 노드는 리스트에 추가 (중복 확인 제외하기 위해)
                verified_nodes.add(find_id)
                # ----------------------------------------------------
                for link in links:
                    aaa =str(link[3])
                    if aaa == find_id:
                        if str(link[1]) in verified_nodes:   #확인된 노드는 건너뛴다.
                            continue
                        nolinkexit = False
                        next_id.append(str(link[1]))
                # 더 이상 확인할 노드 없으면 루프 탈출 슝~
                if nolinkexit and len(next_id) == 0:
                    break
            # ---------------------------------------------------------
            # 루프가 끝나면 Positive prompt랑 negative를 체크한다.
            for smp in self.__m_samplers:
                pos = smp.get("positive")
                neg = smp.get("negative")

                tmp_prmpt = self.__m_prompt.get(pos)
                if tmp_prmpt:
                    tmp_prmpt["positive"] = True

                tmp_prmpt = self.__m_prompt.get(neg)
                if tmp_prmpt:
                    tmp_prmpt["positive"] = False
    # ------------------------------------------------------------------------
    def __make_exif(self, exif_str:str, width:int, height:int):
        ret_str = exif_str

        # ---------------------------------------------------------------------
        # %width%, %height%
        ret_str = ret_str.replace('%width%', str(width))
        ret_str = ret_str.replace('%height%', str(height))

        # ---------------------------------------------------------------------
        # %ckpt% %ckpt_hash%
        for ckpt in self.__m_ckpt_name:
            ret_str = ret_str.replace('%ckpt%', str(ckpt[0]))
            ret_str = ret_str.replace('%ckpt_hash%', str(ckpt[1]))
            break

        # ---------------------------------------------------------------------
        # %seed%, %steps%, %cfg%, %sampler_name%, %scheduler%, %denoise%
        tmp_seed = None
        tmp_steps = None
        tmp_cfg = None
        tmp_sampler_name = None
        tmp_scheduler = None
        tmp_denoise = None
        for sampler in self.__m_samplers:
            tmp_seed = sampler.get("seed")
            tmp_steps = sampler.get("steps")
            tmp_cfg = sampler.get("cfg")
            tmp_sampler_name = sampler.get("sampler_name")
            tmp_scheduler = sampler.get("scheduler")
            tmp_denoise = sampler.get("denoise")
            break  # 나중에 나오는 샘플러는 일단 배제...
        ret_str = ret_str.replace('%seed%', str(tmp_seed))
        ret_str = ret_str.replace('%steps%', str(tmp_steps))
        ret_str = ret_str.replace('%cfg%', str(tmp_cfg))
        ret_str = ret_str.replace('%sampler_name%', tmp_sampler_name)
        ret_str = ret_str.replace('%scheduler%', tmp_scheduler)
        ret_str = ret_str.replace('%denoise%', str(tmp_denoise))

        # ---------------------------------------------------------------------
        # %clipskip%
        tmp_clip = None
        for clip in self.__m_clip_skip:
            tmp_clip = clip * -1
            break
        ret_str = ret_str.replace('%clipskip%', str(tmp_clip))

        # ---------------------------------------------------------------------
        # %positive%, %negative%
        tmp_positive = ""
        tmp_negative = ""
        prompt_list = self.__m_prompt.values()
        for tmp_prompt in prompt_list:
            positive = tmp_prompt.get("positive")
            text = tmp_prompt.get("text")
            if positive is True:
                tmp_positive = tmp_positive + text + ','
            else:
                tmp_negative = tmp_negative + text + ','
        tmp_positive.rstrip(',')
        tmp_negative.rstrip(',')
        ret_str = ret_str.replace('%positive%', tmp_positive)
        ret_str = ret_str.replace('%negative%', tmp_negative)

        # ---------------------------------------------------------------------
        # %loras%
        # Lora hashes: "Detailed anime style - SDXL_pony: fccbd680c4cd, SonoBisqueDoll_KitagawaMarinXL: a7f948081de0, Detailed Background: de3187cb8f3c, mitsuha-miyamizu-ponyxl-lora-nochekaiser: c6f2fa9992de"
        tmp_lora_str = ''
        for lora in self.__m_loras:
            name = lora[0]
            if isinstance(name, dict):
                name = name.get("content")
            elif isinstance(name, list):
                name = os.path.basename(name)

            tmp_lora_str = tmp_lora_str + f'{name}: {lora[2]}, '
        if len(tmp_lora_str) > 0:
            tmp_lora_str = tmp_lora_str.rstrip(", ")
            ret_str = ret_str.replace('%loras%', tmp_lora_str)
        return ret_str

    # ------------------------------------------------------------------------
    def __get_file_hash(self, file_path:str):
        # .sha256 파일이 있는지 확인한다.
        sha256_hash = None
        sha256_abs_path = file_path + '.sha256'
        if os.path.exists(sha256_abs_path):
            # 파일이 있으면 읽고
            with open(sha256_abs_path, "r", encoding="utf8") as file:
                sha256_hash = file.read()
            sha256_hash = sha256_hash.split(" ")
            sha256_hash = sha256_hash[0]
        else:
            # 파일이 없으면 생성하고 저장한다.
            h = hashlib.sha256()
            b = bytearray(128 * 1024)
            mv = memoryview(b)
            with open(file_path, "rb", buffering=0) as f:
                while n := f.readinto(mv):
                    h.update(mv[:n])
            sha256_hash = h.hexdigest()
            #.sha256 파일로 저장
            tmp_str = sha256_hash + " *" + os.path.basename(file_path)
            with open(sha256_abs_path, "w", encoding="utf8") as file:
                file.write(tmp_str)
        return sha256_hash

    # ------------------------------------------------------------------------
    # 리스트, 딕, 셋 자료형이면 첫번째껄 리턴함
    def __get_first_item(self, anydata):
        while True:
            if isinstance(anydata, list):
                anydata = anydata[0]
                continue
            if isinstance(anydata, dict):
                for _, value in anydata.items():
                    anydata = value
                    break
                continue
            if isinstance(anydata, set):
                anydata = anydata[0]
                continue
            break
        return anydata

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
    # 절취선

    def save_images(self, images, filename_prefix, file_type, quality, save_option, exif_format=None, unique_id=None, prompt=None, extra_pnginfo=None):
        output_dir = folder_paths.get_output_directory()
        # https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py
        loras_path = folder_paths.folder_names_and_paths['loras']
        ckpt_path = folder_paths.folder_names_and_paths['checkpoints']
        # aaa = unique_id     #문자열로 들어옴
        # bbb = exif_format   #문자열로 들어옴
        #-------------------------------------------------------------------
        # 디버깅용
        # 이건 프롬프트
        if prompt is not None:
            jfile = "prompt.json"
            outfile = open(os.path.join(output_dir, jfile), 'w', encoding="utf8")
            json.dump(prompt, outfile, indent=4)
            outfile.close()

        # 이건 워크플로
        if extra_pnginfo is not None:
            jfile = "extra_pnginfo.json"
            outfile = open(os.path.join(output_dir, jfile), 'w', encoding="utf8")
            json.dump(extra_pnginfo, outfile, indent=4)
            outfile.close()
        #-------------------------------------------------------------------

        self.__parse_prompt(unique_id, prompt, extra_pnginfo,ckpt_path, loras_path)

        results = []
        for image in images:
            array = 255. * image.cpu().numpy()
            img = Image.fromarray(numpy.clip(array, 0, 255).astype(numpy.uint8))

            kwargs = dict()
            if save_option != self.SAVE_OPTION_NONE and not args.disable_metadata:
                if file_type == self.FILE_TYPE_PNG:
                    kwargs["compress_level"] = 4
                    metadata = PngInfo()
                    if prompt is not None:
                        metadata.add_text("prompt", json.dumps(prompt))
                    if extra_pnginfo is not None:
                        for x in extra_pnginfo:
                            metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                    kwargs["pnginfo"] = metadata
                # png가 아닌 나머지 확장자들...
                else:
                    if quality == -1:
                        kwargs["lossless"] = True
                    else:
                        kwargs["quality"] = quality

                    exif_dict = {"0th": {}, "Exif": {} }
                    tmp = self.__make_exif(exif_format, img.width, img.height)
                    exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(tmp)

                    # webp는 workflow를 내장한다. (jpg는 넣어도 ComfyUI에서 불러오는거 안되서 안넣음)
                    if extra_pnginfo is not None and file_type==self.FILE_TYPE_WEBP:
                        tmp_data = extra_pnginfo.get('workflow')
                        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = "Workflow: " + json.dumps(tmp_data)
                    # 이건 나중에 쓸지 모르니 일단 놔둠
                    # if prompt is not None:
                    #     exif_dict["0th"][piexif.ImageIFD.Make] = "Prompt: " + json.dumps(prompt)

                    kwargs["exif"] = piexif.dump(exif_dict)

            # filename_prefix에 암것도 안쓰면 이렇게
            if  len(filename_prefix) <= 0:
                filename_prefix = 'Linsoo_%date:YYYYMMDD_hhmmss%'
            ret = self.__parse_filename_prefix(filename_prefix)

            subfolder = os.path.dirname(ret)
            filename = f"{os.path.basename(ret)}{file_type}"
            abs_path = os.path.join(output_dir, subfolder)

            if not os.path.isdir(abs_path):
                os.makedirs(abs_path)

            if save_option == self.SAVE_OPTION_IMAGE_AND_JSON:
                if extra_pnginfo is not None:
                    json_filename = f"{os.path.basename(ret)}{'_workflow.json'}"
                    tmp_data = extra_pnginfo.get('workflow')
                    with open(os.path.join(abs_path, json_filename), 'w', encoding="utf8") as outfile:
                        json.dump(tmp_data, outfile, indent=4)
                if prompt is not None:
                    json_filename = f"{os.path.basename(ret)}{'_prompt.json'}"
                    # tmp_data = "Prompt: " + json.dumps(prompt)
                    with open(os.path.join(abs_path, json_filename), 'w', encoding="utf8") as outfile:
                        json.dump(prompt, outfile, indent=4)

            img.save(os.path.join(abs_path, filename), **kwargs)
            results.append({
                "filename": filename,
                "subfolder": subfolder,
                "type": "output",
            })

        return { "ui": { "images": results } }