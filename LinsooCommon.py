
import hashlib
import json
import os

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False
any_typ = AnyType("*")

class LinsooCustomDataType(str):
    def __ne__(self, __value: object) -> bool:
        return False

# ------------------------------------------------------------------------
def linsoo_get_file_hash(file_path:str):
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
def linsoo_get_first_item(anydata):
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
def linsoo_parse_prompt(prompt=None, workflow=None,unique_id:str=None, cpkts_path=None, loras_path=None):

    list_ckpt_name = []
    list_samplers = []
    list_prompt = {}
    list_clip_skip = []
    list_loras = []

    next_id = []
    verified_nodes=set()

    if workflow and prompt:

        if isinstance(workflow, dict) is not True:
            workflow = workflow.decode("utf-8")
            workflow = workflow.removeprefix('workflow: ')
            workflow = json.loads(workflow)
        else:
            tmp = workflow.get("workflow")
            if tmp:
                workflow = tmp


        if isinstance(prompt, dict) is not True:
            prompt = prompt.decode("utf-8")
            prompt = prompt.removeprefix('prompt: ')
            prompt = json.loads(prompt)

        # 시작 포인트가 없으면 saveimage가 들어간거 id를 넣는다
        if unique_id is None:
            for tmp in prompt.items():
                cls_type =  tmp[1].get('class_type')
                # 우선 내 파일 저장 노드 먼저 찾아보고
                if cls_type.lower() == 'linsoosaveimage':
                    next_id.append(tmp[0])
            # 없으면 일반 이미지 저장 노드를 찾아서 거기서 부터 시작한다.
            if len(next_id) == 0:
                for tmp in prompt.items():
                    cls_type =  tmp[1].get('class_type')
                    if cls_type.lower() == 'saveimage':
                        next_id.append(tmp[0])
        else:
            next_id.append(unique_id)


        # 링크가 있는 노드들만 일단 추려냄
        links = workflow.get("links")

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
                    ckpt_name = linsoo_get_first_item(found_node_inputs)

                    # 체크포인트 경로가 있으면 해시값을 구하고 없으면 그냥 None으로 퉁침
                    if cpkts_path:
                        ckpt_abs_path = None
                        for tmp in cpkts_path[0]:
                            tmp = os.path.join(tmp +'/'+ ckpt_name)
                            if os.path.exists(tmp):
                                ckpt_abs_path = tmp
                                break

                        if ckpt_abs_path:
                            sha256_str = linsoo_get_file_hash(ckpt_abs_path)

                        if sha256_str:
                            sha256_str = sha256_str[0:10] # 10자만 잘라냄..

                    # 파일 이름만 추출해서 넣음 (확장자 제외)        
                    ckpt_name = os.path.basename(ckpt_name)
                    ckpt_name = os.path.splitext(ckpt_name)[0]
                    list_ckpt_name.append([ckpt_name, sha256_str])
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

                    list_samplers.append(sampler)
                # ----------------------------------------------------
                elif 'cliptextencode' in found_node_cls_type:
                    prpt = dict()
                    prpt["text"] = found_node_inputs.get("text")
                    prpt["positive"] = None
                    list_prompt[find_id] = prpt
                # ----------------------------------------------------
                elif 'clipsetlastlayer' in found_node_cls_type:
                    list_clip_skip.append(found_node_inputs.get("stop_at_clip_layer"))
                elif 'loraloader' in found_node_cls_type:
                    lora_abs_path   = None
                    lora_name       = found_node_inputs.get("lora_name")
                    strength_model  = found_node_inputs.get("strength_model")
                    sha256_str      = None
                    lora_name = linsoo_get_first_item(lora_name)

                    if loras_path:
                        # 우선 Lora 경로중에 어느 경로에 파일이 있는지 찾음.
                        for lora_path in loras_path[0]:
                            tmp = os.path.join(lora_path +'/'+ lora_name)
                            if os.path.exists(tmp):
                                lora_abs_path = tmp    #존재하는 절대 경로 찾음!
                                break

                        # 해시 파일이 있는지 확인한다.
                        if lora_abs_path:
                            sha256_str = linsoo_get_file_hash(lora_abs_path)

                        if sha256_str:
                            sha256_str = sha256_str[0:10] # 10자만 잘라냄..

                    # 파일 이름만 추출해서 넣음 (확장자 제외)
                    if lora_name:
                        lora_name = os.path.basename(lora_name)
                        lora_name = os.path.splitext(lora_name)[0]

                    list_loras.append([lora_name, strength_model, sha256_str])
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
        for tmp in list_samplers:
            pos = tmp.get("positive")
            neg = tmp.get("negative")

            tmp_prmpt = list_prompt.get(pos)
            if tmp_prmpt:
                tmp_prmpt["positive"] = True

            tmp_prmpt = list_prompt.get(neg)
            if tmp_prmpt:
                tmp_prmpt["positive"] = False
    return (list_ckpt_name, list_samplers, list_prompt, list_clip_skip, list_loras)
    # ------------------------------------------------------------------------
# with open("extra_pnginfo.json", "r", encoding="utf8") as tmpfile:
#     workflow = json.load(tmpfile)
# with open("prompt.json", "r", encoding="utf8") as tmpfile:
#     prompt = json.load(tmpfile)
# ret_ckpt, ret_sampler, ret_prompt, ret_clip, ret_loras = linsoo_parse_prompt(prompt,workflow,)

# print('ckpt: ', ret_ckpt)
# print('sampler: ', ret_sampler)
# print('prompt: ',ret_prompt)
# print('clip skip: ',ret_clip)
# print('loras: ',ret_loras)
